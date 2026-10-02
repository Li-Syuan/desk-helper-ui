"""Local transactions, explicit tool approval, cancellation and deduplication."""
import concurrent.futures
import json
from pathlib import Path
import sqlite3
import threading
import time
import uuid
from .backends import DemoBackend, Reply, validate_reply

class BusyError(ValueError):
    pass

class Store:
    def __init__(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(directory / 'workspace.sqlite3')
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, project TEXT REFERENCES projects(id), status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS messages(seq INTEGER PRIMARY KEY, project TEXT REFERENCES projects(id), request TEXT REFERENCES requests(id), role TEXT, content TEXT);
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, project TEXT REFERENCES projects(id), title TEXT, done INTEGER NOT NULL DEFAULT 0 CHECK(done IN(0,1)));
        CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY, project TEXT REFERENCES projects(id), request TEXT UNIQUE REFERENCES requests(id), payload TEXT, expires REAL, status TEXT CHECK(status IN('pending','approved','declined')), receipt TEXT);
        """)
        with self.db:
            # An interrupted request is unknown; reopening never sends it again.
            self.db.execute("UPDATE requests SET status='interrupted' WHERE status='running'")
        if not self.projects():
            self.create_project('My workspace')
    def projects(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM projects ORDER BY rowid')]
    def project(self, project):
        if not self.db.execute('SELECT 1 FROM projects WHERE id=?', (project,)).fetchone():
            raise ValueError('unknown_project')
    def create_project(self, name):
        name = name.strip()
        if not 1 <= len(name) <= 80:
            raise ValueError('project_name_required_max_80')
        value = uuid.uuid4().hex
        with self.db:
            self.db.execute('INSERT INTO projects VALUES(?,?)', (value, name))
        return value
    def messages(self, project):
        self.project(project)
        return [dict(r) for r in self.db.execute('SELECT m.*, r.status FROM messages m JOIN requests r ON r.id=m.request WHERE m.project=? ORDER BY m.seq', (project,))]
    def context(self, project):
        return [{'role':m['role'],'content':m['content']} for m in self.messages(project) if m['status']=='completed']
    def tasks(self, project):
        self.project(project)
        return [dict(r) for r in self.db.execute('SELECT * FROM tasks WHERE project=? ORDER BY rowid', (project,))]
    def add_task(self, project, title):
        self.project(project)
        title = title.strip()
        if not 1 <= len(title) <= 200 or any(ord(c)<32 for c in title):
            raise ValueError('task_title_required_max_200')
        value = uuid.uuid4().hex
        with self.db:
            self.db.execute('INSERT INTO tasks(id,project,title) VALUES(?,?,?)', (value, project, title))
        return value
    def set_done(self, project, task, done):
        if type(done) is not bool:
            raise ValueError('invalid_task_state')
        with self.db:
            changed = self.db.execute('UPDATE tasks SET done=? WHERE id=? AND project=?', (int(done), task, project)).rowcount
            if changed != 1:
                raise ValueError('task_not_in_project')
    def proposals(self, project):
        return [dict(r) for r in self.db.execute("SELECT * FROM proposals WHERE project=? AND status='pending' ORDER BY rowid", (project,))]
    def approve(self, project, proposal, now=None, expected_payload=None):
        now = time.time() if now is None else now
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT p.*,r.status AS request_status FROM proposals p JOIN requests r ON r.id=p.request WHERE p.id=? AND p.project=?', (proposal, project)).fetchone()
            if not row:
                raise ValueError('proposal_not_in_project')
            if expected_payload is not None and row['payload'] != expected_payload:
                raise ValueError('proposal_changed_review_again')
            if row['status']=='approved':
                return json.loads(row['receipt'])
            if row['status']!='pending' or row['request_status']!='completed' or now >= row['expires']:
                raise ValueError('proposal_not_approved_or_expired')
            titles = json.loads(row['payload'])
            validate_reply(Reply('proposal',tuple(titles)))
            ids=[]
            for title in titles:
                value=uuid.uuid4().hex
                self.db.execute('INSERT INTO tasks(id,project,title) VALUES(?,?,?)',(value,project,title))
                ids.append(value)
            self.db.execute("UPDATE proposals SET status='approved',receipt=? WHERE id=?", (json.dumps(ids),proposal))
            return ids
    def decline(self, project, proposal):
        with self.db:
            changed=self.db.execute("UPDATE proposals SET status='declined' WHERE id=? AND project=? AND status='pending'", (proposal,project)).rowcount
        if not changed:
            raise ValueError('proposal_not_pending')
    def close(self):
        self.db.close()

class Engine:
    def __init__(self, store, backend=None):
        self.store=store
        self.backend=backend or DemoBackend()
        self.pool=concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.active=None
        self.closing=False
    def send(self, project, text):
        if self.closing or self.active is not None:
            raise BusyError('wait_for_active_request')
        self.store.project(project)
        if not isinstance(text,str) or not 1 <= len(text.strip()) <= 6000:
            raise ValueError('message_required_max_6000')
        text=text.strip()
        request=uuid.uuid4().hex
        history=self.store.context(project)+[{'role':'user','content':text}]
        cancelled=threading.Event()
        with self.store.db:
            self.store.db.execute("INSERT INTO requests VALUES(?,?,'running')",(request,project))
            self.store.db.execute('INSERT INTO messages(project,request,role,content) VALUES(?,?,?,?)',(project,request,'user',text))
        future=self.pool.submit(self.backend.reply,history,cancelled,request)
        self.active=(project,request,cancelled,future)
        return request
    def cancel(self):
        if self.active:
            project,request,event,future=self.active
            event.set()
            with self.store.db:
                self.store.db.execute("UPDATE requests SET status='cancelled' WHERE id=?",(request,))
        # Cancellation is cooperative; an arbitrary backend might still be working.
    def poll(self):
        if not self.active or not self.active[3].done():
            return None
        project,request,event,future=self.active
        try:
            if event.is_set():
                return {'status':'cancelled','project':project}
            try:
                reply=validate_reply(future.result())
            except Exception:
                with self.store.db:
                    self.store.db.execute("UPDATE requests SET status='failed' WHERE id=?",(request,))
                return {'status':'failed','project':project,'code':'backend_failed_or_invalid_reply'}
            with self.store.db:
                self.store.db.execute("UPDATE requests SET status='completed' WHERE id=?",(request,))
                self.store.db.execute('INSERT INTO messages(project,request,role,content) VALUES(?,?,?,?)',(project,request,'assistant',reply.text))
                if reply.tasks:
                    self.store.db.execute("INSERT INTO proposals(id,project,request,payload,expires,status) VALUES(?,?,?,?,?,'pending')",(uuid.uuid4().hex,project,request,json.dumps(reply.tasks),time.time()+600))
            return {'status':'completed','project':project}
        finally:
            self.active=None
    def close(self):
        self.closing=True
        self.cancel()
        # Wait for the real worker before destroying the Store. No false remote-stop claim.
        self.pool.shutdown(wait=True,cancel_futures=True)
        self.poll()

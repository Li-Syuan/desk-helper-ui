import concurrent.futures
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from desk_helper_ui.backends import Reply,load_backend,validate_reply
from desk_helper_ui.core import Store,Engine,BusyError

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=Store(self.temp.name)
        self.engine=Engine(self.store);self.project=self.store.projects()[0]['id']
    def tearDown(self):
        self.engine.close();self.store.close();self.temp.cleanup()
    def complete(self):
        for _ in range(200):
            result=self.engine.poll()
            if result:return result
            time.sleep(.005)
        self.fail('worker did not finish')
    def proposal(self):
        self.engine.send(self.project,'/task Review result');self.assertEqual(self.complete()['status'],'completed')
        return self.store.proposals(self.project)[0]
    def test_demo_chat_is_local_and_persistent(self):
        self.engine.send(self.project,'Hello');self.complete()
        self.assertIn('Offline demo',self.store.messages(self.project)[1]['content'])
        self.store.close();self.store=Store(self.temp.name);self.engine.store=self.store
        self.assertEqual(len(self.store.messages(self.project)),2)
    def test_project_history_tasks_and_context_are_isolated(self):
        other=self.store.create_project('Other');self.engine.send(self.project,'Hello');self.complete()
        self.store.add_task(self.project,'Private to first project')
        self.assertEqual(self.store.messages(other),[]);self.assertEqual(self.store.context(other),[]);self.assertEqual(self.store.tasks(other),[])
        with self.assertRaises(ValueError):self.store.set_done(other,self.store.tasks(self.project)[0]['id'],True)
    def test_no_tool_before_approval_and_repeat_is_one_receipt(self):
        p=self.proposal();self.assertEqual(self.store.tasks(self.project),[])
        ids=self.store.approve(self.project,p['id'],expected_payload=p['payload'])
        self.assertEqual(self.store.approve(self.project,p['id']),ids);self.assertEqual(len(self.store.tasks(self.project)),1)
    def test_decline_expiry_wrong_project_and_changed_preview(self):
        p=self.proposal();other=self.store.create_project('Other')
        with self.assertRaises(ValueError):self.store.approve(other,p['id'])
        with self.assertRaises(ValueError):self.store.approve(self.project,p['id'],now=p['expires'])
        with self.assertRaises(ValueError):self.store.approve(self.project,p['id'],expected_payload='different')
        self.store.decline(self.project,p['id'])
        with self.assertRaises(ValueError):self.store.approve(self.project,p['id'])
        self.assertEqual(self.store.tasks(self.project),[])
    def test_cancellation_blocks_repeat_until_worker_finishes_and_fences_reply(self):
        started=threading.Event();release=threading.Event()
        class Slow:
            name='slow fixture'
            def reply(self,*args):started.set();release.wait(3);return Reply('Late',('Must not create',))
        self.engine.backend=Slow();self.engine.send(self.project,'Hello');self.assertTrue(started.wait(1));self.engine.cancel()
        with self.assertRaises(BusyError):self.engine.send(self.project,'Again')
        release.set();self.assertEqual(self.complete()['status'],'cancelled')
        self.assertEqual(len(self.store.messages(self.project)),1);self.assertEqual(self.store.proposals(self.project),[])
    def test_backend_failure_has_no_fallback_or_raw_error(self):
        class Bad:
            name='failure fixture'
            def reply(self,*args):raise RuntimeError('private provider error')
        self.engine.backend=Bad();self.engine.send(self.project,'Hello');result=self.complete()
        self.assertEqual(result['status'],'failed');self.assertNotIn('private',str(result));self.assertEqual(len(self.store.messages(self.project)),1)
    def test_reply_validation_rejects_invalid_payloads(self):
        for reply in (None,Reply(''),Reply('text',['task']),Reply('text',('bad\ncontrol',)),Reply('x',tuple('x' for _ in range(6)))):
            with self.subTest(reply=reply),self.assertRaises(ValueError):validate_reply(reply)
    def test_invalid_inputs_do_not_create_work(self):
        for value in ('',' '*5,'x'*6001):
            with self.assertRaises(ValueError):self.engine.send(self.project,value)
        with self.assertRaises(ValueError):self.store.create_project('')
        with self.assertRaises(ValueError):self.store.add_task(self.project,'')
        self.assertEqual(self.store.messages(self.project),[])
    def test_manual_completion_only_updates_selected_task(self):
        one=self.store.add_task(self.project,'One');two=self.store.add_task(self.project,'Two')
        self.store.set_done(self.project,one,True)
        self.assertEqual([t['done'] for t in self.store.tasks(self.project)],[1,0])
    def test_interrupted_request_is_retained_without_replay(self):
        with self.store.db:self.store.db.execute("INSERT INTO requests VALUES('interrupted',?,'running')",(self.project,))
        self.store.close();self.store=Store(self.temp.name);self.engine.store=self.store
        self.assertEqual(self.store.db.execute("SELECT status FROM requests WHERE id='interrupted'").fetchone()[0],'interrupted')
        self.assertIsNone(self.engine.active)
    def test_explicit_backend_swap_uses_the_plugin(self):
        self.engine.backend=load_backend(Path(__file__).resolve().parents[1]/'examples/custom_backend.py')
        self.engine.send(self.project,'Hello');self.complete()
        self.assertEqual(self.store.messages(self.project)[1]['content'],'Custom backend received: Hello')
    def test_backend_initialization_error_is_redacted(self):
        plugin=Path(self.temp.name)/'bad.py'
        plugin.write_text("def create_backend(): raise RuntimeError('private fixture detail')\n",encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'^backend_initialization_failed$'):
            load_backend(plugin)

    def test_sql_characters_are_plain_text(self):
        title="Don't run SQL; DROP TABLE tasks;"
        self.store.add_task(self.project,title);self.assertEqual(self.store.tasks(self.project)[0]['title'],title)
    def test_transaction_prevents_duplicate_approval_between_connections(self):
        p=self.proposal()
        def confirm():
            connection=Store(self.temp.name)
            try:return connection.approve(self.project,p['id'])
            finally:connection.close()
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda _:confirm(),range(2)))
        self.assertEqual(results[0],results[1]);self.assertEqual(len(self.store.tasks(self.project)),1)

if __name__=='__main__':unittest.main()

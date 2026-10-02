"""Tk desktop UI; all backend I/O runs outside the UI thread."""
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from .core import Engine, Store

class App:
    def __init__(self, root, directory, backend=None):
        self.root=root
        self.store=Store(directory)
        self.engine=Engine(self.store,backend)
        self.project=self.store.projects()[0]['id']
        self.drafts={}
        self._after=None
        self.root.title('desk helper ui')
        self.root.geometry('1080x720')
        self.root.minsize(760,520)
        style=ttk.Style(root)
        style.theme_use('clam')
        style.configure('TFrame',background='#edf2f7')
        style.configure('TLabel',background='#edf2f7',foreground='#1c2940',font=('Segoe UI',10))
        style.configure('Title.TLabel',font=('Segoe UI',19,'bold'))
        style.configure('TButton',padding=7,font=('Segoe UI',10))
        shell=ttk.Frame(root,padding=16);shell.pack(fill='both',expand=True)
        ttk.Label(shell,text='desk helper ui',style='Title.TLabel').pack(anchor='w')
        ttk.Label(shell,text=self.engine.backend.name).pack(anchor='w',pady=(2,12))
        body=ttk.Frame(shell);body.pack(fill='both',expand=True)
        left=ttk.Frame(body,padding=(0,0,14,0));left.pack(side='left',fill='y')
        ttk.Label(left,text='Projects').pack(anchor='w')
        self.projects=tk.Listbox(left,width=22,exportselection=False,height=10)
        self.projects.pack(fill='y',expand=True,pady=6)
        self.projects.bind('<<ListboxSelect>>',lambda e:self.switch_project())
        self.project_name=ttk.Entry(left,width=22);self.project_name.pack(fill='x')
        ttk.Button(left,text='Create project',command=self.create_project).pack(fill='x',pady=6)
        right=ttk.Frame(body);right.pack(side='left',fill='both',expand=True)
        tabs=ttk.Notebook(right);self.tabs=tabs;tabs.pack(fill='both',expand=True)
        chat=ttk.Frame(tabs,padding=12);todo=ttk.Frame(tabs,padding=12)
        tabs.add(chat,text='Chat & history');tabs.add(todo,text='Tasks & confirmed tools')
        transcript_frame=ttk.Frame(chat);transcript_frame.pack(fill='both',expand=True)
        self.transcript=tk.Text(transcript_frame,wrap='word',state='disabled',font=('Segoe UI',11),padx=12,pady=12,background='#ffffff',relief='flat')
        self.transcript.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(transcript_frame,command=self.transcript.yview);scroll.pack(side='right',fill='y')
        self.transcript.configure(yscrollcommand=scroll.set,width=30,height=10)
        self.input=tk.Text(chat,height=4,wrap='word',font=('Segoe UI',11));self.input.pack(fill='x',pady=(10,6))
        buttons=ttk.Frame(chat);buttons.pack(fill='x')
        self.send_button=ttk.Button(buttons,text='Send',command=self.send);self.send_button.pack(side='right')
        self.cancel_button=ttk.Button(buttons,text='Cancel request',command=self.cancel);self.cancel_button.pack(side='right',padx=8)
        ttk.Label(buttons,text='Demo tool: /task Your next step').pack(side='left')
        # Reserve input/actions before allowing transcript to expand.
        transcript_frame.pack_forget();self.input.pack_forget();buttons.pack_forget()
        buttons.pack(side='bottom',fill='x')
        self.input.pack(side='bottom',fill='x',pady=(10,6))
        transcript_frame.pack(fill='both',expand=True)
        manual_label=ttk.Label(todo,text='Manual tasks — completion is your decision',wraplength=400)
        manual_label.pack(anchor='w')
        self.task_list=tk.Listbox(todo,exportselection=False,font=('Segoe UI',11),height=9);self.task_list.pack(fill='both',expand=True,pady=8)
        manual=ttk.Frame(todo);manual.pack(fill='x')
        self.task_title=ttk.Entry(manual);self.task_title.pack(side='left',fill='x',expand=True)
        ttk.Button(manual,text='Add task',command=self.add_task).pack(side='left',padx=6)
        ttk.Button(manual,text='Toggle done',command=self.toggle_done).pack(side='left')
        proposal_label=ttk.Label(todo,text='Tool proposals — no task is created before confirmation',wraplength=400)
        proposal_label.pack(anchor='w',pady=(15,5))
        self.proposals=tk.Listbox(todo,exportselection=False,height=5,font=('Segoe UI',10));self.proposals.pack(fill='both',expand=True)
        actions=ttk.Frame(todo);actions.pack(fill='x',pady=8)
        self.confirm_button=ttk.Button(actions,text='Review & confirm',command=self.approve)
        self.confirm_button.pack(side='left')
        self.decline_button=ttk.Button(actions,text='Decline',command=self.decline)
        self.decline_button.pack(side='left',padx=8)
        # Grid fixes footer visibility while only the two lists consume spare height.
        for child in todo.winfo_children():child.pack_forget()
        for row,widget in enumerate((manual_label,self.task_list,manual,proposal_label,self.proposals,actions)):
            widget.grid(row=row,column=0,sticky='nsew',pady=4)
        todo.columnconfigure(0,weight=1)
        todo.rowconfigure(1,weight=3,minsize=45);todo.rowconfigure(4,weight=1,minsize=35)
        self.status=tk.StringVar(value='Ready. Local workspace; demo uses no network.')
        status_label=ttk.Label(shell,textvariable=self.status,wraplength=650)
        body.pack_forget();status_label.pack(side='bottom',fill='x',pady=(10,0))
        body.pack(fill='both',expand=True)
        self.refresh_projects()
        self.refresh()
        root.protocol('WM_DELETE_WINDOW',self.close)
        self.tick()
    def refresh_projects(self):
        self.project_rows=self.store.projects()
        self.projects.delete(0,'end')
        for row in self.project_rows:self.projects.insert('end',row['name'])
        index=next(i for i,r in enumerate(self.project_rows) if r['id']==self.project)
        self.projects.selection_set(index)
    def refresh(self):
        self.transcript.configure(state='normal');self.transcript.delete('1.0','end')
        for m in self.store.messages(self.project):
            self.transcript.insert('end',m['role'].title()+' ['+m['status']+']\n'+m['content']+'\n\n')
        self.transcript.configure(state='disabled');self.transcript.see('end')
        self.task_rows=self.store.tasks(self.project);self.task_list.delete(0,'end')
        for t in self.task_rows:self.task_list.insert('end',('[done] ' if t['done'] else '[todo] ')+t['title'])
        self.proposal_rows=self.store.proposals(self.project);self.proposals.delete(0,'end')
        for p in self.proposal_rows:self.proposals.insert('end','Create local tasks: '+', '.join(json.loads(p['payload'])))
    def switch_project(self):
        selected=self.projects.curselection()
        if not selected:return
        self.drafts[self.project]=self.input.get('1.0','end-1c')
        self.project=self.project_rows[selected[0]]['id']
        self.input.delete('1.0','end');self.input.insert('1.0',self.drafts.get(self.project,''))
        self.refresh()
    def create_project(self):
        try:
            new=self.store.create_project(self.project_name.get())
            self.drafts[self.project]=self.input.get('1.0','end-1c')
            self.project=new;self.input.delete('1.0','end');self.project_name.delete(0,'end')
            self.refresh_projects();self.refresh()
        except ValueError as e:self.status.set(str(e))
    def send(self):
        try:
            self.engine.send(self.project,self.input.get('1.0','end-1c'))
            self.input.delete('1.0','end');self.drafts[self.project]=''
            self.status.set('Working. Cancel fences local results; a backend may still be running.')
            self.send_button.configure(state='disabled');self.refresh()
        except ValueError as e:self.status.set(str(e))
    def cancel(self):
        self.engine.cancel();self.status.set('Cancel requested. Waiting for the actual backend to finish.');self.refresh()
    def add_task(self):
        try:self.store.add_task(self.project,self.task_title.get());self.task_title.delete(0,'end');self.refresh()
        except ValueError as e:self.status.set(str(e))
    def toggle_done(self):
        selected=self.task_list.curselection()
        if not selected:self.status.set('Select a task.');return
        task=self.task_rows[selected[0]]
        self.store.set_done(self.project,task['id'],not bool(task['done']));self.refresh()
    def approve(self):
        selected=self.proposals.curselection()
        if not selected:self.status.set('Select a proposal.');return
        p=self.proposal_rows[selected[0]]
        titles=json.loads(p['payload'])
        if not messagebox.askyesno('Confirm local tool', 'Create these local tasks?\n\n'+'\n'.join(titles)+'\n\nNo shell, network or schedule operation.',parent=self.root,default='no'):return
        try:self.store.approve(self.project,p['id'],expected_payload=p['payload']);self.status.set('Confirmed once. Tasks created locally.');self.refresh()
        except ValueError as e:self.status.set(str(e))
    def decline(self):
        selected=self.proposals.curselection()
        if not selected:self.status.set('Select a proposal.');return
        try:self.store.decline(self.project,self.proposal_rows[selected[0]]['id']);self.refresh()
        except ValueError as e:self.status.set(str(e))
    def tick(self):
        result=self.engine.poll()
        if result:
            self.status.set('Request '+result['status']+'. No automatic retry or fallback.')
            self.refresh()
        self.send_button.configure(state='disabled' if self.engine.active else 'normal')
        self._after=self.root.after(60,self.tick)
    def close(self):
        self.root.after_cancel(self._after)
        self.engine.closing=True;self.engine.cancel()
        self.status.set('Closing after the backend worker finishes; no new operations accepted.')
        self.send_button.configure(state='disabled')
        def drain():
            self.engine.poll()
            if self.engine.active:self.root.after(60,drain);return
            self.engine.close();self.store.close();self.root.destroy()
        drain()

import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch
from desk_helper_ui.app import App

class UITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=tk.Tk();self.app=App(self.root,self.temp.name);self.root.update()
    def tearDown(self):
        if self.app.engine.active:
            self.app.engine.cancel()
            for _ in range(200):
                if self.app.engine.poll():break
                time.sleep(.005)
        self.app.close();self.temp.cleanup()
    def wait(self):
        for _ in range(200):
            self.root.update()
            if not self.app.engine.active:return
            time.sleep(.01)
        self.fail('UI request timeout')
    def select_project(self,index):
        self.app.projects.selection_clear(0,'end');self.app.projects.selection_set(index);self.app.switch_project();self.root.update()
    def test_chat_and_repeated_send_create_one_request(self):
        self.app.input.insert('1.0','Hello');self.app.send();self.app.input.insert('1.0','Must remain draft');self.app.send()
        self.wait();self.assertEqual(len(self.app.store.messages(self.app.project)),2)
        self.assertEqual(self.app.input.get('1.0','end-1c'),'Must remain draft')
        self.assertIn('Offline demo',self.app.transcript.get('1.0','end'))
    def test_project_navigation_preserves_each_draft(self):
        self.app.input.insert('1.0','First draft');self.app.project_name.insert(0,'Second');self.app.create_project()
        self.app.input.insert('1.0','Second draft');self.select_project(0)
        self.assertEqual(self.app.input.get('1.0','end-1c'),'First draft');self.select_project(1)
        self.assertEqual(self.app.input.get('1.0','end-1c'),'Second draft')
    def test_confirmation_cancel_then_confirm_and_manual_done(self):
        self.app.input.insert('1.0','/task Review');self.app.send();self.wait();self.app.proposals.selection_set(0)
        with patch('desk_helper_ui.app.messagebox.askyesno',return_value=False):self.app.approve()
        self.assertEqual(self.app.store.tasks(self.app.project),[])
        with patch('desk_helper_ui.app.messagebox.askyesno',return_value=True):self.app.approve()
        self.assertEqual(len(self.app.store.tasks(self.app.project)),1)
        self.app.approve();self.assertEqual(len(self.app.store.tasks(self.app.project)),1)
        self.app.task_list.selection_set(0);self.app.toggle_done();self.assertEqual(self.app.store.tasks(self.app.project)[0]['done'],1)
    def test_empty_inputs_selection_and_decline_do_not_create_work(self):
        self.app.send();self.app.add_task();self.app.toggle_done();self.app.approve();self.app.decline();self.app.create_project()
        self.assertEqual(self.app.store.tasks(self.app.project),[]);self.assertEqual(self.app.store.messages(self.app.project),[])
        self.app.input.insert('1.0','/task Decline');self.app.send();self.wait();self.app.proposals.selection_set(0);self.app.decline()
        self.assertEqual(self.app.store.proposals(self.app.project),[])
    def test_small_and_large_window_controls_are_reachable(self):
        for geometry in ('760x520','1280x800'):
            self.root.geometry(geometry);self.root.update()
            button=self.app.send_button
            self.assertTrue(button.winfo_ismapped())
            self.assertTrue(self.app.cancel_button.winfo_ismapped())
            self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())
            self.assertLessEqual(button.winfo_rootx()+button.winfo_width(),self.root.winfo_rootx()+self.root.winfo_width())
            self.app.tabs.select(1);self.root.update()
            for control in (self.app.task_title,self.app.confirm_button,self.app.decline_button):
                self.assertTrue(control.winfo_ismapped())
                self.assertLessEqual(control.winfo_rooty()+control.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())
                self.assertLessEqual(control.winfo_rootx()+control.winfo_width(),self.root.winfo_rootx()+self.root.winfo_width())
            self.app.tabs.select(0);self.root.update()
    def test_plain_text_never_becomes_markup_or_command(self):
        self.app.input.insert('1.0','<script>alert(1)</script>');self.app.send();self.wait()
        self.assertIn('<script>',self.app.transcript.get('1.0','end'))
        self.assertEqual(self.app.store.tasks(self.app.project),[])

if __name__=='__main__':unittest.main()

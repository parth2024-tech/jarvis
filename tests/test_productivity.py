import unittest
import sys
import os
import time

sys.path.append("/home/thor/Desktop/JARVIS/core")
from productivity import (
    set_timer, get_active_timers, cancel_timer,
    add_todo, list_todos, complete_todo, clear_completed_todos,
    get_clipboard_text, set_clipboard_text
)

class TestProductivity(unittest.TestCase):
    def test_timers(self):
        # Set short timer
        res = set_timer(10, label="Test Timer")
        self.assertTrue(res["success"])
        timer_id = res["timer_id"]
        self.assertEqual(res["label"], "Test Timer")

        # Check active timers
        active = get_active_timers()
        ids = [t["id"] for t in active]
        self.assertIn(timer_id, ids)

        # Cancel timer
        cancel_res = cancel_timer(timer_id)
        self.assertTrue(cancel_res["success"])

        # Check it's gone
        active_after = get_active_timers()
        ids_after = [t["id"] for t in active_after]
        self.assertNotIn(timer_id, ids_after)

    def test_todos(self):
        # Add todo
        res = add_todo("Calibrate Repulsor Capacitors", priority="high")
        self.assertTrue(res["success"])
        todo_id = res["id"]
        self.assertGreater(todo_id, 0)

        # List todos
        todos = list_todos(include_completed=False)
        task_ids = [t["id"] for t in todos]
        self.assertIn(todo_id, task_ids)

        # Complete todo
        comp_res = complete_todo(todo_id)
        self.assertTrue(comp_res["success"])

        # List should no longer include in pending
        todos_pending = list_todos(include_completed=False)
        pending_ids = [t["id"] for t in todos_pending]
        self.assertNotIn(todo_id, pending_ids)

        # Clear completed
        clear_res = clear_completed_todos()
        self.assertTrue(clear_res["success"])

    def test_clipboard(self):
        test_payload = f"JARVIS_CLIP_VERIFICATION_{int(time.time())}"
        set_res = set_clipboard_text(test_payload)
        self.assertIn("success", set_res)

        get_res = get_clipboard_text()
        self.assertIn("success", get_res)
        if get_res["success"]:
            self.assertEqual(get_res["text"], test_payload)

if __name__ == "__main__":
    unittest.main()

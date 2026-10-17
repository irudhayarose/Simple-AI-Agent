"""
test_agent.py - Unit and integration tests for tools and agent logic.
"""

import os
import unittest
from tools import (
    calculate,
    get_current_time,
    search_wikipedia,
    search_web,
    save_note,
    read_note,
    list_notes,
    TOOL_REGISTRY,
    NOTES_DIR,
)
from agent import SimpleAgent


class TestAgentTools(unittest.TestCase):
    def test_calculate_basic(self):
        result = calculate("12 + 34 * 2")
        self.assertEqual(result, "80")

    def test_calculate_math_funcs(self):
        result = calculate("sqrt(144) + 10")
        self.assertEqual(result, "22.0")

    def test_calculate_division_by_zero(self):
        result = calculate("10 / 0")
        self.assertIn("Division by zero", result)

    def test_get_current_time(self):
        result = get_current_time()
        self.assertIn("Current date and time", result)

    def test_notes_crud(self):
        title = "unit_test_note"
        content = "Testing notes persistence."
        save_res = save_note(title, content)
        self.assertIn("Successfully saved note", save_res)

        read_res = read_note(title)
        self.assertEqual(read_res, content)

        list_res = list_notes()
        self.assertIn(f"{title}.txt", list_res)

        # Cleanup
        filepath = os.path.join(NOTES_DIR, f"{title}.txt")
        if os.path.exists(filepath):
            os.remove(filepath)

    def test_mock_agent_math(self):
        agent = SimpleAgent(mock=True, verbose=False)
        ans = agent.run("calculate 50 * 2")
        self.assertIn("100", ans)

    def test_mock_agent_time(self):
        agent = SimpleAgent(mock=True, verbose=False)
        ans = agent.run("What date and time is it?")
        self.assertIn("Current date and time", ans)


if __name__ == "__main__":
    unittest.main()

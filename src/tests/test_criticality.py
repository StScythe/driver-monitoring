# -*- coding: utf-8 -*-
"""
Тесты оценки критичности.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dms.criticality import CriticalityEvaluator


class TestCriticality(unittest.TestCase):
    """Тесты оценки критичности."""

    def setUp(self):
        self.eval = CriticalityEvaluator()

    def test_normal(self):
        """Нет событий — NORMAL."""
        level, messages = self.eval.evaluate(False, False, False, False, 'normal')
        self.assertEqual(level, 0)

    def test_yawn_warning(self):
        """Только зевок — WARNING."""
        level, messages = self.eval.evaluate(True, False, False, False, 'normal')
        self.assertEqual(level, 1)

    def test_drowsiness_danger(self):
        """Сонливость — DANGER."""
        level, messages = self.eval.evaluate(False, True, False, False, 'normal')
        self.assertEqual(level, 2)

    def test_yawn_drowsiness_critical(self):
        """Зевок + сонливость — CRITICAL."""
        level, messages = self.eval.evaluate(True, True, False, False, 'normal')
        self.assertEqual(level, 3)

    def test_perclos_critical(self):
        """PERCLOS critical — CRITICAL."""
        level, messages = self.eval.evaluate(False, False, False, False, 'critical')
        self.assertEqual(level, 3)


if __name__ == "__main__":
    unittest.main()
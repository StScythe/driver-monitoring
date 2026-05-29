# -*- coding: utf-8 -*-
"""
Тесты калькулятора PERCLOS.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dms.perclos import PERCLOSCalculator


class TestPERCLOS(unittest.TestCase):
    """Тесты калькулятора PERCLOS."""

    def test_perclos_range(self):
        """PERCLOS всегда в диапазоне 0-100%."""
        calc = PERCLOSCalculator(window_seconds=3, fps=10)
        calc.set_ear_threshold(0.20)

        for _ in range(30):
            calc.add_frame(0.30)
        self.assertAlmostEqual(calc.calculate(), 0.0, delta=0.5)

        for _ in range(30):
            calc.add_frame(0.10)
        perclos = calc.calculate()
        self.assertAlmostEqual(perclos, 100.0, delta=0.5)
        self.assertLessEqual(perclos, 100.0)

    def test_perclos_scrolling(self):
        """Скользящее окно работает корректно."""
        calc = PERCLOSCalculator(window_seconds=3, fps=10)
        calc.set_ear_threshold(0.20)

        for _ in range(30):
            calc.add_frame(0.10)
        self.assertGreater(calc.calculate(), 90.0)

        for _ in range(30):
            calc.add_frame(0.30)
        self.assertAlmostEqual(calc.calculate(), 0.0, delta=0.5)

    def test_perclos_reset(self):
        """Сброс истории."""
        calc = PERCLOSCalculator(window_seconds=3, fps=10)
        calc.set_ear_threshold(0.20)

        for _ in range(30):
            calc.add_frame(0.10)
        self.assertGreater(calc.calculate(), 90.0)

        calc.reset()
        self.assertEqual(calc.calculate(), 0.0)


if __name__ == "__main__":
    unittest.main()
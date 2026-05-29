# -*- coding: utf-8 -*-
"""
Тесты логики политопной детекции.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dms.polytope import Polytope1D, Polytope2D


class TestPolytopeLogic(unittest.TestCase):
    """Тесты логики политопной детекции."""

    def test_polytope_1d_above(self):
        """1D-политоп: все значения >= порога."""
        p = Polytope1D(window_size=5, threshold=30.0, mode='above')

        for val in [35, 32, 31, 33]:
            p.add_frame(val)
        self.assertFalse(p.check())

        p.add_frame(30)
        self.assertTrue(p.check())

        p.add_frame(25)
        self.assertFalse(p.check())

    def test_polytope_1d_below(self):
        """1D-политоп: все значения < порога."""
        p = Polytope1D(window_size=5, threshold=0.18, mode='below')

        for val in [0.10, 0.12, 0.15, 0.17, 0.16]:
            p.add_frame(val)
        self.assertTrue(p.check())

        p.add_frame(0.20)
        self.assertFalse(p.check())

    def test_polytope_2d_yawn(self):
        """2D-политоп: оба параметра >= порогов."""
        p = Polytope2D(window_size=5, mar_threshold=0.50,
                       nose_chin_threshold=1.10)

        for i in range(5):
            p.add_frame(0.55, 1.15)
        self.assertTrue(p.check())

        p.add_frame(0.45, 1.15)
        self.assertFalse(p.check())

    def test_polytope_2d_partial(self):
        """2D-политоп: только одно условие — нет срабатывания."""
        p = Polytope2D(window_size=5, mar_threshold=0.50,
                       nose_chin_threshold=1.20)

        for i in range(5):
            p.add_frame(0.55, 1.05)
        self.assertFalse(p.check())


if __name__ == "__main__":
    unittest.main()
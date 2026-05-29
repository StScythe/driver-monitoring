# -*- coding: utf-8 -*-
"""
Тесты математических формул.
"""

import unittest
import numpy as np


class TestFormulas(unittest.TestCase):
    """Тесты математических формул."""

    def test_mar_dlib_style(self):
        """
        Тест формулы MAR Dlib-стиль с тремя вертикальными замерами.
        MAR = (|P80-P82| + |P13-P14| + |P312-P317|) / (3 * |P78-P308|)
        """
        def pt(x, y):
            return np.array([x, y])

        v_left = np.linalg.norm(pt(0, 0) - pt(0, 1))
        v_center = np.linalg.norm(pt(0, 0) - pt(0, 2))
        v_right = np.linalg.norm(pt(0, 0) - pt(0, 1))
        horizontal = np.linalg.norm(pt(0, 0) - pt(100, 0))

        mar = (v_left + v_center + v_right) / (3.0 * horizontal)
        self.assertAlmostEqual(mar, 0.0133, delta=0.001)

    def test_ear_formula(self):
        """Тест формулы EAR."""
        pts = np.array([
            [0, 5],     # p1
            [2, 4],     # p2
            [4, 4],     # p3
            [6, 5],     # p4
            [4, 6],     # p5
            [2, 6]      # p6
        ], dtype=float)

        vertical = (np.linalg.norm(pts[1] - pts[5]) +
                    np.linalg.norm(pts[2] - pts[4]))
        horizontal = 2.0 * np.linalg.norm(pts[0] - pts[3])
        ear = vertical / (horizontal + 1e-6)

        self.assertAlmostEqual(ear, 0.33, delta=0.02)

    def test_nose_chin_formula(self):
        """Тест формулы расстояния нос-подбородок."""
        nose = np.array([0, 0])
        chin = np.array([0, 100])
        left_eye = np.array([-50, -30])
        right_eye = np.array([50, -30])

        absolute = np.linalg.norm(nose - chin)
        face_w = np.linalg.norm(left_eye - right_eye)
        dist = absolute / face_w

        self.assertAlmostEqual(dist, 1.0, delta=0.01)

    def test_coefficient_k_calculation(self):
        """Тест расчета коэффициента K."""
        yawn_values = np.array([0.5, 0.6, 0.7, 0.8, 0.9])
        no_yawn_values = np.array([0.04, 0.05, 0.06, 0.07, 0.08])

        yawn_p25 = np.percentile(yawn_values, 25)
        no_yawn_median = np.median(no_yawn_values)

        K_mar = yawn_p25 / no_yawn_median if no_yawn_median > 0 else 1.0

        self.assertGreater(K_mar, 1.0)
        self.assertAlmostEqual(K_mar, 10.0, delta=0.5)


if __name__ == "__main__":
    unittest.main()
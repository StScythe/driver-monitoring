# -*- coding: utf-8 -*-
"""
Тесты операций с базой данных.
"""

import unittest
import tempfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dms.database import DatabaseManager
from dms.config import SystemConfig


class TestDatabase(unittest.TestCase):
    """Тесты операций с базой данных."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, "test.db")

        # Создаем конфиг с тестовой БД
        self.config = SystemConfig()
        self.original_db_path = self.config.DB_PATH
        self.config.DB_PATH = self.test_db

        self.db = DatabaseManager(self.config)

    def tearDown(self):
        self.config.DB_PATH = self.original_db_path
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_profile_save_load(self):
        """Сохранение и загрузка профиля."""
        profile = {
            'driver_id': 'test_driver',
            'ear_baseline': 0.30,
            'mar_baseline': 0.07,
            'nose_chin_baseline': 0.85,
            'ear_threshold': 0.18,
            'mar_threshold': 0.51,
            'nose_chin_threshold': 1.17,
            'calibration_date': '2026-05-06'
        }
        self.db.save_driver_profile(profile)
        loaded = self.db.get_driver_profile('test_driver')

        self.assertIsNotNone(loaded)
        self.assertAlmostEqual(loaded['mar_threshold'], 0.51, delta=0.01)

    def test_monitoring_save(self):
        """Сохранение данных мониторинга с флагами событий."""
        profile = {
            'driver_id': 'driver_1',
            'ear_baseline': 0.30, 'mar_baseline': 0.07,
            'nose_chin_baseline': 0.85, 'ear_threshold': 0.18,
            'mar_threshold': 0.51, 'nose_chin_threshold': 1.17,
            'calibration_date': '2026-05-06'
        }
        self.db.save_driver_profile(profile)

        self.db.save_monitoring_data(
            driver_id='driver_1',
            metrics={'ear': 0.25, 'mar': 0.07, 'nose_chin': 0.85,
                     'yaw': 5.0, 'roll': 2.0},
            perclos_value=15.5, fatigue_level='light',
            criticality_level=1,
            yawn_detected=False, distraction_detected=False,
            roll_detected=False, drowsiness_detected=False
        )

        import sqlite3
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM monitoring_data")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
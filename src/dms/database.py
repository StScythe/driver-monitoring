# -*- coding: utf-8 -*-
"""
Управление SQLite базой данных.
"""

import sqlite3
from datetime import datetime


class DatabaseManager:
    """
    Управление SQLite базой данных.

    Таблицы:
      - driver_profiles: профили водителей (калибровка)
      - monitoring_data: данные мониторинга с расширенными полями
      - detected_events: события детекции (зевки, сонливость и т.д.)
    """

    def __init__(self, config):
        self.config = config
        self._init_database()

    def _init_database(self):
        """Инициализация таблиц базы данных."""
        conn = sqlite3.connect(self.config.DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS driver_profiles (
                driver_id TEXT PRIMARY KEY,
                ear_baseline REAL,
                mar_baseline REAL,
                nose_chin_baseline REAL,
                ear_threshold REAL,
                mar_threshold REAL,
                nose_chin_threshold REAL,
                calibration_date TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id TEXT,
                timestamp TEXT,
                ear_value REAL,
                mar_value REAL,
                nose_chin_value REAL,
                yaw_value REAL,
                roll_value REAL,
                perclos_value REAL,
                fatigue_level TEXT,
                criticality_level INTEGER,
                yawn_detected INTEGER,
                distraction_detected INTEGER,
                roll_detected INTEGER,
                drowsiness_detected INTEGER,
                FOREIGN KEY (driver_id) REFERENCES driver_profiles (driver_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detected_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id TEXT,
                session_id TEXT,
                event_type TEXT,
                start_time REAL,
                end_time REAL,
                duration REAL,
                timestamp TEXT,
                FOREIGN KEY (driver_id) REFERENCES driver_profiles (driver_id)
            )
        ''')

        conn.commit()
        conn.close()
        print(f"База данных инициализирована: {self.config.DB_PATH}")

    def save_driver_profile(self, profile):
        """Сохранение профиля водителя."""
        conn = sqlite3.connect(self.config.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO driver_profiles
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            profile['driver_id'],
            profile['ear_baseline'],
            profile['mar_baseline'],
            profile['nose_chin_baseline'],
            profile['ear_threshold'],
            profile['mar_threshold'],
            profile['nose_chin_threshold'],
            profile['calibration_date']
        ))
        conn.commit()
        conn.close()

    def get_driver_profile(self, driver_id):
        """Получение профиля водителя."""
        conn = sqlite3.connect(self.config.DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM driver_profiles WHERE driver_id = ?", (driver_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'driver_id': row[0],
                'ear_baseline': row[1],
                'mar_baseline': row[2],
                'nose_chin_baseline': row[3],
                'ear_threshold': row[4],
                'mar_threshold': row[5],
                'nose_chin_threshold': row[6],
                'calibration_date': row[7]
            }
        return None

    def save_monitoring_data(self, driver_id, metrics, perclos_value,
                             fatigue_level, criticality_level,
                             yawn_detected, distraction_detected,
                             roll_detected, drowsiness_detected):
        """Сохранение данных мониторинга."""
        conn = sqlite3.connect(self.config.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO monitoring_data
            (driver_id, timestamp, ear_value, mar_value, nose_chin_value,
             yaw_value, roll_value, perclos_value, fatigue_level,
             criticality_level, yawn_detected, distraction_detected,
             roll_detected, drowsiness_detected)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            driver_id,
            datetime.now().isoformat(),
            metrics['ear'],
            metrics['mar'],
            metrics['nose_chin'],
            metrics.get('yaw', 0),
            metrics.get('roll', 0),
            perclos_value,
            fatigue_level,
            criticality_level,
            int(yawn_detected),
            int(distraction_detected),
            int(roll_detected),
            int(drowsiness_detected)
        ))
        conn.commit()
        conn.close()

    def save_event(self, driver_id, session_id, event_type, start_time, end_time, duration):
        """Сохранение события детекции."""
        conn = sqlite3.connect(self.config.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO detected_events
            (driver_id, session_id, event_type, start_time, end_time, duration, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            driver_id, session_id, event_type, start_time, end_time, duration,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    def get_session_events(self, session_id):
        """Получение событий по сессии."""
        conn = sqlite3.connect(self.config.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT event_type, start_time, end_time, duration
            FROM detected_events
            WHERE session_id = ?
            ORDER BY start_time
        ''', (session_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows
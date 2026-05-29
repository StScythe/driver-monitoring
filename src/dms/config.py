# -*- coding: utf-8 -*-
"""
Конфигурация системы мониторинга усталости.
"""

import os
import json
import numpy as np


class SystemConfig:
    """
    Конфигурация системы мониторинга усталости.

    Загружает научные коэффициенты из JSON-файла.
    Содержит индексы ключевых точек MediaPipe и параметры систем.
    """

    # Индексы точек MediaPipe для MAR (Dlib-стиль, 3 вертикальных замера)
    MAR_TOP_LEFT = 80
    MAR_BOTTOM_LEFT = 82
    MAR_TOP_CENTER = 13
    MAR_BOTTOM_CENTER = 14
    MAR_TOP_RIGHT = 312
    MAR_BOTTOM_RIGHT = 317
    MAR_LEFT_CORNER = 78
    MAR_RIGHT_CORNER = 308

    # Индексы точек для EAR
    LEFT_EYE_IDX = [362, 385, 387, 263, 373, 380]
    RIGHT_EYE_IDX = [33, 160, 158, 133, 153, 144]

    # Индексы для расстояния нос-подбородок
    NOSE_TIP_IDX = 1
    CHIN_IDX = 152
    LEFT_EYE_OUTER = 33
    RIGHT_EYE_OUTER = 263

    # Индексы для позы головы
    POSE_IDS = [1, 152, 33, 263, 61, 291]

    # 3D-модель для solvePnP
    FACE_3D = np.array([
        [0.0, 0.0, 0.0],
        [0.0, -330.0, -65.0],
        [-225.0, 170.0, -135.0],
        [225.0, 170.0, -135.0],
        [-150.0, -150.0, -125.0],
        [150.0, -150.0, -125.0]
    ], dtype=np.float64)

    # Параметры системы
    CALIBRATION_SECONDS = 30
    FPS_TARGET = 30

    # Окна политопов
    YAWN_WINDOW = 15         # 0.5 сек — зевок
    STATE_WINDOW = 60        # 2 сек — сонливость, отвлечение, наклон

    # Фиксированные пороги для позы головы
    YAW_THRESHOLD = 30.0     # градусов
    ROLL_THRESHOLD = 20.0    # градусов

    # Порог EAR (фиксированный коэффициент из литературы)
    K_EAR = 0.6

    def __init__(self):
        # Определяем путь к файлу коэффициентов относительно этого файла
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.COEFFICIENTS_PATH = os.path.join(base_dir, "data", "scientific_coefficients.json")
        self.DB_PATH = os.path.join(base_dir, "driver_fatigue_monitoring.db")

        self.load_coefficients()

    def load_coefficients(self):
        """Загрузка научных коэффициентов из JSON файла."""
        if not os.path.exists(self.COEFFICIENTS_PATH):
            print(f"Внимание: файл {self.COEFFICIENTS_PATH} не найден.")
            print("Используются коэффициенты по умолчанию.")
            self.K_MAR = 7.26
            self.K_NOSE_CHIN = 1.38
            return

        with open(self.COEFFICIENTS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        coefficients = data.get('coefficients', {})
        self.K_MAR = coefficients.get('K_mar', {}).get('value', 7.26)
        self.K_NOSE_CHIN = coefficients.get('K_nose_chin_distance', {}).get('value', 1.38)

        print(f"Коэффициенты загружены: K_MAR={self.K_MAR:.2f}, "
              f"K_NOSE_CHIN={self.K_NOSE_CHIN:.2f}")
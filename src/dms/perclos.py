# -*- coding: utf-8 -*-
"""
Калькулятор метрики PERCLOS (без DEQ).
"""

from collections import deque
import time


class PERCLOSCalculator:
    """
    Калькулятор метрики PERCLOS.

    PERCLOS — процент времени, в течение которого глаза были закрыты
    в скользящем окне заданной длительности.

    Пороги усталости:
      - normal: PERCLOS < 10%
      - light: 10% ≤ PERCLOS < 20%
      - medium: 20% ≤ PERCLOS < 28%
      - critical: PERCLOS ≥ 28% (с подтверждением ≥ 2 сек)
    """

    def __init__(self, window_seconds=30, fps=30):
        self.window_size = window_seconds * fps
        self.ear_threshold = None
        self.ear_history = deque(maxlen=self.window_size)
        self.closed_history = deque(maxlen=self.window_size)
        self.confirmed_critical = False
        self.critical_start_time = 0

    def set_ear_threshold(self, threshold):
        """Установить индивидуальный порог EAR."""
        self.ear_threshold = threshold

    def add_frame(self, ear_value):
        """Добавить кадр в историю."""
        if self.ear_threshold is None:
            return

        is_closed = ear_value < self.ear_threshold
        self.ear_history.append(ear_value)
        self.closed_history.append(is_closed)

    def calculate(self):
        """Расчет текущего PERCLOS."""
        if len(self.closed_history) == 0:
            return 0.0
        return (sum(self.closed_history) / len(self.closed_history)) * 100

    def get_level(self):
        """Определение уровня усталости по PERCLOS."""
        perclos = self.calculate()

        if perclos >= 28:
            current_time = time.time()
            if not self.confirmed_critical:
                self.confirmed_critical = True
                self.critical_start_time = current_time
                return 'medium'
            elif current_time - self.critical_start_time >= 2.0:
                return 'critical'
            else:
                return 'medium'
        else:
            self.confirmed_critical = False
            if perclos >= 20:
                return 'medium'
            elif perclos >= 10:
                return 'light'
            else:
                return 'normal'

    def reset(self):
        """Сброс истории (при новой калибровке)."""
        self.ear_history.clear()
        self.closed_history.clear()
        self.confirmed_critical = False
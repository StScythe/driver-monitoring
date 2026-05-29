# -*- coding: utf-8 -*-
"""
Политопные детекторы для систем мониторинга.
"""

from collections import deque


class Polytope1D:
    """
    Одномерный политоп для детекции превышения порога.

    Используется для:
      - Отвлечения внимания (|yaw| > порог, mode='above')
      - Наклона головы (|roll| > порог, mode='above')
      - Сонливости (EAR < порог, mode='below')

    Событие фиксируется, если ВСЕ кадры в окне удовлетворяют условию.
    """

    def __init__(self, window_size, threshold, mode='above'):
        """
        Аргументы:
            window_size: размер окна в кадрах
            threshold: пороговое значение
            mode: 'above' — значение >= порога, 'below' — значение < порога
        """
        self.window_size = window_size
        self.threshold = threshold
        self.mode = mode
        self.buffer = deque(maxlen=window_size)

    def add_frame(self, value):
        """Добавление значения в буфер."""
        self.buffer.append(value)

    def is_full(self):
        """Заполнено ли окно полностью."""
        return len(self.buffer) >= self.window_size

    def check(self):
        """
        Проверка условия для всего окна.
        Возвращает True, если все значения в окне удовлетворяют условию.
        """
        if not self.is_full():
            return False
        if self.mode == 'above':
            return min(self.buffer) >= self.threshold
        else:
            return max(self.buffer) < self.threshold


class Polytope2D:
    """
    Двумерный политоп для детекции зевка.

    Измерения:
      - MAR (открытость рта)
      - Расстояние нос-подбородок (опускание челюсти)

    Зевок фиксируется, если ОБА параметра >= порогов
    для ВСЕХ кадров в окне.
    """

    def __init__(self, window_size, mar_threshold, nose_chin_threshold):
        self.window_size = window_size
        self.mar_threshold = mar_threshold
        self.nose_chin_threshold = nose_chin_threshold
        self.mar_buffer = deque(maxlen=window_size)
        self.nose_chin_buffer = deque(maxlen=window_size)

    def add_frame(self, mar, nose_chin):
        """Добавление кадра в буферы."""
        self.mar_buffer.append(mar)
        self.nose_chin_buffer.append(nose_chin)

    def is_full(self):
        """Заполнено ли окно полностью."""
        return len(self.mar_buffer) >= self.window_size

    def check(self):
        """
        Проверка зевка: оба параметра >= порогов для всего окна.
        """
        if not self.is_full():
            return False
        return (
            min(self.mar_buffer) >= self.mar_threshold and
            min(self.nose_chin_buffer) >= self.nose_chin_threshold
        )
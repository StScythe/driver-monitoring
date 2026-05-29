# -*- coding: utf-8 -*-
"""
Оценка критичности состояния водителя.
"""


class CriticalityEvaluator:
    """
    Оценка критичности состояния водителя.

    Уровни критичности:
      0 - NORMAL:    нет событий
      1 - WARNING:   одно событие (зевок ИЛИ отвлечение)
      2 - DANGER:    сонливость ИЛИ наклон ИЛИ зевок+отвлечение
      3 - CRITICAL:  два события одновременно ИЛИ PERCLOS≥28%
    """

    def __init__(self):
        self.level = 0
        self.messages = []
        self.level_names = {0: 'NORMAL', 1: 'WARNING', 2: 'DANGER', 3: 'CRITICAL'}

    def evaluate(self, yawn_detected, drowsiness_detected,
                 distraction_detected, roll_detected, perclos_level):
        """
        Оценка критичности на основе флагов детекции и PERCLOS.
        """
        self.messages = []
        criticality_score = 0

        # Сбор активных событий
        if yawn_detected:
            self.messages.append("YAWN DETECTED")
            criticality_score += 1

        if drowsiness_detected:
            self.messages.append("DROWSINESS: eyes closed")
            criticality_score += 2

        if distraction_detected:
            self.messages.append("DISTRACTION: head turned")
            criticality_score += 1

        if roll_detected:
            self.messages.append("HEAD ROLL: head tilted")
            criticality_score += 2

        # PERCLOS
        if perclos_level == 'critical':
            self.messages.append("PERCLOS CRITICAL (>28%)")
            criticality_score = max(criticality_score, 3)
        elif perclos_level == 'medium':
            if "DROWSINESS" not in str(self.messages):
                self.messages.append("FATIGUE MEDIUM")
            criticality_score = max(criticality_score, 2)

        # Комбинации событий
        if yawn_detected and drowsiness_detected:
            self.messages.append("CRITICAL: yawn + drowsiness")
            criticality_score = max(criticality_score, 3)

        if distraction_detected and drowsiness_detected:
            self.messages.append("CRITICAL: distraction + drowsiness")
            criticality_score = max(criticality_score, 3)

        if roll_detected and drowsiness_detected:
            self.messages.append("CRITICAL: head roll + drowsiness")
            criticality_score = max(criticality_score, 3)

        # Определение уровня
        if criticality_score >= 3:
            self.level = 3
        elif criticality_score == 2:
            self.level = 2
        elif criticality_score == 1:
            self.level = 1
        else:
            self.level = 0
            if not self.messages:
                self.messages.append("NORMAL")

        return self.level, self.messages

    def get_level_name(self):
        """Возвращает название текущего уровня."""
        return self.level_names.get(self.level, 'UNKNOWN')

    def get_color(self):
        """Возвращает цвет для визуализации (BGR)."""
        colors = {
            0: (0, 255, 0),      # зеленый
            1: (0, 255, 255),    # желтый
            2: (0, 165, 255),    # оранжевый
            3: (0, 0, 255)       # красный
        }
        return colors.get(self.level, (255, 255, 255))
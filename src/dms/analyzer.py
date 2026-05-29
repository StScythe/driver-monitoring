# -*- coding: utf-8 -*-
"""
Анализатор состояния водителя с полной логикой политопной детекции и физических таймеров.
"""

import uuid
from collections import deque

from dms.perclos import PERCLOSCalculator
from dms.criticality import CriticalityEvaluator
from dms.polytope import Polytope1D, Polytope2D


class FatigueAnalyzer:
    """
    Анализатор состояния водителя.

    Объединяет четыре системы политопной детекции и PERCLOS.
    Оценивает критичность состояния на основе сочетаний событий.
    """

    def __init__(self, config):
        self.config = config
        self.perclos_calc = PERCLOSCalculator(
            window_seconds=30,
            fps=config.FPS_TARGET
        )
        self.criticality_eval = CriticalityEvaluator()

        # Политопные детекторы (инициализируются после калибровки)
        self.polytope_yawn = None
        self.polytope_drowsiness = None
        self.polytope_distraction = None
        self.polytope_roll = None
        self.initialized = False

        # Для отслеживания состояния политопов (активно ли событие)
        self.event_active = {
            'yawn': False,
            'drowsiness': False,
            'distraction': False,
            'roll': False
        }

        # Физические таймеры для отслеживания реальной длительности
        self.physical_start = {
            'yawn': None,
            'drowsiness': None,
            'distraction': None,
            'roll': None
        }

        # Флаги для отслеживания, выведено ли уже сообщение о начале
        self.physical_start_reported = {
            'yawn': False,
            'drowsiness': False,
            'distraction': False,
            'roll': False
        }

        self.frame_time = 1.0 / config.FPS_TARGET
        self.session_id = None
        self.current_events = []  # Для хранения событий текущей сессии
        self.frame_count = 0

    def start_new_session(self):
        """Начать новую сессию мониторинга."""
        self.session_id = str(uuid.uuid4())
        self.current_events = []
        self.frame_count = 0
        # Сбрасываем все таймеры
        self.event_active = {k: False for k in self.event_active}
        self.physical_start = {k: None for k in self.physical_start}
        self.physical_start_reported = {k: False for k in self.physical_start_reported}
        print(f"Новая сессия: {self.session_id}")

    def get_elapsed_time(self):
        """Получить прошедшее время в секундах с начала сессии."""
        return self.frame_count * self.frame_time

    def initialize(self, profile):
        """
        Инициализация политопных детекторов с порогами из профиля.
        """
        if profile is None:
            return

        self.perclos_calc.set_ear_threshold(profile['ear_threshold'])
        self.perclos_calc.reset()

        self.polytope_yawn = Polytope2D(
            window_size=self.config.YAWN_WINDOW,
            mar_threshold=profile['mar_threshold'],
            nose_chin_threshold=profile['nose_chin_threshold']
        )
        self.polytope_drowsiness = Polytope1D(
            window_size=self.config.STATE_WINDOW,
            threshold=profile['ear_threshold'],
            mode='below'
        )
        self.polytope_distraction = Polytope1D(
            window_size=self.config.STATE_WINDOW,
            threshold=self.config.YAW_THRESHOLD,
            mode='above'
        )
        self.polytope_roll = Polytope1D(
            window_size=self.config.STATE_WINDOW,
            threshold=self.config.ROLL_THRESHOLD,
            mode='above'
        )
        self.initialized = True

    def force_end_all_events(self, current_time):
        """Принудительно завершить все активные события (при остановке мониторинга)."""
        for event_type in ['yawn', 'drowsiness', 'distraction', 'roll']:
            if self.event_active.get(event_type, False):
                # Завершаем событие
                self.event_active[event_type] = False

                # Если есть физическое начало, используем его
                if self.physical_start[event_type] is not None:
                    duration = current_time - self.physical_start[event_type]

                    # Проверяем минимальную длительность
                    min_duration = 0.5 if event_type == 'yawn' else 2.0

                    if duration >= min_duration:
                        event = {
                            'type': event_type,
                            'start': self.physical_start[event_type],
                            'end': current_time,
                            'duration': duration,
                            'physical_frames': int(duration * self.config.FPS_TARGET),
                            'polytope_window': self.config.YAWN_WINDOW if event_type == 'yawn' else self.config.STATE_WINDOW
                        }
                        self.current_events.append(event)
                        print(f"[СОБЫТИЕ] {event_type} принудительно завершено при остановке, физическая длительность: {duration:.2f} сек")

                # Сбрасываем таймеры
                self.physical_start[event_type] = None
                self.physical_start_reported[event_type] = False

    def analyze(self, metrics):
        """
        Анализ одного кадра.
        """
        if not self.initialized:
            return 'unknown', 0, ["SYSTEM NOT CALIBRATED"], {}

        self.frame_count += 1
        current_time_abs = self.get_elapsed_time()

        ear = metrics['ear']
        mar = metrics['mar']
        nose_chin = metrics['nose_chin']
        yaw = metrics.get('yaw', 0)
        roll = metrics.get('roll', 0)

        # Обновление PERCLOS
        self.perclos_calc.add_frame(ear)
        perclos_value = self.perclos_calc.calculate()
        perclos_level = self.perclos_calc.get_level()

        # Обновление политопных детекторов
        self.polytope_yawn.add_frame(mar, nose_chin)
        yaw_abs = abs(yaw) if yaw is not None else 0
        roll_abs = abs(roll) if roll is not None else 0
        self.polytope_drowsiness.add_frame(ear)
        self.polytope_distraction.add_frame(yaw_abs)
        self.polytope_roll.add_frame(roll_abs)

        # Проверка состояния политопов (окно заполнено)
        yawn_detected = self.polytope_yawn.check()
        drowsiness_detected = self.polytope_drowsiness.check()
        distraction_detected = self.polytope_distraction.check()
        roll_detected = self.polytope_roll.check()

        # Физические условия (превышение порога в текущем кадре)
        mar_above = mar >= self.polytope_yawn.mar_threshold
        nose_chin_above = nose_chin >= self.polytope_yawn.nose_chin_threshold
        yawn_physical = mar_above and nose_chin_above

        ear_below = ear < self.polytope_drowsiness.threshold
        yaw_above = yaw_abs >= self.polytope_distraction.threshold
        roll_above = roll_abs >= self.polytope_roll.threshold

        # ==================== ЗЕВОК ====================
        # Отслеживаем физическое начало (один раз за событие)
        if yawn_physical and not self.physical_start_reported['yawn']:
            self.physical_start['yawn'] = current_time_abs
            self.physical_start_reported['yawn'] = True
            print(f"[ФИЗИЧЕСКОЕ] Зевок начался в {current_time_abs:.1f} сек")

        # Физическое окончание
        if not yawn_physical and self.physical_start_reported['yawn']:
            physical_duration = current_time_abs - self.physical_start['yawn']
            if physical_duration >= 0.5:  # Минимум 0.5 сек (15 кадров)
                # Сохраняем для отчета
                self._last_yawn_physical_duration = physical_duration
                self._last_yawn_physical_start = self.physical_start['yawn']
                self._last_yawn_physical_end = current_time_abs
                self._last_yawn_physical_frames = int(physical_duration * self.config.FPS_TARGET)
            self.physical_start['yawn'] = None
            self.physical_start_reported['yawn'] = False

        # Политоп сработал (окно заполнилось)
        if yawn_detected and not self.event_active['yawn']:
            self.event_active['yawn'] = True
            print(f"[СОБЫТИЕ] Зевок ЗАФИКСИРОВАН (политоп сработал) в {current_time_abs:.1f} сек")

        elif not yawn_physical and self.event_active['yawn']:
            self.event_active['yawn'] = False

            if hasattr(self, '_last_yawn_physical_duration'):
                event = {
                    'type': 'yawn',
                    'start': self._last_yawn_physical_start,
                    'end': self._last_yawn_physical_end,
                    'duration': self._last_yawn_physical_duration,
                    'physical_frames': self._last_yawn_physical_frames,
                    'polytope_window': self.config.YAWN_WINDOW
                }
                self.current_events.append(event)
                print(f"[СОБЫТИЕ] Зевок закончился, физическая длительность: {event['duration']:.2f} сек ({event['physical_frames']} кадров)")

                # Очищаем
                del self._last_yawn_physical_duration
                del self._last_yawn_physical_start
                del self._last_yawn_physical_end
                del self._last_yawn_physical_frames

        # ==================== СОНЛИВОСТЬ ====================
        if ear_below and not self.physical_start_reported['drowsiness']:
            self.physical_start['drowsiness'] = current_time_abs
            self.physical_start_reported['drowsiness'] = True
            print(f"[ФИЗИЧЕСКОЕ] Сонливость началась в {current_time_abs:.1f} сек")

        if not ear_below and self.physical_start_reported['drowsiness']:
            physical_duration = current_time_abs - self.physical_start['drowsiness']
            if physical_duration >= 2.0:
                self._last_drowsiness_physical_duration = physical_duration
                self._last_drowsiness_physical_start = self.physical_start['drowsiness']
                self._last_drowsiness_physical_end = current_time_abs
                self._last_drowsiness_physical_frames = int(physical_duration * self.config.FPS_TARGET)
                print(f"[ФИЗИЧЕСКОЕ] Сонливость закончилась, физическая длительность: {physical_duration:.2f} сек")
            self.physical_start['drowsiness'] = None
            self.physical_start_reported['drowsiness'] = False

        if drowsiness_detected and not self.event_active['drowsiness']:
            self.event_active['drowsiness'] = True
            print(f"[СОБЫТИЕ] Сонливость ЗАФИКСИРОВАНА (политоп сработал) в {current_time_abs:.1f} сек")

        elif not ear_below and self.event_active['drowsiness']:
            self.event_active['drowsiness'] = False

            if hasattr(self, '_last_drowsiness_physical_duration'):
                event = {
                    'type': 'drowsiness',
                    'start': self._last_drowsiness_physical_start,
                    'end': self._last_drowsiness_physical_end,
                    'duration': self._last_drowsiness_physical_duration,
                    'physical_frames': self._last_drowsiness_physical_frames,
                    'polytope_window': self.config.STATE_WINDOW
                }
                self.current_events.append(event)
                print(f"[СОБЫТИЕ] Сонливость закончилась, физическая длительность: {event['duration']:.2f} сек ({event['physical_frames']} кадров)")

                del self._last_drowsiness_physical_duration
                del self._last_drowsiness_physical_start
                del self._last_drowsiness_physical_end
                del self._last_drowsiness_physical_frames

        # ==================== ОТВЛЕЧЕНИЕ ====================
        if yaw_above and not self.physical_start_reported['distraction']:
            self.physical_start['distraction'] = current_time_abs
            self.physical_start_reported['distraction'] = True
            print(f"[ФИЗИЧЕСКОЕ] Отвлечение началось в {current_time_abs:.1f} сек")

        if not yaw_above and self.physical_start_reported['distraction']:
            physical_duration = current_time_abs - self.physical_start['distraction']
            if physical_duration >= 2.0:
                self._last_distraction_physical_duration = physical_duration
                self._last_distraction_physical_start = self.physical_start['distraction']
                self._last_distraction_physical_end = current_time_abs
                self._last_distraction_physical_frames = int(physical_duration * self.config.FPS_TARGET)
                print(f"[ФИЗИЧЕСКОЕ] Отвлечение закончилось, физическая длительность: {physical_duration:.2f} сек")
            self.physical_start['distraction'] = None
            self.physical_start_reported['distraction'] = False

        if distraction_detected and not self.event_active['distraction']:
            self.event_active['distraction'] = True
            print(f"[СОБЫТИЕ] Отвлечение ЗАФИКСИРОВАНО (политоп сработал) в {current_time_abs:.1f} сек")

        elif not yaw_above and self.event_active['distraction']:
            self.event_active['distraction'] = False

            if hasattr(self, '_last_distraction_physical_duration'):
                event = {
                    'type': 'distraction',
                    'start': self._last_distraction_physical_start,
                    'end': self._last_distraction_physical_end,
                    'duration': self._last_distraction_physical_duration,
                    'physical_frames': self._last_distraction_physical_frames,
                    'polytope_window': self.config.STATE_WINDOW
                }
                self.current_events.append(event)
                print(f"[СОБЫТИЕ] Отвлечение закончилось, физическая длительность: {event['duration']:.2f} сек ({event['physical_frames']} кадров)")

                del self._last_distraction_physical_duration
                del self._last_distraction_physical_start
                del self._last_distraction_physical_end
                del self._last_distraction_physical_frames

        # ==================== НАКЛОН ГОЛОВЫ ====================
        if roll_above and not self.physical_start_reported['roll']:
            self.physical_start['roll'] = current_time_abs
            self.physical_start_reported['roll'] = True
            print(f"[ФИЗИЧЕСКОЕ] Наклон головы начался в {current_time_abs:.1f} сек")

        if not roll_above and self.physical_start_reported['roll']:
            physical_duration = current_time_abs - self.physical_start['roll']
            if physical_duration >= 2.0:
                self._last_roll_physical_duration = physical_duration
                self._last_roll_physical_start = self.physical_start['roll']
                self._last_roll_physical_end = current_time_abs
                self._last_roll_physical_frames = int(physical_duration * self.config.FPS_TARGET)
                print(f"[ФИЗИЧЕСКОЕ] Наклон головы закончился, физическая длительность: {physical_duration:.2f} сек")
            self.physical_start['roll'] = None
            self.physical_start_reported['roll'] = False

        if roll_detected and not self.event_active['roll']:
            self.event_active['roll'] = True
            print(f"[СОБЫТИЕ] Наклон головы ЗАФИКСИРОВАН (политоп сработал) в {current_time_abs:.1f} сек")

        elif not roll_above and self.event_active['roll']:
            self.event_active['roll'] = False

            if hasattr(self, '_last_roll_physical_duration'):
                event = {
                    'type': 'roll',
                    'start': self._last_roll_physical_start,
                    'end': self._last_roll_physical_end,
                    'duration': self._last_roll_physical_duration,
                    'physical_frames': self._last_roll_physical_frames,
                    'polytope_window': self.config.STATE_WINDOW
                }
                self.current_events.append(event)
                print(f"[СОБЫТИЕ] Наклон головы закончился, физическая длительность: {event['duration']:.2f} сек ({event['physical_frames']} кадров)")

                del self._last_roll_physical_duration
                del self._last_roll_physical_start
                del self._last_roll_physical_end
                del self._last_roll_physical_frames

        # Оценка критичности (используем политопные флаги)
        criticality_level, messages = self.criticality_eval.evaluate(
            yawn_detected=yawn_detected,
            drowsiness_detected=drowsiness_detected,
            distraction_detected=distraction_detected,
            roll_detected=roll_detected,
            perclos_level=perclos_level
        )

        flags = {
            'yawn': yawn_detected,
            'drowsiness': drowsiness_detected,
            'distraction': distraction_detected,
            'roll': roll_detected,
            'perclos_value': perclos_value
        }

        return perclos_level, criticality_level, messages, flags

    def get_session_events(self):
        """Получить все события текущей сессии."""
        return self.current_events

    def save_events_to_db(self, db_manager, driver_id):
        """Сохранить события в базу данных."""
        for event in self.current_events:
            db_manager.save_event(
                driver_id=driver_id,
                session_id=self.session_id,
                event_type=event['type'],
                start_time=event['start'],
                end_time=event['end'],
                duration=event['duration']
            )
        print(f"Сохранено {len(self.current_events)} событий в базу данных")

    def print_events_summary(self):
        """Вывести сводку по событиям в консоль."""
        if not self.current_events:
            print("Событий не зафиксировано")
            return

        print("\n" + "=" * 60)
        print("СВОДКА ПОЛИТОПНЫХ СОБЫТИЙ ЗА СЕССИЮ")
        print("=" * 60)

        event_names = {
            'yawn': 'Зевок',
            'drowsiness': 'Сонливость (закрытые глаза)',
            'distraction': 'Отвлечение (поворот головы)',
            'roll': 'Наклон головы'
        }

        for i, event in enumerate(self.current_events, 1):
            name = event_names.get(event['type'], event['type'])
            window_size = event['polytope_window']
            min_duration = 0.5 if event['type'] == 'yawn' else 2.0

            print(f"\n{i}. {name}:")
            print(f"   Политопное окно: {window_size} кадров ({min_duration:.1f} сек)")
            print(f"   Начало события (физическое): {event['start']:.1f} сек")
            print(f"   Конец события (физический): {event['end']:.1f} сек")
            print(f"   Длительность события: {event['duration']:.2f} сек")
            print(f"   (превышение порога в течение {event['physical_frames']} кадров)")
            print(f"   Политоп сработал, когда окно из {window_size} кадров заполнилось")
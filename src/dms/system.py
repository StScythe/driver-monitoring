# -*- coding: utf-8 -*-
"""
Основная система мониторинга усталости водителя.
"""

import cv2
import time

from dms.config import SystemConfig
from dms.extractor import FaceMetricsExtractor
from dms.database import DatabaseManager
from dms.calibrator import Calibrator
from dms.analyzer import FatigueAnalyzer
from dms.visualizer import Visualizer
from dms.reporter import ReportGenerator


class FatigueMonitoringSystem:
    """
    Основная система мониторинга усталости водителя.
    """

    def __init__(self):
        self.config = SystemConfig()
        self.extractor = FaceMetricsExtractor(self.config)
        self.db_manager = DatabaseManager(self.config)
        self.calibrator = Calibrator(self.config, self.db_manager)
        self.analyzer = FatigueAnalyzer(self.config)
        self.visualizer = Visualizer(self.config)
        self.report_generator = ReportGenerator(self.config, self.db_manager)

        self.current_driver = None
        self.current_profile = None
        self.monitoring_active = False

    def identify_driver(self):
        """Идентификация водителя."""
        driver_id = input("Введите ID водителя: ").strip()

        profile = self.db_manager.get_driver_profile(driver_id)

        if profile:
            print(f"Водитель {driver_id} найден в базе данных")
            self.current_driver = driver_id
            self.current_profile = profile
            self.analyzer.initialize(profile)
            return driver_id
        else:
            print(f"Водитель {driver_id} не найден. Требуется калибровка.")
            response = input("Выполнить калибровку? (да/нет): ").strip().lower()
            if response == 'да':
                profile = self.calibrator.calibrate(driver_id)
                if profile:
                    self.current_driver = driver_id
                    self.current_profile = profile
                    self.analyzer.initialize(profile)
                    return driver_id
            return None

    def monitor(self):
        """Запуск мониторинга в реальном времени."""
        if self.current_driver is None:
            print("Ошибка: водитель не идентифицирован")
            return

        print(f"\nЗапуск мониторинга для водителя {self.current_driver}")
        print("Нажмите 'q' или ESC для остановки\n")

        # НОВОЕ: Начинаем новую сессию
        self.analyzer.start_new_session()

        self.extractor.initialize()
        cap = cv2.VideoCapture()
        mjpg_fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
        cap.set(cv2.CAP_PROP_FOURCC, mjpg_fourcc)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.open(0, cv2.CAP_DSHOW)

        if not cap.isOpened():
            print("Ошибка: не удалось открыть камеру")
            self.extractor.release()
            return

        time.sleep(1)
        for _ in range(15):
            cap.read()

        self.monitoring_active = True

        try:
            while self.monitoring_active:
                ret, frame = cap.read()
                if not ret:
                    continue

                h, w = frame.shape[:2]
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.extractor.face_mesh.process(rgb_frame)

                if results.multi_face_landmarks:
                    landmarks = results.multi_face_landmarks[0].landmark

                    mar = self.extractor.compute_mar(landmarks, w, h)
                    ear_l = self.extractor.compute_ear(
                        landmarks, self.config.LEFT_EYE_IDX, w, h)
                    ear_r = self.extractor.compute_ear(
                        landmarks, self.config.RIGHT_EYE_IDX, w, h)
                    ear = (ear_l + ear_r) / 2.0
                    nose_chin = self.extractor.compute_nose_chin(landmarks, w, h)
                    yaw, pitch, roll = self.extractor.get_head_pose(landmarks, h, w)

                    metrics = {
                        'ear': ear,
                        'mar': mar,
                        'nose_chin': nose_chin,
                        'yaw': yaw if yaw is not None else 0,
                        'roll': roll if roll is not None else 0
                    }

                    perclos_level, criticality_level, messages, flags = \
                        self.analyzer.analyze(metrics)

                    self.db_manager.save_monitoring_data(
                        driver_id=self.current_driver,
                        metrics=metrics,
                        perclos_value=flags.get('perclos_value', 0),
                        fatigue_level=perclos_level,
                        criticality_level=criticality_level,
                        yawn_detected=flags.get('yawn', False),
                        distraction_detected=flags.get('distraction', False),
                        roll_detected=flags.get('roll', False),
                        drowsiness_detected=flags.get('drowsiness', False)
                    )

                    display_frame = self.visualizer.draw_results(
                        frame, landmarks, metrics, self.current_profile,
                        perclos_level, criticality_level, messages, flags
                    )
                    cv2.imshow('Fatigue Monitoring System', display_frame)
                else:
                    cv2.putText(frame, "No face detected", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.imshow('Fatigue Monitoring System', frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:
                    self.monitoring_active = False
                    print("\nМониторинг остановлен.")
                if cv2.getWindowProperty('Fatigue Monitoring System',
                                         cv2.WND_PROP_VISIBLE) < 1:
                    self.monitoring_active = False
                    print("\nОкно закрыто. Мониторинг остановлен.")

        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.extractor.release()
            cv2.waitKey(100)

            # Принудительно завершаем все активные события
            current_time = self.analyzer.get_elapsed_time()
            self.analyzer.force_end_all_events(current_time)

            # Сохраняем события в БД и выводим сводку
            self.analyzer.save_events_to_db(self.db_manager, self.current_driver)
            self.analyzer.print_events_summary()

    def generate_report(self):
        """Генерация отчета."""
        if self.current_driver is None:
            driver_id = input("Введите ID водителя: ").strip()
        else:
            driver_id = self.current_driver

        if not driver_id:
            print("ID водителя не указан.")
            return

        # Проверяем, есть ли профиль в БД
        profile = self.db_manager.get_driver_profile(driver_id)
        if profile is None:
            print(f"Водитель {driver_id} не найден в базе данных.")
            print("Сначала выполните калибровку (опция 1).")
            return

        date = input("Введите дату (ГГГГ-ММ-ДД) или Enter для всех данных: ").strip()
        date = date if date else None

        self.report_generator.generate_report(driver_id, date)
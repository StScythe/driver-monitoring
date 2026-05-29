# -*- coding: utf-8 -*-
import time
import cv2
import numpy as np
from datetime import datetime
from dms.extractor import FaceMetricsExtractor


class Calibrator:
    def __init__(self, config, db_manager):
        self.config = config
        self.db_manager = db_manager
        self.extractor = FaceMetricsExtractor(config)

    def calibrate(self, driver_id):
        print(f"\nКалибровка водителя {driver_id}")
        print("Смотрите в камеру 30 секунд. Глаза открыты, рот закрыт.")
        print("Сохраняйте нейтральное положение головы.\n")

        cap = cv2.VideoCapture()
        mjpg_fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
        cap.set(cv2.CAP_PROP_FOURCC, mjpg_fourcc)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.open(0, cv2.CAP_DSHOW)

        if not cap.isOpened():
            print("Ошибка: не удалось открыть камеру")
            return None
        # Даем камере время на инициализацию
        time.sleep(1)
        # Сбрасываем буфер (пропускаем проблемные первые кадры)
        for _ in range(15):
            cap.read()

        self.extractor.initialize()

        ear_samples = []
        mar_samples = []
        nose_chin_samples = []

        start_time = time.time()

        while time.time() - start_time < self.config.CALIBRATION_SECONDS:
            ret, frame = cap.read()
            if not ret:
                continue

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.extractor.face_mesh.process(rgb_frame)

            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                h, w = frame.shape[:2]

                mar = self.extractor.compute_mar(landmarks, w, h)
                ear_l = self.extractor.compute_ear(
                    landmarks, self.config.LEFT_EYE_IDX, w, h
                )
                ear_r = self.extractor.compute_ear(
                    landmarks, self.config.RIGHT_EYE_IDX, w, h
                )
                ear = (ear_l + ear_r) / 2.0
                nose_chin = self.extractor.compute_nose_chin(landmarks, w, h)

                # Фильтр: глаза открыты (EAR > 0.20), рот закрыт (MAR < 0.09)
                if ear > 0.20 and mar < 0.09:
                    ear_samples.append(ear)
                    mar_samples.append(mar)
                    nose_chin_samples.append(nose_chin)

            # Отображение обратного отсчета
            elapsed = int(time.time() - start_time)
            remaining = self.config.CALIBRATION_SECONDS - elapsed

            display_frame = frame.copy()
            cv2.putText(display_frame, f"Calibration: {remaining}s", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(display_frame, f"Samples: {len(ear_samples)}", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow('Calibration', display_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        self.extractor.release()

        if len(ear_samples) < 50:
            print(f"\nНедостаточно образцов: {len(ear_samples)}. "
                  f"Требуется минимум 50.")
            return None

        # Расчет базовых значений (медианы)
        ear_baseline = np.median(ear_samples)
        mar_baseline = np.median(mar_samples)
        nose_chin_baseline = np.median(nose_chin_samples)

        # Расчет индивидуальных порогов
        ear_threshold = ear_baseline * self.config.K_EAR
        mar_threshold = mar_baseline * self.config.K_MAR
        nose_chin_threshold = nose_chin_baseline * self.config.K_NOSE_CHIN

        profile = {
            'driver_id': driver_id,
            'ear_baseline': float(ear_baseline),
            'mar_baseline': float(mar_baseline),
            'nose_chin_baseline': float(nose_chin_baseline),
            'ear_threshold': float(ear_threshold),
            'mar_threshold': float(mar_threshold),
            'nose_chin_threshold': float(nose_chin_threshold),
            'calibration_date': datetime.now().isoformat()
        }

        # Сохранение профиля
        self.db_manager.save_driver_profile(profile)

        print(f"\nКалибровка завершена. ID: {driver_id}")
        print(f"Базовые значения:")
        print(f"  EAR={ear_baseline:.4f}, MAR={mar_baseline:.4f}, "
              f"Расстояние={nose_chin_baseline:.4f}")
        print(f"Пороги:")
        print(f"  EAR={ear_threshold:.4f}, MAR={mar_threshold:.4f}, "
              f"Расстояние={nose_chin_threshold:.4f}")

        return profile
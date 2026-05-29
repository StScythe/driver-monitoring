# -*- coding: utf-8 -*-
"""
Визуализатор результатов на кадре с полной сеткой MediaPipe.
"""

import cv2
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2


class Visualizer:
    """
    Визуализатор результатов на кадре.
    Отрисовывает полную сетку лица MediaPipe.
    """

    def __init__(self, config):
        self.config = config
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_face_mesh = mp.solutions.face_mesh

    def draw_results(self, frame, landmarks, metrics, profile,
                     perclos_level, criticality_level, messages, flags):
        """
        Отрисовка результатов на кадре с полной сеткой MediaPipe.
        """
        display_frame = frame.copy()
        h, w = frame.shape[:2]

        # ===== ПОЛНАЯ СЕТКА ЛИЦА MEDIAPIPE =====
        if landmarks:
            # Создаем объект NormalizedLandmarkList
            landmark_list = landmark_pb2.NormalizedLandmarkList()
            for lm in landmarks:
                landmark_proto = landmark_list.landmark.add()
                landmark_proto.x = lm.x
                landmark_proto.y = lm.y
                landmark_proto.z = lm.z

            # Рисуем полную сетку лица (все соединения)
            self.mp_drawing.draw_landmarks(
                image=display_frame,
                landmark_list=landmark_list,
                connections=self.mp_face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec=None,
                connection_drawing_spec=self.mp_drawing.DrawingSpec(
                    color=(100, 100, 100), thickness=1, circle_radius=1
                )
            )

            # Рисуем контуры глаз (более ярко)
            self.mp_drawing.draw_landmarks(
                image=display_frame,
                landmark_list=landmark_list,
                connections=self.mp_face_mesh.FACEMESH_IRISES,
                landmark_drawing_spec=None,
                connection_drawing_spec=self.mp_drawing.DrawingSpec(
                    color=(0, 255, 0), thickness=2, circle_radius=2
                )
            )

            # Рисуем контуры губ (более ярко)
            self.mp_drawing.draw_landmarks(
                image=display_frame,
                landmark_list=landmark_list,
                connections=self.mp_face_mesh.FACEMESH_LIPS,
                landmark_drawing_spec=None,
                connection_drawing_spec=self.mp_drawing.DrawingSpec(
                    color=(0, 0, 255), thickness=2, circle_radius=2
                )
            )

        # Цветовая рамка по уровню критичности
        criticality_colors = {
            0: (0, 255, 0),      # зеленый
            1: (0, 255, 255),    # желтый
            2: (0, 165, 255),    # оранжевый
            3: (0, 0, 255)       # красный
        }
        color = criticality_colors.get(criticality_level, (255, 255, 255))
        cv2.rectangle(display_frame, (5, 5), (w-5, h-5), color, 3)

        # Сообщения в левом верхнем углу
        y_pos = 35
        max_messages = 5
        for msg in messages[:max_messages]:
            cv2.putText(display_frame, msg, (15, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
            y_pos += 25

        # Метрики в левом нижнем углу
        y_pos = h - 120
        line_height = 20

        ear_threshold = profile.get('ear_threshold', 0.18) if profile else 0.18
        mar_threshold = profile.get('mar_threshold', 0.51) if profile else 0.51

        metric_texts = [
            f"PERCLOS: {flags.get('perclos_value', 0):.1f}% ({perclos_level})",
            f"EAR: {metrics['ear']:.3f} (thr: {ear_threshold:.3f})",
            f"MAR: {metrics['mar']:.3f} (thr: {mar_threshold:.3f})",
            f"Nose-Chin: {metrics['nose_chin']:.3f}",
            f"Yaw: {metrics.get('yaw', 0):.1f}  Roll: {metrics.get('roll', 0):.1f}",
        ]

        for text in metric_texts:
            cv2.putText(display_frame, text, (15, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
            y_pos += line_height

        return display_frame
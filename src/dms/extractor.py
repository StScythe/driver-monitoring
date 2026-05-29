# -*- coding: utf-8 -*-
"""
Извлечение геометрических метрик лица.
"""

import cv2
import numpy as np
import mediapipe as mp


class FaceMetricsExtractor:
    """
    Извлечение геометрических метрик лица.

    Метрики:
      - MAR (Dlib-стиль, 3 вертикальных замера)
      - EAR (для левого и правого глаза)
      - Расстояние нос-подбородок (нормированное)
      - Yaw, Roll (поза головы)
    """

    def __init__(self, config):
        self.config = config
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = None

    def initialize(self):
        """Инициализация MediaPipe Face Mesh."""
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def release(self):
        """Освобождение ресурсов."""
        if self.face_mesh is not None:
            self.face_mesh.close()

    def compute_mar(self, landmarks, w, h):
        """
        Расчет MAR по Dlib-стилю с тремя вертикальными замерами.
        MAR = (|P80-P82| + |P13-P14| + |P312-P317|) / (3 * |P78-P308|)
        """
        def pt(idx):
            return np.array([landmarks[idx].x * w, landmarks[idx].y * h])

        v_left = np.linalg.norm(pt(self.config.MAR_TOP_LEFT) - pt(self.config.MAR_BOTTOM_LEFT))
        v_center = np.linalg.norm(pt(self.config.MAR_TOP_CENTER) - pt(self.config.MAR_BOTTOM_CENTER))
        v_right = np.linalg.norm(pt(self.config.MAR_TOP_RIGHT) - pt(self.config.MAR_BOTTOM_RIGHT))
        horizontal = np.linalg.norm(pt(self.config.MAR_LEFT_CORNER) - pt(self.config.MAR_RIGHT_CORNER))

        if horizontal < 1e-6:
            return 0.0
        return (v_left + v_center + v_right) / (3.0 * horizontal)

    def compute_ear(self, landmarks, eye_idx, w, h):
        """Расчет Eye Aspect Ratio для одного глаза."""
        pts = np.array([[landmarks[i].x * w, landmarks[i].y * h] for i in eye_idx])
        vertical = (np.linalg.norm(pts[1] - pts[5]) + np.linalg.norm(pts[2] - pts[4]))
        horizontal = 2.0 * np.linalg.norm(pts[0] - pts[3])
        return vertical / (horizontal + 1e-6)

    def compute_nose_chin(self, landmarks, w, h):
        """Расчет нормализованного расстояния нос-подбородок."""
        def pt(idx):
            return np.array([landmarks[idx].x * w, landmarks[idx].y * h])
        nose = pt(self.config.NOSE_TIP_IDX)
        chin = pt(self.config.CHIN_IDX)
        left_eye = pt(self.config.LEFT_EYE_OUTER)
        right_eye = pt(self.config.RIGHT_EYE_OUTER)
        absolute = np.linalg.norm(nose - chin)
        face_w = np.linalg.norm(left_eye - right_eye)
        return absolute / face_w if face_w > 0 else 0.85

    def get_head_pose(self, landmarks, h, w):
        """Оценка углов поворота головы (yaw, pitch, roll)."""
        pts_2d = np.array(
            [(landmarks[i].x * w, landmarks[i].y * h) for i in self.config.POSE_IDS],
            dtype=np.float64
        )
        focal = float(w)
        cam_mat = np.array([
            [focal, 0.0, float(w) / 2.0],
            [0.0, focal, float(h) / 2.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)
        dist = np.zeros((4, 1), dtype=np.float64)
        ok, rvec, _ = cv2.solvePnP(self.config.FACE_3D, pts_2d, cam_mat, dist)
        if not ok:
            return None, None, None
        rmat, _ = cv2.Rodrigues(rvec)
        angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
        return angles[1], angles[0], angles[2]  # yaw, pitch, roll
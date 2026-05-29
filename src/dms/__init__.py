# -*- coding: utf-8 -*-
"""
Driver Monitoring System (DMS) - Система мониторинга состояния водителя
Версия: 2.0 (ВКР)
"""

from dms.config import SystemConfig
from dms.extractor import FaceMetricsExtractor
from dms.polytope import Polytope1D, Polytope2D
from dms.perclos import PERCLOSCalculator
from dms.criticality import CriticalityEvaluator
from dms.database import DatabaseManager
from dms.calibrator import Calibrator
from dms.visualizer import Visualizer
from dms.reporter import ReportGenerator
from dms.analyzer import FatigueAnalyzer
from dms.system import FatigueMonitoringSystem

__version__ = "2.0.0"
__author__ = "Волков Д.В."
__all__ = [
    "SystemConfig",
    "FaceMetricsExtractor",
    "Polytope1D",
    "Polytope2D",
    "PERCLOSCalculator",
    "CriticalityEvaluator",
    "DatabaseManager",
    "Calibrator",
    "Visualizer",
    "ReportGenerator",
    "FatigueAnalyzer",
    "FatigueMonitoringSystem"
]
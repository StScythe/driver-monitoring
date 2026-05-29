# -*- coding: utf-8 -*-
"""
Генерация статистических отчетов по данным мониторинга.
"""

import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime


class ReportGenerator:
    """
    Генерация статистических отчетов по данным мониторинга.

    Формирует:
      - Текстовый отчет с распределением событий и критичности
      - Сравнение покадрового и политопного методов детекции
      - Графики динамики EAR, MAR, nose-chin, yaw/roll, PERCLOS
      - Сохранение в файлы .txt и .png
    """

    def __init__(self, config, db_manager):
        self.config = config
        self.db_manager = db_manager

    def generate_report(self, driver_id, date=None):
        """Генерация полного отчета."""
        if not driver_id:
            print("ID водителя не указан.")
            return

        print(f"\nГенерация отчета для водителя {driver_id}...")

        data = self._get_monitoring_data(driver_id, date)

        if data.empty:
            print(f"Нет данных мониторинга для водителя {driver_id}")
            return

        profile = self.db_manager.get_driver_profile(driver_id)
        statistics = self._calculate_statistics(data, profile)
        self._print_statistics(statistics)
        self._save_report(driver_id, statistics, date)
        self._plot_graphs(driver_id, data, profile, date)

    def _get_monitoring_data(self, driver_id, date=None):
        """Получение данных мониторинга из БД."""
        conn = sqlite3.connect(self.config.DB_PATH)

        if date:
            query = '''
                SELECT timestamp, ear_value, mar_value, nose_chin_value,
                       yaw_value, roll_value, perclos_value, fatigue_level,
                       criticality_level, yawn_detected, distraction_detected,
                       roll_detected, drowsiness_detected
                FROM monitoring_data
                WHERE driver_id = ? AND date(timestamp) = date(?)
                ORDER BY timestamp
            '''
            params = (driver_id, date)
        else:
            query = '''
                SELECT timestamp, ear_value, mar_value, nose_chin_value,
                       yaw_value, roll_value, perclos_value, fatigue_level,
                       criticality_level, yawn_detected, distraction_detected,
                       roll_detected, drowsiness_detected
                FROM monitoring_data
                WHERE driver_id = ?
                ORDER BY timestamp
            '''
            params = (driver_id,)

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

    def _count_events(self, detection_array):
        """Подсчет событий в бинарном массиве."""
        events = 0
        in_event = False
        for val in detection_array:
            if val and not in_event:
                events += 1
                in_event = True
            elif not val:
                in_event = False
        return events

    def _calculate_statistics(self, data, profile):
        """Расчет статистических показателей."""
        total_records = len(data)
        total_time = total_records / self.config.FPS_TARGET

        # Политопные события
        poly_yawn_events = self._count_events(data['yawn_detected'].values)
        poly_distraction_events = self._count_events(data['distraction_detected'].values)
        poly_roll_events = self._count_events(data['roll_detected'].values)
        poly_drowsiness_events = self._count_events(data['drowsiness_detected'].values)

        # Покадровые события
        if profile:
            frame_yawn = (
                (data['mar_value'].values >= profile['mar_threshold']) &
                (data['nose_chin_value'].values >= profile['nose_chin_threshold'])
            )
            frame_drowsiness = data['ear_value'].values < profile['ear_threshold']
        else:
            frame_yawn = np.zeros(total_records, dtype=bool)
            frame_drowsiness = np.zeros(total_records, dtype=bool)

        frame_distraction = np.abs(data['yaw_value'].values) >= self.config.YAW_THRESHOLD
        frame_roll = np.abs(data['roll_value'].values) >= self.config.ROLL_THRESHOLD

        frame_yawn_events = self._count_events(frame_yawn)
        frame_drowsiness_events = self._count_events(frame_drowsiness)
        frame_distraction_events = self._count_events(frame_distraction)
        frame_roll_events = self._count_events(frame_roll)

        def reduction(frame_count, poly_count):
            if frame_count == 0:
                return 100.0
            return (frame_count - poly_count) / frame_count * 100

        yawn_reduction = reduction(frame_yawn_events, poly_yawn_events)
        distraction_reduction = reduction(frame_distraction_events, poly_distraction_events)
        roll_reduction = reduction(frame_roll_events, poly_roll_events)
        drowsiness_reduction = reduction(frame_drowsiness_events, poly_drowsiness_events)

        # PERCLOS статистика
        perclos_values = data['perclos_value'].values
        avg_perclos = np.mean(perclos_values) if len(perclos_values) > 0 else 0
        max_perclos = np.max(perclos_values) if len(perclos_values) > 0 else 0
        time_high_10 = np.sum(perclos_values >= 10) / self.config.FPS_TARGET
        time_high_20 = np.sum(perclos_values >= 20) / self.config.FPS_TARGET
        time_high_28 = np.sum(perclos_values >= 28) / self.config.FPS_TARGET

        # Распределение критичности
        if 'criticality_level' in data.columns:
            crit_dist = data['criticality_level'].value_counts()
            crit_time = {}
            crit_pct = {}
            for level in [0, 1, 2, 3]:
                count = crit_dist.get(level, 0)
                crit_time[level] = count / self.config.FPS_TARGET
                crit_pct[level] = (crit_time[level] / total_time * 100) if total_time > 0 else 0
        else:
            crit_time = {0: 0, 1: 0, 2: 0, 3: 0}
            crit_pct = {0: 0, 1: 0, 2: 0, 3: 0}

        return {
            'total_time': total_time,
            'total_records': total_records,
            'poly_yawn_events': poly_yawn_events,
            'poly_distraction_events': poly_distraction_events,
            'poly_roll_events': poly_roll_events,
            'poly_drowsiness_events': poly_drowsiness_events,
            'frame_yawn_events': frame_yawn_events,
            'frame_distraction_events': frame_distraction_events,
            'frame_roll_events': frame_roll_events,
            'frame_drowsiness_events': frame_drowsiness_events,
            'yawn_reduction': yawn_reduction,
            'distraction_reduction': distraction_reduction,
            'roll_reduction': roll_reduction,
            'drowsiness_reduction': drowsiness_reduction,
            'avg_perclos': avg_perclos,
            'max_perclos': max_perclos,
            'time_high_10': time_high_10,
            'time_high_20': time_high_20,
            'time_high_28': time_high_28,
            'crit_time': crit_time,
            'crit_pct': crit_pct
        }

    def _print_statistics(self, stats):
        """Вывод статистики в консоль."""
        level_names = {0: 'NORMAL', 1: 'WARNING', 2: 'DANGER', 3: 'CRITICAL'}

        print("\n" + "=" * 60)
        print("СТАТИСТИКА МОНИТОРИНГА СОСТОЯНИЯ ВОДИТЕЛЯ")
        print("=" * 60)
        print(f"Общее время анализа: {stats['total_time']:.1f} сек")
        print(f"Всего записей: {stats['total_records']}")
        print()

        print("ОБНАРУЖЕНО СОБЫТИЙ (политопный метод):")
        print(f"  Зевки (MAR + расстояние):     {stats['poly_yawn_events']}")
        print(f"  Отвлечение внимания (|yaw|):  {stats['poly_distraction_events']}")
        print(f"  Наклоны головы (|roll|):      {stats['poly_roll_events']}")
        print(f"  Сонливость (EAR):             {stats['poly_drowsiness_events']}")
        print()

        print("ДЛЯ СРАВНЕНИЯ (покадровый метод, без политопа):")
        print(f"  Зевки:                        {stats['frame_yawn_events']}")
        print(f"  Отвлечение:                   {stats['frame_distraction_events']}")
        print(f"  Наклоны:                      {stats['frame_roll_events']}")
        print(f"  Сонливость:                   {stats['frame_drowsiness_events']}")
        print()

        print("ЭФФЕКТИВНОСТЬ ПОЛИТОПНОЙ ФИЛЬТРАЦИИ:")
        print(f"  Зевки:               снижение на {stats['yawn_reduction']:.1f}%")
        print(f"  Отвлечение:          снижение на {stats['distraction_reduction']:.1f}%")
        print(f"  Наклоны:             снижение на {stats['roll_reduction']:.1f}%")
        print(f"  Сонливость:          снижение на {stats['drowsiness_reduction']:.1f}%")
        print()

        print("СТАТИСТИКА PERCLOS:")
        print(f"  Средний PERCLOS:              {stats['avg_perclos']:.1f}%")
        print(f"  Максимальный PERCLOS:         {stats['max_perclos']:.1f}%")
        print(f"  Время с PERCLOS ≥ 10%:        {stats['time_high_10']:.1f} сек")
        print(f"  Время с PERCLOS ≥ 20%:        {stats['time_high_20']:.1f} сек")
        print(f"  Время с PERCLOS ≥ 28%:        {stats['time_high_28']:.1f} сек")
        print()

        print("РАСПРЕДЕЛЕНИЕ УРОВНЕЙ КРИТИЧНОСТИ:")
        for level in [0, 1, 2, 3]:
            t = stats['crit_time'].get(level, 0)
            pct = stats['crit_pct'].get(level, 0)
            print(f"  {level_names[level]:<10} {t:>8.1f} сек ({pct:>5.1f}%)")
        print()

        print("ФИНАЛЬНАЯ ОЦЕНКА СОСТОЯНИЯ:")
        if stats['crit_pct'].get(3, 0) > 10 or stats['time_high_28'] > 5:
            print("  КРИТИЧЕСКОЕ СОСТОЯНИЕ — НЕОБХОДИМ ОТДЫХ")
        elif stats['crit_pct'].get(2, 0) > 20 or stats['time_high_20'] > 10:
            print("  ПОВЫШЕННАЯ УСТАЛОСТЬ — РЕКОМЕНДУЕТСЯ ПЕРЕРЫВ")
        elif stats['poly_yawn_events'] >= 3:
            print("  ПРИЗНАКИ УСТАЛОСТИ — БУДЬТЕ ВНИМАТЕЛЬНЫ")
        else:
            print("  НОРМАЛЬНОЕ СОСТОЯНИЕ")

    def _save_report(self, driver_id, stats, date):
        """Сохранение текстового отчета в файл."""
        report_date = date if date else datetime.now().strftime("%Y-%m-%d")
        filename = f"report_{driver_id}_{report_date}.txt"
        level_names = {0: 'NORMAL', 1: 'WARNING', 2: 'DANGER', 3: 'CRITICAL'}

        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("ОТЧЕТ МОНИТОРИНГА СОСТОЯНИЯ ВОДИТЕЛЯ\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Водитель: {driver_id}\n")
            f.write(f"Дата отчета: {report_date}\n")
            f.write(f"Общее время анализа: {stats['total_time']:.1f} сек\n")
            f.write(f"Всего записей: {stats['total_records']}\n\n")

            f.write("ОБНАРУЖЕНО СОБЫТИЙ (политопный метод):\n")
            f.write(f"  Зевки (MAR + расстояние):     {stats['poly_yawn_events']}\n")
            f.write(f"  Отвлечение внимания (|yaw|):  {stats['poly_distraction_events']}\n")
            f.write(f"  Наклоны головы (|roll|):      {stats['poly_roll_events']}\n")
            f.write(f"  Сонливость (EAR):             {stats['poly_drowsiness_events']}\n\n")

            f.write("ДЛЯ СРАВНЕНИЯ (покадровый метод, без политопа):\n")
            f.write(f"  Зевки:                        {stats['frame_yawn_events']}\n")
            f.write(f"  Отвлечение:                   {stats['frame_distraction_events']}\n")
            f.write(f"  Наклоны:                      {stats['frame_roll_events']}\n")
            f.write(f"  Сонливость:                   {stats['frame_drowsiness_events']}\n\n")

            f.write("ЭФФЕКТИВНОСТЬ ПОЛИТОПНОЙ ФИЛЬТРАЦИИ:\n")
            f.write(f"  Зевки:               снижение на {stats['yawn_reduction']:.1f}%\n")
            f.write(f"  Отвлечение:          снижение на {stats['distraction_reduction']:.1f}%\n")
            f.write(f"  Наклоны:             снижение на {stats['roll_reduction']:.1f}%\n")
            f.write(f"  Сонливость:          снижение на {stats['drowsiness_reduction']:.1f}%\n\n")

            f.write("СТАТИСТИКА PERCLOS:\n")
            f.write(f"  Средний PERCLOS:              {stats['avg_perclos']:.1f}%\n")
            f.write(f"  Максимальный PERCLOS:         {stats['max_perclos']:.1f}%\n")
            f.write(f"  Время с PERCLOS ≥ 10%:        {stats['time_high_10']:.1f} сек\n")
            f.write(f"  Время с PERCLOS ≥ 20%:        {stats['time_high_20']:.1f} сек\n")
            f.write(f"  Время с PERCLOS ≥ 28%:        {stats['time_high_28']:.1f} сек\n\n")

            f.write("РАСПРЕДЕЛЕНИЕ УРОВНЕЙ КРИТИЧНОСТИ:\n")
            for level in [0, 1, 2, 3]:
                t = stats['crit_time'].get(level, 0)
                pct = stats['crit_pct'].get(level, 0)
                f.write(f"  {level_names[level]:<10} {t:>8.1f} сек ({pct:>5.1f}%)\n")
            f.write("\n")

            f.write("ФИНАЛЬНАЯ ОЦЕНКА СОСТОЯНИЯ:\n")
            if stats['crit_pct'].get(3, 0) > 10 or stats['time_high_28'] > 5:
                f.write("  КРИТИЧЕСКОЕ СОСТОЯНИЕ — НЕОБХОДИМ ОТДЫХ\n")
            elif stats['crit_pct'].get(2, 0) > 20 or stats['time_high_20'] > 10:
                f.write("  ПОВЫШЕННАЯ УСТАЛОСТЬ — РЕКОМЕНДУЕТСЯ ПЕРЕРЫВ\n")
            elif stats['poly_yawn_events'] >= 3:
                f.write("  ПРИЗНАКИ УСТАЛОСТИ — БУДЬТЕ ВНИМАТЕЛЬНЫ\n")
            else:
                f.write("  НОРМАЛЬНОЕ СОСТОЯНИЕ\n")

        print(f"Текстовый отчет сохранен: {filename}")

    def _plot_graphs(self, driver_id, data, profile, date):
        """Построение графиков динамики метрик с выделением политопных интервалов."""
        timestamps = pd.to_datetime(data['timestamp'])

        # Преобразуем время в секунды от начала
        start_time = timestamps.iloc[0]
        time_seconds = (timestamps - start_time).dt.total_seconds()

        # Создаем 5 подграфиков: EAR, MAR, Nose-Chin, Yaw/Roll, PERCLOS
        fig, axes = plt.subplots(5, 1, figsize=(14, 20))

        # ========== 1. EAR (Сонливость) ==========
        axes[0].plot(time_seconds, data['ear_value'], 'b-', alpha=0.7, linewidth=0.5)
        if profile:
            axes[0].axhline(y=profile['ear_threshold'], color='r', linestyle='--',
                        label=f"Порог EAR={profile['ear_threshold']:.3f}")
        axes[0].set_ylabel('EAR')
        axes[0].set_title('Динамика открытости глаз (EAR) - детекция сонливости')
        axes[0].set_xlabel('Время (секунды)')
        axes[0].legend(loc='upper right', fontsize=8)
        axes[0].grid(True, alpha=0.3)

        # Выделяем интервалы сонливости (политопное окно)
        drowsiness_mask = data['drowsiness_detected'].values.astype(bool)
        if np.any(drowsiness_mask):
            in_event = False
            event_start_idx = 0
            for i, val in enumerate(drowsiness_mask):
                if val and not in_event:
                    in_event = True
                    event_start_idx = i
                elif not val and in_event:
                    start_x = time_seconds.iloc[event_start_idx]
                    end_x = time_seconds.iloc[i-1]
                    axes[0].axvspan(start_x, end_x, alpha=0.25, color='orange')
                    mid_x = (start_x + end_x) / 2
                    axes[0].text(mid_x, axes[0].get_ylim()[1]*0.95, 'Сонливость', 
                                ha='center', fontsize=9, color='orange', weight='bold')
                    in_event = False

        # ========== 2. MAR (Зевок) ==========
        axes[1].plot(time_seconds, data['mar_value'], 'g-', alpha=0.7, linewidth=0.5)
        if profile:
            axes[1].axhline(y=profile['mar_threshold'], color='r', linestyle='--',
                        label=f"Порог MAR={profile['mar_threshold']:.3f}")
        axes[1].set_ylabel('MAR')
        axes[1].set_title('Динамика открытости рта (MAR) - детекция зевка')
        axes[1].set_xlabel('Время (секунды)')
        axes[1].legend(loc='upper right', fontsize=8)
        axes[1].grid(True, alpha=0.3)

        # Выделяем интервалы зевков (политопное окно)
        yawn_mask = data['yawn_detected'].values.astype(bool)
        if np.any(yawn_mask):
            in_event = False
            event_start_idx = 0
            for i, val in enumerate(yawn_mask):
                if val and not in_event:
                    in_event = True
                    event_start_idx = i
                elif not val and in_event:
                    start_x = time_seconds.iloc[event_start_idx]
                    end_x = time_seconds.iloc[i-1]
                    axes[1].axvspan(start_x, end_x, alpha=0.25, color='red')
                    mid_x = (start_x + end_x) / 2
                    axes[1].text(mid_x, axes[1].get_ylim()[1]*0.95, 'Зевок', 
                                ha='center', fontsize=9, color='red', weight='bold')
                    in_event = False

        # ========== 3. NOSE-CHIN (Зевок - второй параметр) ==========
        axes[2].plot(time_seconds, data['nose_chin_value'], 'c-', alpha=0.7, linewidth=0.5)
        if profile:
            axes[2].axhline(y=profile['nose_chin_threshold'], color='r', linestyle='--',
                        label=f"Порог Nose-Chin={profile['nose_chin_threshold']:.3f}")
        axes[2].set_ylabel('Nose-Chin (норм.)')
        axes[2].set_title('Динамика расстояния нос-подбородок - детекция зевка')
        axes[2].set_xlabel('Время (секунды)')
        axes[2].legend(loc='upper right', fontsize=8)
        axes[2].grid(True, alpha=0.3)

        # Выделяем интервалы зевков (для корреляции с MAR)
        if np.any(yawn_mask):
            in_event = False
            event_start_idx = 0
            for i, val in enumerate(yawn_mask):
                if val and not in_event:
                    in_event = True
                    event_start_idx = i
                elif not val and in_event:
                    start_x = time_seconds.iloc[event_start_idx]
                    end_x = time_seconds.iloc[i-1]
                    axes[2].axvspan(start_x, end_x, alpha=0.25, color='red')
                    in_event = False

        # ========== 4. Yaw и Roll (Отвлечение и Наклон) ==========
        axes[3].plot(time_seconds, data['yaw_value'], 'r-', alpha=0.5,
                    linewidth=0.5, label='Yaw (поворот головы)')
        axes[3].plot(time_seconds, data['roll_value'], 'orange', alpha=0.5,
                    linewidth=0.5, label='Roll (наклон головы)')
        axes[3].axhline(y=30, color='r', linestyle='--', alpha=0.5, label='Порог Yaw: ±30°')
        axes[3].axhline(y=-30, color='r', linestyle='--', alpha=0.5)
        axes[3].axhline(y=20, color='orange', linestyle='--', alpha=0.5, label='Порог Roll: ±20°')
        axes[3].axhline(y=-20, color='orange', linestyle='--', alpha=0.5)
        axes[3].set_ylabel('Градусы')
        axes[3].set_title('Поза головы - детекция отвлечения и наклона')
        axes[3].set_xlabel('Время (секунды)')
        axes[3].legend(loc='upper right', fontsize=8)
        axes[3].grid(True, alpha=0.3)

        # Выделяем интервалы отвлечения (политопное окно)
        distraction_mask = data['distraction_detected'].values.astype(bool)
        if np.any(distraction_mask):
            in_event = False
            event_start_idx = 0
            for i, val in enumerate(distraction_mask):
                if val and not in_event:
                    in_event = True
                    event_start_idx = i
                elif not val and in_event:
                    start_x = time_seconds.iloc[event_start_idx]
                    end_x = time_seconds.iloc[i-1]
                    axes[3].axvspan(start_x, end_x, alpha=0.25, color='purple')
                    mid_x = (start_x + end_x) / 2
                    axes[3].text(mid_x, axes[3].get_ylim()[1]*0.95, 'Отвлечение', 
                                ha='center', fontsize=9, color='purple', weight='bold')
                    in_event = False

        # Выделяем интервалы наклона головы (политопное окно)
        roll_mask = data['roll_detected'].values.astype(bool)
        if np.any(roll_mask):
            in_event = False
            event_start_idx = 0
            for i, val in enumerate(roll_mask):
                if val and not in_event:
                    in_event = True
                    event_start_idx = i
                elif not val and in_event:
                    start_x = time_seconds.iloc[event_start_idx]
                    end_x = time_seconds.iloc[i-1]
                    axes[3].axvspan(start_x, end_x, alpha=0.25, color='brown')
                    mid_x = (start_x + end_x) / 2
                    axes[3].text(mid_x, axes[3].get_ylim()[0]*1.05, 'Наклон', 
                                ha='center', fontsize=9, color='brown', weight='bold')
                    in_event = False

        # ========== 5. PERCLOS ==========
        axes[4].plot(time_seconds, data['perclos_value'], 'purple', alpha=0.7,
                    linewidth=0.5, label='PERCLOS')
        axes[4].axhline(y=10, color='yellow', linestyle='--', alpha=0.5,
                    label='10% (легкая усталость)')
        axes[4].axhline(y=20, color='orange', linestyle='--', alpha=0.5,
                    label='20% (средняя усталость)')
        axes[4].axhline(y=28, color='red', linestyle='--', alpha=0.5,
                    label='28% (критическая усталость)')
        axes[4].set_ylabel('PERCLOS (%)')
        axes[4].set_xlabel('Время (секунды)')
        axes[4].set_title('Динамика PERCLOS (процент времени с закрытыми глазами)')
        axes[4].legend(loc='upper right', fontsize=8)
        axes[4].grid(True, alpha=0.3)

        plt.suptitle(f'Отчет о состоянии водителя {driver_id}', fontsize=14, y=0.98)
        plt.tight_layout(rect=[0, 0, 1, 0.96])

        report_date = date if date else datetime.now().strftime("%Y-%m-%d")
        filename = f"graph_{driver_id}_{report_date}.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.show()
        print(f"График сохранен: {filename}")
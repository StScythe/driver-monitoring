#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Точка входа в систему мониторинга состояния водителя.
Запуск: python -m scripts.run
"""

import sys
import os

# Добавляем src в путь для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dms.system import FatigueMonitoringSystem


def main():
    """Главная функция приложения."""
    system = FatigueMonitoringSystem()
    
    print("=" * 60)
    print("СИСТЕМА МОНИТОРИНГА СОСТОЯНИЯ ВОДИТЕЛЯ")
    print("=" * 60)
    print("\nГлавное меню:")
    print("1. Идентификация водителя")
    print("2. Запуск мониторинга")
    print("3. Генерация отчета")
    print("4. Выход")

    while True:
        choice = input("\nВыберите опцию (1-4): ").strip()

        if choice == '1':
            driver_id = system.identify_driver()
            if driver_id:
                print(f"Текущий водитель: {driver_id}")

        elif choice == '2':
            system.monitor()

        elif choice == '3':
            system.generate_report()

        elif choice == '4':
            print("Завершение работы")
            break

        else:
            print("Неверный выбор")


if __name__ == "__main__":
    main()
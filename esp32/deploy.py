# deploy.py
# Скрипт для автоматической загрузки кода через ampy

import os
import sys

# --- НАСТРОЙКИ ---
PORT = "COM14"  # Порт вашей платы
# Файлы для загрузки: (локальный путь, удаленный путь)
# ПУТИ ДОЛЖНЫ БЫТЬ ОТНОСИТЕЛЬНЫ КОРНЯ ПРОЕКТА, ГДЕ ЛЕЖИТ ЭТОТ СКРИПТ
FILES_TO_UPLOAD = [
    # Файлы, которые лежали в src
    ("src/config.py", "config.py"),
    ("src/main.py", "main.py"),
    # Файл, который лежал в transport
    ("../transport/esp32_transport.py", "esp32_transport.py"),
    # Библиотека umqtt
    ("src/umqtt/simple.py", "umqtt/simple.py"),
]


# -----------------

def run_ampy_command(command):
    """Выполняет команду ampy и печатает результат."""
    cmd = f"ampy --port {PORT} {command}"
    print(f"\nExecuting: {cmd}")
    result = os.system(cmd)
    return result


def deploy():
    print("--- 🛠️ Начинаем автоматическую загрузку кода на ESP32 ---")

    # 1. Создаем директорию для библиотеки MQTT, если ее нет
    # (ampy будет ругаться, если папка уже есть, но это не критично)
    run_ampy_command("mkdir umqtt")

    # 2. Загружаем все файлы
    for local_path, remote_path in FILES_TO_UPLOAD:
        # Проверяем наличие файла
        if not os.path.exists(local_path):
            print(f"🛑 ERROR: Local file not found: {local_path}. Check your path!")
            continue

        # Загрузка
        run_ampy_command(f"put {local_path} {remote_path}")

    # 3. Перезагрузка
    print("\n--- 🔄 Перезагрузка платы ---")
    run_ampy_command("reset")

    print("\n--- ✅ Загрузка завершена. ---")
    print(f"Теперь запустите мониторинг: mpremote connect {PORT} repl")


if __name__ == "__main__":
    deploy()

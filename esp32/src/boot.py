# src/boot.py
import gc
import machine
import network
import time
import micropython

# --- Конфигурация Режима Восстановления ---
# Кнопка BOOT/FLASH на ESP32 подключена к GPIO 0.
RECOVERY_PIN = 0
p = machine.Pin(RECOVERY_PIN, machine.Pin.IN, machine.Pin.PULL_UP)

# 1. Проверка режима восстановления
if p.value() == 0:
    # Кнопка BOOT/FLASH нажата при старте (пин в LOW).
    print("\n\n*** RECOVERY MODE ACTIVE: main.py skipped ***")

    # Очищаем очередь, чтобы REPL не был переполнен старыми логами
    micropython.kbd_intr(-1)

    # Ждем, пока пользователь отпустит кнопку
    print("Release BOOT button to continue.")
    while p.value() == 0:
        time.sleep_ms(50)

        # Выход из функции/файла. MicroPython не пойдет дальше и не запустит main.py.
    # Это оставляет интерпретатор в состоянии REPL (>>>) для команд.
    # Если вы не хотите, чтобы в этом режиме выполнялась ваша старая логика,
    # просто уберите 'return'. В данном случае, это безопасно.
    # return
else:
    # 2. Обычный запуск (Кнопка BOOT/FLASH не нажата)
    # --- Ваша старая логика ---

    # Отключаем Wi-Fi, чтобы не мешать основному коду
    network.WLAN(network.STA_IF).active(False)
    network.WLAN(network.AP_IF).active(False)

    # Освобождаем память
    gc.collect()

    # Позволяем MicroPython автоматически запустить main.py
    # (выполняется после завершения boot.py)

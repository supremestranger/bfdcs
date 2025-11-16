import time
import machine
import config
import esp32_transport
import _thread

# --- Инициализация бортового LED (GPIO 2) ---
# На большинстве плат ESP32-S бортовой LED подключен к GPIO 2.
try:
    # Устанавливаем LED как выходной пин
    ONBOARD_LED = machine.Pin(2, machine.Pin.OUT)
    ONBOARD_LED.value(0)  # Убеждаемся, что LED выключен (Low-active)
except ValueError:
    print("[App] Warning: Could not initialize Pin(2). Blink feedback will be skipped.")
    ONBOARD_LED = None


# ---------------------------------------------


def __log__(log):
    """Логгер уровня приложения."""
    print(f"[{time.ticks_ms()}] [App] {log}")


def blink_feedback(duration_ms, count=1):
    """
    Мигает LED для визуальной обратной связи.
    Неблокирующая версия для MicroPython.
    """
    if ONBOARD_LED is None:
        return

    delay_s = duration_ms / 1000.0
    for _ in range(count):
        ONBOARD_LED.value(1)  # Включить
        time.sleep(delay_s / 2)
        ONBOARD_LED.value(0)  # Выключить
        time.sleep(delay_s / 2)

    # Убедиться, что LED выключен после мигания
    ONBOARD_LED.value(0)


def process_task(task):
    """
    !!! ЛОГИКА ОБРАБОТКИ ЗАДАЧИ ЗДЕСЬ !!!

    Эта функция получает сырые данные задачи,
    выполняет работу и возвращает результат.
    """
    __log__(f"Processing task {task.get('id', 'N/A')}...")

    # Пример... извлечение данных
    payload = task.get("payload", {})
    command = payload.get("command")

    # Имитация работы
    start_time = time.ticks_ms()

    # --- Начало реальной работы ---
    if command == "add":
        # Короткая операция
        result_data = payload.get("a", 0) + payload.get("b", 0)
    elif command == "blink":
        # Убедитесь, что эта функция не длится дольше 80 секунд!
        blink_feedback(duration_ms=500, count=4)
        result_data = "blinked"
    else:
        result_data = "unknown_command"
    # --- Конец реальной работы ---

    processing_time = time.ticks_diff(time.ticks_ms(), start_time)
    __log__(f"Task finished in {processing_time}ms. Result: {result_data}")

    return {"status": "ok", "time_ms": processing_time, "data": result_data}


def main():
    """Главный цикл работы ноды."""
    __log__(f"Starting node {config.NODE_TYPE}...")

    # 1. Создаем транспортный объект
    node = esp32_transport.ComputeNode(
        config.MQTT_BROKER,
        config.MQTT_PORT,
        config.MQTT_KEEPALIVE
    )

    while True:
        try:
            # 1. Проверяем и восстанавливаем соединение
            if not node.is_connected():
                __log__("Attempting to connect...")

                # 🔴 БЫСТРОЕ МИГАНИЕ при ошибке подключения
                if not node.connect():
                    blink_feedback(duration_ms=250, count=2)
                    __log__("Connection failed. Retrying in 5 seconds...")
                    time.sleep(5)
                    continue  # Начинаем цикл заново

                # 🟢 МЕДЛЕННОЕ МИГАНИЕ при успешном подключении
                blink_feedback(duration_ms=2000, count=1)

                __log__("Node connected and registered.")
                # После подключения сразу ставим "ready"
                node.publish_status("ready")

                # --- ЗАПУСК ПОТОКА ЗДЕСЬ ---
                node.start_keepalive_thread()

            # 2. Проверяем входящие сообщения (задачи) и отправляем PINGREQ
            # Это наполняет внутреннюю очередь задач в node
            # и поддерживает Keep-Alive.
            # node.check_messages()
            # (он теперь выполняется в фоновом потоке)

            # 3. Получаем задачу из очереди
            task = node.get_task()

            if task:
                # 4. Если задача есть - выполняем
                node.publish_status("busy")

                # --- Вызов бизнес-логики ---
                result = process_task(task)
                # --- Конец бизнес-логики ---

                node.send_result(result)
                node.publish_status("ready")

            else:
                # 5. Задач нет.
                # Короткий сон, чтобы процессор не работал вхолостую
                time.sleep_ms(10)

        except (OSError, Exception) as e:
            __log__(f"Main loop error: {e}")
            # 🔴 БЫСТРОЕ МИГАНИЕ при ошибке в цикле
            blink_feedback(duration_ms=250, count=5)
            node.handle_disconnect()
            __log__("Restarting in 10 seconds...")
            time.sleep(10)
            # В MicroPython надежнее всего перезагрузиться
            # при непредвиденной ошибке в главном цикле
            machine.reset()


if __name__ == "__main__":
    main()
"""
Транспортный модуль ComputeNode для MicroPython (ESP32)
Адаптированная версия node_transport.py для работы с umqtt и MicroPython.
"""

import machine
import time
import ujson
import network
import binascii
from umqtt.simple import MQTTClient
import config  # Предполагается, что config.py лежит рядом с main.py, который импортирует этот модуль
import _thread


class ComputeNode:
    def __init__(self, broker_host, broker_port, broker_keepalive):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.broker_keepalive = broker_keepalive

        # Генерируем постоянный ID ноды из MAC-адреса
        self.node_id = binascii.hexlify(machine.unique_id()).decode('utf-8')

        # Топики (воспроизводим логику node_transport.py)
        self.task_topic = self.node_id  # Топик, куда приходят задачи
        self.status_topic = f"{self.node_id}/status"  # Топик для публикации статуса

        # Очереди задач, как в оригинале
        self.tasks = {p: [] for p in range(1, 11)}

        self.client = None
        self.status = "offline"
        self.sta_if = network.WLAN(network.STA_IF)

        # Переменная для контроля состояния фонового потока
        self.keepalive_thread_running = False

        self.__log__(f"Node ID: {self.node_id}")
        self.__log__(f"Task Topic: {self.task_topic}")
        self.__log__(f"Status Topic: {self.status_topic}")

    def __log__(self, log):
        """Простой логгер."""
        # Вывод в консоль MicroPython (REPL)
        print(f"[{time.ticks_ms()}] [Transport] {log}")

    def _connect_wifi(self):
        """(Внутренний) Подключается к WiFi с агрессивным сбросом и статическим IP."""
        if self.sta_if.isconnected():
            self.__log__("Marker 1A: WiFi already connected.")
            return True

        self.__log__(f"Marker 1B: Starting full reconnect for SSID: {config.WIFI_SSID}...")

        # Агрессивный сброс Wi-Fi для повышения надежности
        self.sta_if.active(False)
        time.sleep_ms(100)
        self.sta_if.active(True)

        # --- Настройка статического IP ---
        # Формат: (IP, Netmask, Gateway, DNS)
        self.sta_if.ifconfig((config.STATIC_IP, config.NETMASK, config.GATEWAY, config.DNS_SERVER))
        self.__log__(f"Marker 1C: Wi-Fi interface reset and static IP set to {config.STATIC_IP}.")
        # -----------------------------------------------

        self.sta_if.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        self.__log__("Marker 1D: Connection attempt initiated.")

        wait_count = 0
        # Таймаут 15 секунд (30 * 500ms)
        while not self.sta_if.isconnected():
            if wait_count > 30:
                self.__log__("Marker 1E: WiFi connection FAILED (Timeout 15s)!")
                self.sta_if.active(False)  # Отключаем Wi-Fi при неудаче
                return False

            time.sleep_ms(500)
            wait_count += 1
            self.__log__(f"Marker 1F: Waiting for connection... ({wait_count * 0.5}s)")

        self.__log__("Marker 1G: WiFi connection SUCCESS.")
        self.__log__(f"Marker 1H: Assigned (Static) IP: {self.sta_if.ifconfig()[0]}")
        return True

    def _on_message_(self, topic, msg):
        """
        (Внутренний) Callback для входящих MQTT сообщений.
        """
        try:
            topic_str = topic.decode('utf-8')
            self.__log__(f"Message received on topic: {topic_str}")

            if not msg:
                self.__log__("Empty message received")
                return

            if topic_str != self.task_topic:
                self.__log__(f"Ignoring message for other topic: {topic_str}")
                return

            task_data = ujson.loads(msg.decode())

            if task_data.get("task_info", {}).get("command") == "init":
                self.__log__("Initialisation command received")
                self.publish_status("ready")
            else:
                self.__log__(f"Task queued: {str(task_data)}")
                priority = max(1, min(task_data.get("priority", 1), 10))
                self.tasks[priority].append(task_data)

        except ujson.JSONDecodeError as e:
            self.__log__(f"Invalid JSON in task: {e}")
        except Exception as e:
            self.__log__(f"Error processing task: {e}")

    def _connect_mqtt(self):
        """(Внутренний) Подключается к MQTT и настраивает LWT."""
        self.__log__("Marker 2A: Starting MQTT connection setup.")
        try:
            # LWT (Last Will and Testament) - аналог will_set
            lwt_msg = ujson.dumps({"node_id": self.node_id, "status": "dead"})

            self.client = MQTTClient(
                client_id=self.node_id,
                server=self.broker_host,
                port=self.broker_port,
                keepalive=self.broker_keepalive
            )

            # Устанавливаем LWT ПЕРЕД подключением
            self.client.set_last_will(self.status_topic, lwt_msg, retain=True, qos=1)
            # Устанавливаем callback
            self.client.set_callback(self._on_message_)

            self.__log__(f"Marker 2B: Attempting client.connect() to {self.broker_host}:{self.broker_port}...")

            self.client.connect()

            # Если дошли сюда, соединение установлено
            self.__log__("Marker 2C: MQTT connection SUCCESS.")

            # Регистрируем ноду после успешного подключения
            self._register_node()
            return True

        except (OSError, Exception) as e:
            self.__log__(f"Marker 2D: MQTT connection FAILED. Error: {e}")
            self.client = None
            return False

    def _register_node(self):
        """
        (Внутренний) Публикует данные о себе и подписывается на задачи.
        """

        # 1. Публикуем сообщение о инициализации (как в Python коде)
        init_msg = {
            "node_id": self.node_id,
            "device_type": config.NODE_TYPE,  # Берем из config.py
            "status": "connected"
        }
        self.client.publish("initialisation", ujson.dumps(init_msg), qos=1)

        # 2. Публикуем свой статус "connected" (retained)
        self.publish_status("connected")

        # 3. Подписываемся на топик с задачами для этой ноды
        self.client.subscribe(self.task_topic, qos=1)

        self.__log__(f"Node registered. Subscribed to topic: {self.task_topic}")

    # --- Публичные методы API (для main.py) ---

    def connect(self):
        """
        Главный метод подключения. Вызывается из main.py.
        Подключается к WiFi, затем к MQTT.
        """
        # Marker 3A
        self.__log__("Marker 3A: Starting full connection sequence.")

        if not self._connect_wifi():
            self.__log__("Marker 3B: _connect_wifi failed. Stopping.")
            return False

        # Marker 3C
        self.__log__("Marker 3C: WiFi is up. Proceeding to MQTT.")

        if not self._connect_mqtt():
            self.__log__("Marker 3D: _connect_mqtt failed. Stopping.")
            return False

        self.__log__("Marker 3E: Full connection SUCCESS.")
        return True

    def is_connected(self):
        """Проверяет, активно ли соединение."""
        return self.sta_if.isconnected() and self.client is not None

    def handle_disconnect(self):
        """
        Вызывается из main.py при сбое. Очищает MQTT-клиент для
        повторного подключения в основном цикле.
        """
        self.__log__("Connection lost. Cleaning up MQTT client.")
        self.status = "offline"
        # Сброс флага, чтобы main.py мог запустить новый поток
        self.keepalive_thread_running = False
        if self.client:
            try:
                self.client.disconnect()
            except:
                pass  # Уже отвалились
        self.client = None

    def check_messages(self):
        """
        Критически важный метод. Замена paho-шного loop_start().
        Должен вызываться в основном цикле main.py.
        Проверяет наличие входящих сообщений MQTT.
        """
        if self.client and self.status != "offline":
            try:
                # check_msg() отправляет PINGREQ, если истекло время
                self.client.check_msg()
                return True
            except Exception as e:
                self.__log__(f"Check messages failed: {e}")
                self.handle_disconnect()
                return False
            return False

    def mqtt_keepalive_loop(self):
        """
        Цикл для поддержания Keep-Alive в отдельном потоке.
        """
        self.__log__("Starting MQTT Keep-Alive thread.")

        # Устанавливаем флаг перед циклом
        self.keepalive_thread_running = True

        # ЦИКЛ: Продолжаем, пока соединение активно
        while self.is_connected():
            # Единственный вызов check_messages, чтобы избежать конфликта
            if not self.check_messages():
                break  # Выход, если check_messages вызвал handle_disconnect

            # Короткая блокирующая пауза, чтобы не нагружать процессор
            time.sleep_ms(10)

        self.__log__("MQTT Keep-Alive thread stopped.")

    def start_keepalive_thread(self):
        """Запускает цикл Keep-Alive в новом потоке, если он еще не запущен."""
        if not self.keepalive_thread_running:
            _thread.start_new_thread(self.mqtt_keepalive_loop, ())

    def publish_status(self, status):
        """
        Публикация нового статуса (retain=True).
        Аналог paho-версии.
        """
        if not self.client:
            self.__log__(f"Cannot publish status '{status}', client is offline.")
            return

        self.status = status
        status_msg = {"node_id": self.node_id, "status": status}

        try:
            self.client.publish(
                self.status_topic,
                ujson.dumps(status_msg),
                qos=1,
                retain=True
            )
            self.__log__(f"Published status: {status}")
        except Exception as e:
            self.__log__(f"Failed to publish status: {e}")
            self.handle_disconnect()

    def send_result(self, result_data):
        """
        Отправка результата.
        Аналог paho-версии.
        """
        if not self.client:
            self.__log__(f"Cannot send result, client is offline.")
            return

        res_msg = {
            "node_id": self.node_id,
            "result": result_data,
            "timestamp": time.time()  # time.time() в MicroPython дает UNIX time
        }
        try:
            self.client.publish("results", ujson.dumps(res_msg), qos=1, retain=True)
            self.__log__(f"Result sent: {str(res_msg)}")
        except Exception as e:
            self.__log__(f"Failed to send result: {e}")
            self.handle_disconnect()

    def get_task(self):
        """
        Получение задачи с наивысшим приоритетом.
        Логика идентична paho-версии.
        """
        for priority in range(10, 0, -1):
            if self.tasks[priority]:
                return self.tasks[priority].pop(0)
        return None

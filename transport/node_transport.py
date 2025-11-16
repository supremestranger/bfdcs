import paho.mqtt.client as mqtt
import uuid
import json
import time
import signal
import sys


class ComputeNodeTransport:
    def __init__(self, broker_host='localhost', broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.node_id = str(uuid.uuid4())
        self.tasks = {
            1:[], 2:[], 3:[], 4:[], 5:[], 6:[], 7:[], 8:[], 9:[], 10:[]
        }

        self.client = mqtt.Client(client_id=self.node_id, clean_session=True)
        # LWT: если нода отвалится некорректно — брокер опубликует в топик <node_id>/status сообщение dead (retain=True)
        self.client.will_set(f"{self.node_id}/status",
                             json.dumps({"node_id": self.node_id, "status": "dead"}),
                             qos=1, retain=True)

        self.client.on_connect = self._on_connect_
        self.client.on_message = self._on_message_

        self.status = "offline"

        # перехват Ctrl+C для корректного отключения
        signal.signal(signal.SIGINT, self._graceful_shutdown_)
        signal.signal(signal.SIGTERM, self._graceful_shutdown_)

    def __log__(self, log):  # TODO: Заменить на обращение к модулю логирования
        print(log)

    def _on_connect_(self, client, userdata, flags, rc):
        self.__log__("Node connected to broker (on_connect callback)")
        return

    def _on_message_(self, client, userdata, msg):
        try:
            if not msg.payload:
                self.__log__("Empty message received")
                return
            task_data = json.loads(msg.payload.decode())
            if task_data.get("task_info", {}).get("command") == "init":# не поняла прикола
                self.__log__("Initialisation received")
                self.publish_status("ready")
                # пример изменения статуса при выполнении работы
                # publish_status("busy")  # если нужно пометить, что нода занята
                # ... выполнить init ...
                # publish_status("ready")  # вернуть ready
            else:
                # Обработка других задач
                self.__log__("Task received:", task_data)
                priority = max(1, min(task_data.get("priority", 0), 10))
                self.tasks[priority].append(task_data)
        except json.JSONDecodeError as e:
            self.__log__(f"Invalid JSON in task: {e}")
        except Exception as e:
            self.__log__(f"Error processing task: {e}")

    def _graceful_shutdown_(self, signum=None, frame=None):
        """Чистое завершение: уведомим мастер, что нода offline (retain=True), затем отключимся."""
        try:
            self.__log__("Graceful shutdown: publishing offline")
            self.publish_status("offline")
            # небольшая пауза, чтобы сообщение дошло
            time.sleep(0.5)
        except Exception:
            pass
        try:
            self.client.disconnect()
            self.client.loop_stop()
        except Exception:
            pass
        self.__log__("Node stopped")
        sys.exit(0)

    def start(self):
        self.client.connect(self.broker_host, self.broker_port)
        self.client.loop_start()
        # при старте публикуем initialisation и свой статус (retain=True)
        # initialisation: как раньше
        init_msg = {
            "node_id": self.node_id,
            "device_type": "esp-32",
            "status": "connected"
        }
        self.client.publish("initialisation", json.dumps(init_msg))
        # публикуем статус ноды (retain) — мастер получит текущее состояние сразу после подписки
        self.publish_status("connected")
        # подписываемся на топик с задачами для ноды
        self.client.subscribe(self.node_id)
        self.__log__(f"Node {self.node_id} started and registered")

    def publish_status(self, status):
        """Публикация нового статуса (retain=True)."""
        self.status = status
        status_msg = {"node_id": self.node_id, "status": status}
        # оставляем retain=True, чтобы мастер получал актуальный статус при подписке
        self.client.publish(f"{self.node_id}/status", json.dumps(status_msg), qos=1, retain=True)
        self.__log__(f"Published status: {status}")

    def send_result(self, result):
        res_msg = {
            "node_id": self.node_id,
            "result": result,
            "timestamp": time.time()
        }
        self.client.publish("results", json.dumps(res_msg), qos=1, retain=True)

    def get_task(self):
        for priority in range(10, 0, -1):
            if self.tasks[priority]:
                return self.tasks[priority].pop(0)
        return None

# Пример использования
if __name__ == "__main__":
    node = ComputeNodeTransport(broker_host='127.0.0.1')
    node.start()


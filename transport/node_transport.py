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

    def _on_connect_(self, client, userdata, flags, rc):
        print("Node connected to broker (on_connect callback)")
        return

    def _on_message_(self, client, userdata, msg):
        try:
            task_data = json.loads(msg.payload.decode())
            if task_data.get("task_info", {}).get("command") == "init":
                print("Initialisation received")
                self.publish_status("ready")
                # пример изменения статуса при выполнении работы
                # publish_status("busy")  # если нужно пометить, что нода занята
                # ... выполнить init ...
                # publish_status("ready")  # вернуть ready
            else:
                # Обработка других задач
                print("Task received:", task_data)
        except Exception as e:
            print(f"Error processing message: {e}")

    def _graceful_shutdown_(self, signum=None, frame=None):
        """Чистое завершение: уведомим мастер, что нода offline (retain=True), затем отключимся."""
        try:
            print("Graceful shutdown: publishing offline")
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
        print("Node stopped")
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
        print(f"Node {self.node_id} started and registered")

    def publish_status(self, status):
        """Публикация нового статуса (retain=True)."""
        self.status = status
        status_msg = {"node_id": self.node_id, "status": status}
        # оставляем retain=True, чтобы мастер получал актуальный статус при подписке
        self.client.publish(f"{self.node_id}/status", json.dumps(status_msg), qos=1, retain=True)
        print(f"Published status: {status}")


# Пример использования
if __name__ == "__main__":
    node = ComputeNodeTransport()
    node.start()

    # Демонстрация: можно программно менять статус в любой момент
    try:
        while True:
            # здесь можно изменить статус, когда нода начинает/заканчивает задачу:
            # node.publish_status("busy")
            # time.sleep(5)
            # node.publish_status("ready")
            time.sleep(1)
    except KeyboardInterrupt:
        node._graceful_shutdown_()

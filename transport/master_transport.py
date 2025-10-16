import paho.mqtt.client as mqtt
import json
import time


class MasterNodeTransport:
    def __init__(self, broker_host='localhost', broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.nodes = []  # массив с нодами
        self.results = {}  # массив с результатами
        self.sended = 0
        self.dead_nodes = []  # массив ID умерших нод

        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect_
        self.client.on_message = self._on_message_

        # callback, который вызывается когда нода становится dead/offline
        self.dead_nodes_callback = None

    def __log__(self, log):  # TODO: Заменить на обращение к модулю логирования
        print(log)

    def _on_connect_(self, client, userdata, flags, rc):
        self.__log__("Connected to broker")
        # подписываемся на сообщения и на статусы нод
        self.client.subscribe("initialisation")
        self.client.subscribe("results")
        self.client.subscribe("+/status")  # подписка на асинхронные уведомления о смене статуса нод

    def _on_message_(self, client, userdata, msg):
        topic = msg.topic

        if topic == "initialisation":
            data = json.loads(msg.payload.decode())
            node_id = data["node_id"]

            self.__log__(f"New node (initialisation): {node_id}")
            new_node = {
                "node_id": node_id,
                "device_type": data.get("device_type", "unknown"),
                "status": data.get("status", "connected"),
                "last_seen": time.time(),
            }
            # если нода уже есть, обновляем, иначе добавляем
            existing = next((n for n in self.nodes if n["node_id"] == node_id), None)
            if existing:
                existing.update(new_node)
            else:
                self.nodes.append(new_node)

            # Initialisation node — отправляем init задачу
            #  TODO: Задача инициализации??
            return

        if topic == "results":
            data = json.loads(msg.payload.decode())
            node_id = data["node_id"]
            if not self.results[node_id]:
                self.results[node_id].append(data["result"])
            else:
                self.results[node_id] = [data["result"]]
            return

        if topic.endswith("/status"):  # асинхронное уведомление о смене статуса ноды
            try:
                data = json.loads(msg.payload.decode())
                node_id = data.get("node_id")
                status = data.get("status")

                node = next((n for n in self.nodes if n["node_id"] == node_id), None)
                if node:
                    node["status"] = status
                    node["last_seen"] = time.time()
                else:
                    # если мастер узнал о ноде только по retained статусу (без initialisation) — добавим с unknown device_type
                    node = {
                        "node_id": node_id,
                        "device_type": data.get("device_type", "unknown"),
                        "status": status,
                        "last_seen": time.time(),
                    }
                    self.nodes.append(node)

                self.__log__(f"Status update from {node_id}: {status}")

                if status in ("dead", "offline"):
                    if node_id not in self.dead_nodes:
                        self.dead_nodes.append(node_id)
                        # вызывем колбэк если задан
                        if self.dead_nodes_callback:
                            try:
                                self.dead_nodes_callback([node_id])
                            except Exception as e:
                                print(f"Error in dead_nodes_callback: {e}")
                else:
                    # если нода ожила — удалим из dead_nodes
                    if node_id in self.dead_nodes:
                        self.dead_nodes = [n for n in self.dead_nodes if n != node_id]

            except Exception as e:
                self.__log__(f"Error processing status message: {e}")
            return

        return  # другие топики

    def set_dead_nodes_callback(self, cb):  # Установить callback(dead_nodes_list) для асинхронной обработки мертвых нод
        self.dead_nodes_callback = cb

    def get_dead_nodes(self, disposable=False):
        dead_nodes = []
        if disposable:
            self.dead_nodes = []
        return dead_nodes

    def get_nodes_by_status(self, status="ready"):
        return [node for node in self.nodes if node["status"] == status]

    def start(self):
        self.client.connect(self.broker_host, self.broker_port)
        self.client.loop_start()

    def send_task(self, node_id, task_data, priority=5):
        for node in self.nodes:
            if node["node_id"] == node_id:
                if not(node["status"] in ["dead", "offline"]):
                    if not "priority" in task_data:
                        task_data["priority"] = priority
                    self.client.publish(node_id, task_data)
                    self.__log__(f"Task sent {node_id}")
                    return
                self.__log__(f"Node {node_id} not working")
                return

        self.__log__(f"Node {node_id} not found")

    def get_node_info(self, node_id=None):
        if node_id is None:
            return self.nodes
        return self.nodes[node_id]

    def get_results(self, node_id_dict=None, disposable=False):
        if node_id_dict is None:
            result = self.results.copy()
            if disposable:
                self.results.clear()
            return result
        filtered_result = {node_id: self.results.get(node_id, []) for node_id in node_id_dict}
        if disposable:
            for node_id in node_id_dict:
                del self.results[node_id]
        return filtered_result

    def forget_node(self, node_id):
        for node in list(self.nodes):
            if node["node_id"] == node_id:
                self.nodes.remove(node)

                # очистим dead_nodes от id
                if node_id in self.dead_nodes:
                    self.dead_nodes = [n for n in self.dead_nodes if n != node_id]

                self.client.unsubscribe(f"{node_id}/status")
                return

        self.__log__(f"Node {node_id} not found")


# Пример использования
if __name__ == "__main__":
    def on_dead(ids):
        print(f"Callback: найден(ы) мёртвы(е) нод(а): {ids}")

    master = MasterNodeTransport()
    master.set_dead_nodes_callback(on_dead)
    master.start()

    # демонстрация: мастер работает событие-ориентированно, лишних циклов нет
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Master stopped")

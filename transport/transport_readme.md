# Система распределения вычислений: Транспортный модуль

## Описание
Данный модуль обеспечивает транспортный слой для системы распределённых вычислений. Он реализует взаимодействие между мастер-ноды и вычислительными нодами через MQTT-протокол. Модуль состоит из двух основных компонентов:

1. **MasterNodeTransport** — транспортный интерфейс для мастера, отвечающего за координацию задач.
2. **ComputeNodeTransport** — транспортный интерфейс для вычислительных нод, принимающих задачи и отправляющих результаты.
3. **ComputeNode (MicroPython)** — версия транспортного слоя для ESP32 и других микроконтроллеров с MicroPython.

Документация предназначена для разработчиков, использующих модуль для построения распределённых систем и для интеграции в реальные проекты.

---

## MasterNodeTransport

### Инициализация
```python
master = MasterNodeTransport(broker_host='localhost', broker_port=1883)
```

**Атрибуты конструктора:**
- `broker_host` (str): Адрес MQTT-брокера. По умолчанию `'localhost'`.
- `broker_port` (int): Порт MQTT-брокера. По умолчанию `1883`.

### Основные методы

#### `start()`
Запускает соединение с брокером и начинает обработку сообщений.

#### `send_task(node_id, task_data, priority=5)`
Отправляет задачу конкретной ноде.

**Параметры:**
- `node_id` (str): Идентификатор ноды, которой отправляется задача.
- `task_data` (dict): Словарь с данными задачи.
- `priority` (int, optional): Приоритет задачи от 1 до 10. По умолчанию `5`.

#### `get_node_info(node_id=None)`
Возвращает информацию о нодах.

**Параметры:**
- `node_id` (str, optional): Если указан — возвращает информацию только о конкретной ноде. Иначе — список всех нод.

#### `get_nodes_by_status(status='ready')`
Возвращает список нод с указанным статусом.

**Параметры:**
- `status` (str): Статус ноды, по которому фильтруем. Например: `'ready'`, `'busy'`, `'dead'`.

#### `set_dead_nodes_callback(cb)`
Устанавливает callback-функцию для обработки нод, которые стали мёртвыми.

**Параметры:**
- `cb` (callable): Функция с одним аргументом — список идентификаторов мёртвых нод.

#### `get_dead_nodes(disposable=False)`
Возвращает список мёртвых нод.

**Параметры:**
- `disposable` (bool): Если `True`, после вызова список мёртвых нод очищается.

#### `get_results(node_id_dict=None, disposable=False)`
Возвращает результаты выполненных задач.

**Параметры:**
- `node_id_dict` (list, optional): Если указано — фильтруем результаты по этим нодам.
- `disposable` (bool): Если `True`, после вызова результаты удаляются из внутреннего хранилища.

#### `forget_node(node_id)`
Удаляет ноду из системы и отписывает её от топика статуса.

**Параметры:**
- `node_id` (str): Идентификатор ноды для удаления.

---

## ComputeNodeTransport

### Инициализация
```python
node = ComputeNodeTransport(broker_host='localhost', broker_port=1883)
```

**Атрибуты конструктора:**
- `broker_host` (str): Адрес MQTT-брокера.
- `broker_port` (int): Порт MQTT-брокера.
- `node_id` (str): Уникальный идентификатор ноды (генерируется автоматически).

### Основные методы

#### `start()`
Запускает соединение с брокером, публикует initialisation и подписывается на топик с задачами.

#### `publish_status(status)`
Публикует текущий статус ноды в топик `<node_id>/status`.

**Параметры:**
- `status` (str): Новый статус ноды. Например: `'connected'`, `'ready'`, `'busy'`, `'offline'`.

#### `send_result(result)`
Отправляет результат выполнения задачи в топик `results`.

**Параметры:**
- `result` (any): Результат выполнения задачи.

#### `get_task()`
Возвращает следующую задачу из очереди по приоритету.

### Особенности работы
- Автоматическая публикация статуса `dead` при некорректном завершении (LWT MQTT).
- Обработка сигналов SIGINT/SIGTERM для корректного отключения и уведомления мастера.
- Задачи распределяются по приоритетам (1–10).

---

# ComputeNode (MicroPython версия для ESP32)

## Обзор
`ComputeNode` — это адаптированная версия транспортного модуля для микроконтроллеров с MicroPython (например, ESP32).
Модуль использует `umqtt.simple` для обмена сообщениями и напрямую взаимодействует с Wi-Fi-интерфейсом устройства.

Основные отличия от классической версии:
* Минимальные зависимости (без paho.mqtt).
* Оптимизировано для работы в ограниченной среде (RAM/CPU).
* Поддержка статического IP и агрессивного восстановления Wi-Fi-соединения.
* Фоновая поддержка MQTT Keep-Alive в отдельном потоке.

### Инициализация
```python
from compute_node import ComputeNode
import config

node = ComputeNode(
    broker_host=config.MQTT_HOST,
    broker_port=config.MQTT_PORT,
    broker_keepalive=60
)
```
### Атрибуты конструктора
* `broker_host` (str): Адрес MQTT-брокера.
* `broker_port` (int): Порт брокера.
* `broker_keepalive` (int): Интервал keepalive в секундах.
* `node_id` (str): Уникальный идентификатор, основанный на MAC-адресе устройства.
* `task_topic` (str): Топик получения задач (равен node_id).
* `status_topic` (str): Топик публикации статуса (<node_id>/status).

### Основные методы

#### `connect()`

Подключается к Wi-Fi и MQTT-брокеру.
Возвращает True при успешном соединении.

#### `is_connected()`

Проверяет, активно ли соединение (Wi-Fi + MQTT).

#### `handle_disconnect()`

Безопасно завершает соединение и сбрасывает состояние клиента.

#### `check_messages()`

Проверяет входящие MQTT-сообщения и выполняет callback.
Рекомендуется вызывать в основном цикле main.py.

#### `mqtt_keepalive_loop()`

Фоновый поток для поддержания активности соединения (Keep-Alive).

#### `start_keepalive_thread()`

Запускает поток mqtt_keepalive_loop, если он ещё не активен.

#### `publish_status(status)`

Публикует текущее состояние ноды в топик <node_id>/status.
Сообщение публикуется с флагом retain=True.

**Параметры:**

 * `status` (str): Например, 'connected', 'ready', 'busy', 'offline'.

#### `send_result(result_data)`

Отправляет результат выполнения задачи в топик results.
Сообщение включает отметку времени (timestamp).

#### `get_task()`

Возвращает задачу с наивысшим приоритетом из очереди.

### Особенности работы

* Автоматическая регистрация и публикация статуса при подключении.
* Отправка LWT-сообщения (status='dead') при аварийном завершении.
* Приоритетная очередь задач (1–10).
* Логирование через встроенный REPL-вывод (print).
* Совместимо с main.py, управляющим циклом работы ноды.

---

## Примеры использования

### Мастер-нода
```python
from master_transport import MasterNodeTransport

master = MasterNodeTransport()
master.set_dead_nodes_callback(lambda ids: print(f"Dead nodes: {ids}"))
master.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Master stopped")
```

### Вычислительная нода
```python
from node_transport import ComputeNodeTransport

node = ComputeNodeTransport()
node.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    node._graceful_shutdown_()
```

### ESP-32 нода
```python
import config
from compute_node import ComputeNode
import time

node = ComputeNode(
    broker_host=config.MQTT_HOST,
    broker_port=config.MQTT_PORT,
    broker_keepalive=60
)

if node.connect():
    node.start_keepalive_thread()
    node.publish_status("ready")

    while True:
        task = node.get_task()
        if task:
            print("Executing:", task)
            # Здесь выполняется обработка задачи
            result = {"task_id": task["id"], "output": "done"}
            node.send_result(result)
        time.sleep(0.1)
else:
    print("Connection failed")
```

---

## Рекомендации по использованию
1. Всегда использовать `set_dead_nodes_callback` для отслеживания недоступных нод.
2. Использовать приоритеты при отправке задач, чтобы распределение нагрузки было гибким.
3. Подписываться на статус нод при старте, чтобы мастер получал актуальные данные.
4. Обрабатывать задачи асинхронно, не блокируя главный цикл.
5. Всегда корректно завершать ноды через `_graceful_shutdown_`.

---

Эта документация обеспечивает полный обзор методов и атрибутов транспортного модуля, позволяя разработчикам безопасно и эффективно интегрировать систему распределённых вычислений в свои проекты.


# -- Конфигурация WiFi --
WIFI_SSID = "DIR-615"
WIFI_PASSWORD = "9045977133"

# -- Конфигурация MQTT --
MQTT_BROKER = "172.16.16.97"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60

# -- Конфигурация Ноды --
NODE_TYPE = "esp32-compute"

# -- Конфигурация подключения --
STATIC_IP = "172.16.16.133"
NETMASK = "255.255.255.0"
GATEWAY = "172.16.16.97"  # Совпадает с брокером
DNS_SERVER = "172.16.16.97"

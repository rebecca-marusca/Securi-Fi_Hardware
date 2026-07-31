# wifi
WIFI_SSID = "SecuriFi-Hub"
WIFI_PASSWORD = "stefanecelmaitare--Rebecca06/07"

# MASTER_MAC = None # TODO pe partea de home setup
MASTER_MAC = "58:E6:C5:12:04:C8" # pt MVP1 hardcodat inainte de flash

# MQ2_PIN = None # TODO
# MQ2_THRESHOLD = None # TODO

# traffic generator
TRAFFIC_RATE_PPS = 20

# mvs 
GAIN_LOCK_PACKETS = 100
THRESHOLD_MULT = 2.3 # TODO

# esp now:
ESPNOW_CHANNEL = None # TODO
ESPNOW_MAX_RETRIES = 3
ESPNOW_TX_INTERVAL_MS = 500


# watchdog:
WATCHDOG_SECONDS = 60

SENSOR_POLL_MS = 1000 // TRAFFIC_RATE_PPS


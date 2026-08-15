import time
import sys

sys.path.insert(0, '../shared')

def read_node_id() -> str:
    try:
        with open("node_id.txt", "r") as f:
            node_id = f.read().strip()
    except OSError:
        raise RuntimeError("node_id.txt not found. Write it to the board during deploy.") 

    if not _validate_node_id(node_id):
        raise RuntimeError(f"Invalid node id: {node_id}")

    return node_id 

def _validate_node_id(node_id: str) -> bool:
    if not node_id.startswith("slave_"):
        return False

    suffix = node_id[len("slave_"):]
    return suffix in ("1", "2", "3")

def boot() -> None:
    from config import (WIFI_SSID, WIFI_PASSWORD, MASTER_MAC, MQ2_PIN, MQ2_THRESHOLD, TRAFFIC_RATE_PPS, ESPNOW_TX_INTERVAL_MS)
    from slave_node import SlaveNode

    node_id = read_node_id()
    print(f"[boot] Starting as {node_id}")

    node = SlaveNode(node_id=node_id, wifi_ssid=WIFI_SSID, wifi_password=WIFI_PASSWORD, master_mac=MASTER_MAC, mq2_pin=MQ2_PIN, mq2_threshold=MQ2_THRESHOLD, traffic_rate_pps=TRAFFIC_RATE_PPS)

    node.start()


try:
    boot()
except Exception as e:
    sys.print_exception(e)
    print(f"[boot] fatal error {e}")
    print("[boot] Rebooting in 5s")
    time.sleep(5)
    import machine
    machine.reset()

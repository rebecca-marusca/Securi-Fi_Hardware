import time
import sys

def read_node_id() -> str:
    try:
        with open("node_id.txt", "r") as f:
            node_id = f.read().strip()
    except OSError:
        raise RuntimeError("node_id.txt was not found. Write'master' to it during deploy")

    if node_id != "master":
        raise RuntimeError(f"Invalid node_id '{node_id}', it must be master")

    return node_id


def boot() -> None:
    from config import WIFI_PASSWORD, WIFI_SSID, SLAVE_MACS, MQ2_PIN, MQ2_THRESHOLD, TRAFFIC_RATE_PPS
    from master_node import MasterNode

    node_id = read_node_id()
    print(f"[boot] Starting as {node_id}")

    node = MasterNode(node_id=node_id, wifi_ssid=WIFI_SSID, wifi_password=WIFI_PASSWORD, slave_macs=SLAVE_MACS, mq2_pin=MQ2_PIN, mq2_threshold=MQ2_THRESHOLD, traffic_rate_pps=TRAFFIC_RATE_PPS)

    node.start()

try:
    boot()
except Exception as e:
    sys.print_exception(e)
    print(f"[boot] Fatal error: {e}")
    print(f"[boot] Rebooting in 5s")
    time.sleep(5)
    import machine
    machine.reset()

# branch test
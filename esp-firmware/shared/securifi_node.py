# cand e eroare la import-uri, ignorati-le ca apar pt ca sunteti in python env si nu micro python

import asyncio
import _thread

import machine
import network 
import time 

from .mvs_detector import MVSDetector
from .traffic_generator import TrafficGenerator
from .csi_capture import CSICapture
from .mq2 import MQ2Sensor


WIFI_TIMEOUT_SECONDS = 20
WATCHDOG_SECONDS = 60
SENSOR_POLL_MS = 50
STALE_THRESHOLD_SECONDS = 5

class NodeReading:
    __slots__ = (
        "node_id",

        "timestamp",
        "movement_pct",
        "state",

        "gas_detected",
        "is_calibrated",

        "packets_sent",
        "packets_dropped",
        "pps",

        "raw_mq2_reading",

        "battery_pct",
        "low_battery"
    )

    def __init__(self, node_id: str, timestamp: int, movement_pct: int, state: str, gas_detected: bool, is_calibrated: bool, packets_sent: int, packets_dropped: int, pps: int, raw_mq2_reading: int):
        self.node_id = node_id

        self.timestamp = timestamp
        self.movement_pct = movement_pct
        self.state = state

        self.gas_detected = gas_detected
        self.is_calibrated = is_calibrated

        self.packets_sent = packets_sent
        self.packets_dropped = packets_dropped
        self.pps = pps

        self.raw_mq2_reading = raw_mq2_reading

        self.battery_pct = None # TODO
        self.low_battery = None # TODO

    def __repr__(self): # cum trebuie reprezentat obiectul cand e printat gen NodeReading(id = ..., mvt = ..., . . .)
        return (
            f"NodeReading(id={self.node_id}, "
            f"mvt={self.movement_pct}%, "
            f"state={self.state}, "
            f"gas={self.gas_detected}, "
            f"cal={self.is_calibrated})"
        )


class SecuriFiNode:
    # State enum (mycropython n-are enum)
    STATE_BOOT = 0
    STATE_CALIBRATING = 1
    STATE_STANDBY = 2
    STATE_ARMED = 3
    STATE_DEEP_SLEEP = 4
    STATE_ERROR = 5

    # error codes: 
    ERR_WIFI_FAILED = "wifi_failed"
    ERR_CALIBRATION_FAILED = "calibration_failed"
    ERR_MQTT_FAILED = "mqtt_failed"
    ERR_WATCHDOG = "watchdog_timeout"
    ERR_MEMORY = "memory_error"
    ERR_SENSOR_FLAT = "sensor_flat"

    CALIBRATION_TIMEOUT_S = 120
    WIFI_MAX_ATTEMPTS = 3

    def __init__(self, node_id: str, wifi_ssid: str, wifi_password: str, mq2_pin: int = 2, mq2_threshold: int = 1500, traffic_rate_pps: int = 20): # TODO sa scoatem / modificam valorile hardcodate pt mq2 pin & threshold 
        self._node_id = node_id
        self._wifi_ssid = wifi_ssid
        self._wifi_password = wifi_password

        self._detector = MVSDetector()
        self._mq2 = MQ2Sensor(pin=mq2_pin, threshold=mq2_threshold)

        self._tg_rate = traffic_rate_pps
        self._traffic_gen: TrafficGenerator = None
        self._csi_capture: CSICapture = None

        self._current_reading: NodeReading = None

        self._last_valid_reading_ts: float = 0.0
        self._boot_time: float = time.time()

        self._running = False
        self._mq2.start_warmup()

        self._sensor_flat: bool = False
        self._mq2_history: list = []


    # Outside functions:
    @property
    def node_id(self) -> str:
        return self._node_id

    @property 
    def is_calibrated(self) -> bool:
        return self._detector.is_calibrated

    def get_reading(self) -> NodeReading:
        return self._current_reading

    def start(self) -> None:
        self._running = True

        wlan = self._connect_wifi()
        router_ip = wlan.ifconfig()[2]
        router_mac = self._resolve_router_mac(router_ip)

        self._traffic_gen = TrafficGenerator(target_ip=router_ip, rate_pps=self._tg_rate)
        _thread.start_new_thread(self._traffic_gen.run, ())

        self._csi_capture = CSICapture(detector=self._detector, router_mac=router_mac)
        self._csi_capture.start()
        _thread.start_new_thread(self._csi_capture.run, ())
        self._wait_for_calibration()

        asyncio.run(self._main_loop())

    def stop(self) -> None:
        self._running = False
        if self._traffic_gen:
            self._traffic_gen.stop()
        if self._csi_capture:
            self._csi_capture.stop()


    # async:
    async def _main_loop(self) -> None:
        coroutines = [self._loop_sensor_poll(), self._loop_watchdog()]
        coroutines.extend(self._subclass_coroutines())

        await asyncio.gather(*coroutines)


    async def _loop_sensor_poll(self) -> None:
        while self._running:
            if self._detector.is_calibrated:
                try:
                    movement_pct, state = self._detector.get_reading()
                    mq2_reading = self._mq2.read()

                    self._current_reading = NodeReading(
                        node_id=self._node_id,
                        timestamp=int(time.time()),
                        movement_pct=movement_pct,
                        state=state,
                        gas_detected=mq2_reading.gas_detected,
                        raw_mq2_reading=mq2_reading.raw_value,
                        is_calibrated=True,
                        packets_sent=self._traffic_gen.packets_sent if self._traffic_gen else 0,
                        packets_dropped=self._traffic_gen.packets_dropped if self._traffic_gen else 0,
                        pps=self._tg_rate
                    )

                    self._last_valid_reading_ts = time.time()
                except Exception as e:
                    print(f"[{self._node_id}] Sensor poll error (recoverable): {e}")

            await asyncio.sleep_ms(SENSOR_POLL_MS)

    async def _loop_watchdog(self) -> None:
        await asyncio.sleep(30) # pauza magica :)

        while self._running:
            await asyncio.sleep(10)

            if self._last_valid_reading_ts == 0:
                continue

            elapsed = time.time() - self._last_valid_reading_ts
            if elapsed > WATCHDOG_SECONDS:
                self._soft_reboot(self.ERR_WATCHDOG)


    # subclass hook:
    def _subclass_coroutines(self) -> list:
        # isi va lua override in slave si master node
        return []


    # wifi helpers:
    def _connect_wifi(self):
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)

        for attempt in range(self.WIFI_MAX_ATTEMPTS):
            print(f"[{self.node_id}] Wiif attempt {attempt + 1}/{self.WIFI_MAX_ATTEMPTS}")

            wlan.connect(self._wifi_ssid, self._wifi_password)
            deadline = time.time() + WIFI_TIMEOUT_SECONDS

            while not wlan.isconnected():
                if time.time() > deadline:
                    wlan.disconnect()
                    time.sleep(1)
                    break
                time.sleep(0.5)

            if wlan.isconnected():
                print(f"[{self._node_id}] Wifi connected, IP: {wlan.ifconfig()[0]}")
                return wlan 

        self._soft_reboot(self.ERR_WIFI_FAILED)

    def _resolve_router_mac(self, router_ip: str):
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.connect((router_ip, 80))
            s.close()
        except OSError:
            pass

        try: 
            import esp 
            arp = esp.arp_table()
            for ip, mac_bytes in arp:
                if ip == router_ip:
                    return ":".join(f"{b:02X}" for b in mac_bytes)
        except (ImportError, AttributeError):
            pass

        return None

    def _wait_for_calibration(self) -> None:
        print(f"[{self._node_id}] Calibrating...")
        start = time.time()

        while not self._detector.is_calibrated:
            elapsed = int(time.time() - start)

            if elapsed > self.CALIBRATION_TIMEOUT_S:
                self._soft_reboot(self.ERR_CALIBRATION_FAILED)

            if elapsed % 5 == 0:
                print(f"[{self._node_id}] Calibrating... {elapsed}s / {self.CALIBRATION_TIMEOUT_S}s")

            time.sleep(0.5)

        print(f"[{self._node_id}] Calibrated in {int(time.time() - start)}s")

    def _soft_reboot(self, reason: str) -> None:
        print(f"[{self._node_id}] SOFT REBOOT: {reason}")

        time.sleep(1)
        machine.reset()

    def _enter_deep_sleep(self) -> None: # TODO: De verificat si de testat, asta e kill switch-ul
        print(f"[{self._node_id}] Entering deep sleep, weke via the pysical button only")
        self.stop()
        time.sleep(0.5)

        try:
            import machine
            wake_pin = machine.Pin(0, machine.Pin.IN, machine.Pin.PULL_UP) # TODO decis butonul si modul
            machine.wake_on_ext0(pin=wake_pin, level=0)
            machine.deepsleep()
        except (OSError, ImportError) as e:
            print(f"[{self._node_id}] Failed to enter deepsleep: {e}")


# TODO: implementat battery % 
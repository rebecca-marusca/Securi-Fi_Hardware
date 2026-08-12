import asyncio
import json

from  shared.securifi_node import SecuriFiNode
from config import MASTER_MAC, ESPNOW_TX_INTERVAL_MS, ESPNOW_CHANNEL, ESPNOW_MAX_RETRIES


class SlaveNode(SecuriFiNode):
    def __init__(self, node_id: str, wifi_ssid: str, wifi_password: str, master_mac: str = MASTER_MAC, mq2_pin: int = 2, mq2_threshold: int = 1500, traffic_rate_pps: int = 20):
        super().__init__(node_id=node_id, wifi_ssid=wifi_ssid, wifi_password=wifi_password, mq2_pin=mq2_pin, mq2_threshold=mq2_threshold, traffic_rate_pps=traffic_rate_pps)

        self._master_mac = master_mac
        self._master_mac_bytes = self._parse_mac(self._master_mac) if master_mac else None
        self._espnow = None

        self._tx_success = 0
        self._tx_failed = 0

    # hook:
    def _subclass_coroutines(self) -> list:
        self._init_espnow()
        return [self._loop_espnow_tx()]


    # esp-now:
    def _init_espnow(self) -> None:
        try:
            import espnow 
            self._espnow = espnow.ESPNow()
            self._espnow.active(True)

            if self._master_mac_bytes is None:
                raise RuntimeError("MASTER_MAC not set in config")
            self._espnow.add_peer(self._master_mac_bytes, channel=ESPNOW_CHANNEL)

            print(f"[{self._node_id}]: ESP-NOW initialized, master peer: {self._master_mac}")
        except ImportError:
            print("Asigurati-va ca sunteti pe MicroPython :))")
            self._espnow = None


    # tx loop
    async def _loop_espnow_tx(self) -> None:
        while not self._detector.is_calibrated:
            await asyncio.sleep_ms(200)

        print(f"[{self._node_id}]: Starting ESP-NOW TX")

        while self._running:
            reading = self.get_reading()

            if reading is not None:
                payload = self._build_payload(reading)
                await self._send_with_retry(payload)

            await asyncio.sleep_ms(ESPNOW_TX_INTERVAL_MS)

    async def _send_with_retry(self, payload: bytes) -> None:
        if self._espnow is None:
            return

        for attempt in range(ESPNOW_MAX_RETRIES):
            try:
                success = self._espnow.send(self._master_mac_bytes, payload)
                if success:
                    self._tx_success += 1
                    return

                await asyncio.sleep_ms(50 * (attempt + 1))
            except OSError:
                await asyncio.sleep_ms(100 * (attempt + 1))

        self._tx_failed += 1


    def _build_payload(self, reading) -> bytes:
        data = {
            "id": reading.node_id,
            "ts": reading.timestamp,
            "mvt": reading.movement_pct,
            "st": reading.state,
            "gas": reading.gas_detected,
            "pkt": reading.packets_sent,
            "drp": reading.packets_dropped,
            "mq2": reading.raw_mq2_reading
        }

        return json.dumps(data).encode("utf-8") # dict -> str -> bytes ca esp-now poate transmite numai bytes


    # helper:
    @staticmethod
    def _parse_mac(mac_str: str) -> bytes:
        parts = mac_str.strip().split(":")
        return bytes(int(p, 16) for p in parts)

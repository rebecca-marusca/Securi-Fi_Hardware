import asyncio
import json

from shared.securifi_node import SecuriFiNode
from shared.hardware.button.button import Button
from config import MASTER_MAC, ESPNOW_TX_INTERVAL_MS, ESPNOW_CHANNEL, ESPNOW_MAX_RETRIES


class SlaveNode(SecuriFiNode):
    def __init__(self, node_id: str, wifi_ssid: str, wifi_password: str, master_mac: str = MASTER_MAC, mq2_pin: int = 2, mq2_threshold: int = 1500, battery_pin: int = 3, traffic_rate_pps: int = 20):
        super().__init__(node_id=node_id, wifi_ssid=wifi_ssid, wifi_password=wifi_password, mq2_pin=mq2_pin, mq2_threshold=mq2_threshold, battery_pin=battery_pin, traffic_rate_pps=traffic_rate_pps)

        self._master_mac = master_mac
        self._master_mac_bytes = self._parse_mac(self._master_mac) if master_mac else None
        self._espnow = None
        self._button = Button()

        self._tx_success = 0
        self._tx_failed = 0


    # hook:
    def _subclass_coroutines(self) -> list:
        self._init_espnow()
        return [self._loop_espnow_tx(), self._loop_espnow_rx(), self._loop_request_state(), self._loop_button_poll()]


    # esp-now:
    def _init_espnow(self) -> None:
        try:
            import espnow 
            self._espnow = espnow.ESPNow()
            self._espnow.active(True)

            if self._master_mac_bytes is None:
                raise RuntimeError("MASTER_MAC not set in config")
            self._espnow.add_peer(self._master_mac_bytes, channel=ESPNOW_CHANNEL)

            print(f"[{self._node_id}] ESP-NOW initialized, master peer: {self._master_mac}")
        except ImportError:
            print("Asigurati-va ca sunteti pe MicroPython :))")
            self._espnow = None
        except (RuntimeError, OSError) as e:
            print(f"[{self._node_id}] ESP-NOW init failed: {e}")
            self._soft_reboot(self.ERR_ESPNOW_FAILED)

    def _handle_espnow_command(self, cmd: dict) -> None:
        command = cmd.get("cmd")

        if command == "arm":
                success = self._resume_sensing() and self._mq2.power_switch(True)
                if success:
                    self._state = self.STATE_ARMED
                    print(f"[{self._node_id}] ARMED")
                else:
                    print(f"[{self._node_id}] Failed to arm — staying in current state")
                self._send_confirmation_to_master(success=success, cmd="arm")
        elif command == "standby":
                success = self._pause_sensing() and self._mq2.power_switch(False)
                self._state = self.STATE_STANDBY
                print(f"[{self._node_id}] STANDBY")
                self._send_confirmation_to_master(success=success, cmd="disarm")
        elif command == "sleep":
                self._send_confirmation_to_master(success=True, cmd="deep_sleep")
                self._enter_deep_sleep()
        elif command == "reboot":
                self._soft_reboot("master_command")
        

    def _send_confirmation_to_master(self, success: bool, cmd: str) -> None:
        payload = json.dumps({
            "type": "confirm",
            "node_id": self._node_id,
            "cmd": cmd,
            "success": success
        })
        self._espnow.send(self._master_mac_bytes, payload.encode("utf-8"))



    # tx loop
    async def _loop_espnow_tx(self) -> None:
        while not self._detector.is_calibrated:
            await asyncio.sleep_ms(200)

        print(f"[{self._node_id}] Calibrated, entering standby")

        while self._running:
            if self._state == self.STATE_ARMED:
                reading = self.get_reading()

                if reading is not None:
                    payload = self._build_payload(reading)
                    await self._send_with_retry(payload)

            await asyncio.sleep_ms(ESPNOW_TX_INTERVAL_MS)

    async def _loop_espnow_rx(self) -> None: 
        while self._running:
            if self._espnow is None:
                await asyncio.sleep_ms(100)
                continue

            try:
                result = self._espnow.recv(0) 
                if result is not None:  
                    mac, data = result
                    try:
                        cmd = json.loads(data.decode("utf-8"))
                        self._handle_espnow_command(cmd)
                    except ValueError as e:
                        print(f"[{self._node_id}] Failed to parse command: {e}")
            except OSError as e:
                print(f"[{self._node_id}] ESP-NOW recv error: {e}")

            await asyncio.sleep_ms(10)

    async def _loop_request_state(self) -> None:
        if self._espnow is None or self._master_mac_bytes is None:
            return

        for attempt in range(3):
            try:
                payload = json.dumps({"cmd": "state_request"}).encode("utf-8")
                self._espnow.send(self._master_mac_bytes, payload)
                print(f"[{self._node_id}] Requested current state from master (attempt {attempt + 1})")
            except OSError as e:
                print(f"[{self._node_id}] Failed to request state: {e}")

            await asyncio.sleep_ms(1000)

            if self._state == self.STATE_ARMED:
                return
        
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
        print(f"[{self._node_id}] Failed to send after {ESPNOW_MAX_RETRIES} attempts, total failures: {self._tx_failed}")


    def _build_payload(self, reading) -> bytes:
        data = {
            "id": reading.node_id,
            "ts": reading.timestamp,
            "mvt": reading.movement_pct,
            "st": reading.state,
            "gas": reading.gas_detected,
            "pkt": reading.packets_sent,
            "drp": reading.packets_dropped,
            "mq2": reading.raw_mq2_reading,
            "bat": reading.battery_pct,
            "low_bat": reading.low_battery,
            "sen_flat": self._sensor_flat
        }

        return json.dumps(data).encode("utf-8") # dict -> str -> bytes ca esp-now poate transmite numai bytes

    async def _loop_button_poll(self) -> None:
        while self._running:
            result = self._button.press_check()
            if result == "long":
                self._on_long_press()
            elif result == "short":
                self._on_short_press()
            await asyncio.sleep_ms(50)
    
    def _on_short_press(self) -> None:
        print(f"[{self._node_id}] Button: entering deep sleep")
        self._send_confirmation_to_master(success=True, cmd="deep_sleep")
        self._enter_deep_sleep()
    
    def _on_long_press(self) -> None:
        print(f"[{self._node_id}] Button: long press - entering boot mode")
        #TODO enter boot mode in onboarding
        self._soft_reboot("onboarding_request")
    

    # helper:
    @staticmethod
    def _parse_mac(mac_str: str) -> bytes:
        parts = mac_str.strip().split(":")
        return bytes(int(p, 16) for p in parts)

    
    
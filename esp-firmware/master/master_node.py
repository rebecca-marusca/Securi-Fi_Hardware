import asyncio
import json
import network
import time

from shared.securifi_node import SecuriFiNode, NodeReading
from config import MQTT_BROKER, MQTT_PORT, MQTT_PASSWORD, MQTT_USERNAME, MQTT_TOPIC, MQTT_CLIENT_ID, MQTT_PUBLISH_INTERVAL_MS, ESPNOW_CHANNEL, SLAVE_MACS, SLAVE_TIMEOUT_MS, DETECTION_PROBABILITY_THRESHOLD, MQTT_RECONNECT_ATTEMPTS

class SlaveState:
    __slots__ = ("node_id", "last_seen_ms", "reading")

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.last_seen_ms: int = 0
        self.reading: dict = None


class MasterNode(SecuriFiNode):
    def __init__(self, node_id: str, wifi_ssid: str, wifi_password: str, slave_macs: list = None, mq2_pin: int = 0, mq2_threshold: int = 1500, battery_pin: int = 3, traffic_rate_pps: int = 20):
        super().__init__(node_id=node_id, wifi_ssid=wifi_ssid, wifi_password=wifi_password, mq2_pin=mq2_pin, mq2_threshold=mq2_threshold, battery_pin=battery_pin, traffic_rate_pps=traffic_rate_pps)
        self._slave_macs = slave_macs or []
        self._espnow = None
        self._mqtt = None

        self._slave_states: dict = {}
        for i, mac in enumerate(self._slave_macs):
            mac_bytes = self._parse_mac(mac)
            self._slave_states[mac_bytes] = SlaveState(node_id=f"slave_{i + 1}")

        self._own_mac: str = None
        self._armed: bool = False

    def _subclass_coroutines(self) -> list:
        self._own_mac = self._read_own_mac()
        self._init_espnow()
        self._init_mqtt()
        self._publish_config_request(self._node_id)
        for state in self._slave_states.values():
            self._publish_config_request(state.node_id)
        return [
            self._loop_espnow_rx(),
            self._loop_mqtt_publish(),
            self._loop_mqtt_commands()
        ]

    def _init_espnow(self) -> None:
        try:
            import espnow
            self._espnow = espnow.ESPNow()
            self._espnow.active(True)

            for mac in self._slave_macs:
                mac_bytes = self._parse_mac(mac)
                self._espnow.add_peer(mac_bytes, channel=ESPNOW_CHANNEL)

            print(f"[{self._node_id}] ESP-NOW initialized, {len(self._slave_macs)} slave peers registered")
        except ImportError:
            print(f"[{self._node_id}] ESP-NOW not available (MycroPython?)")
            self._espnow = None
        except OSError as e:
            print(f"[{self._node_id}] ESP-NOW init failed: {e}")
            self._soft_reboot(self.ERR_ESPNOW_FAILED)

    async def _loop_espnow_rx(self) -> None:
        while self._running:
            if self._espnow is None:
                await asyncio.sleep_ms(100)
                continue

            try:
                result = self._espnow.recv(0)
                if result is not None:
                    mac, data = result
                    self._handle_slave_packet(mac, data)
            except OSError as e:
                print(f"[{self._node_id}] ESP-NOW recv error: {e}")

            await asyncio.sleep_ms(10)


    def _handle_slave_packet(self, mac: bytes, data: bytes) -> None:
        state = self._slave_states.get(mac)
        if state is None:
            return

        try:
            payload = json.loads(data.decode("utf-8"))
        except (ValueError, UnicodeError) as e:
            print(f"[{self._node_id}] Failed to parse slave packet from {mac}: {e}")
            return

        if "confirmed" in payload:
            self._publish_config_confirmation(
                node_id=state.node_id,
                arm=payload.get("armed", False),
                disarm=payload.get("disarm", False),
                deep_sleep=payload.get("deep_sleep", False),
                success=payload.get("confirmed", False)
            )

        if payload.get("cmd") == "state_request":
            response = "arm" if self._state == self.STATE_ARMED else "standby"
            try:
                self._espnow.send(mac, json.dumps({"cmd": response}).encode("utf-8"))
                print(f"[{self._node_id}] Answered state_request from {state.node_id}: {response}")
            except OSError as e:
                print(f"[{self._node_id}] Failed to answer state_request from {state.node_id}: {e}")
                return
        
        state.reading = payload
        state.last_seen_ms = time.ticks_ms()
        


    # mqtt:
    def _init_mqtt(self) -> None:
        try:
            from umqtt.simple import MQTTClient
            self._mqtt = MQTTClient(client_id=MQTT_CLIENT_ID, server=MQTT_BROKER, port=MQTT_PORT, user=MQTT_USERNAME or None, password=MQTT_PASSWORD or None, keepalive=30)
            self._mqtt.connect()
            print(f"[{self._node_id}] MQTT connected to {MQTT_BROKER}:{MQTT_PORT}")
        except ImportError:
            self._mqtt = None
        except OSError as e:
            print(f"[{self._node_id}] MQTT connection failed: {e}")
            self._mqtt = None

    async def _loop_mqtt_publish(self) -> None:
        while not self._detector.is_calibrated:
            await asyncio.sleep_ms(200)

        print(f"[{self._node_id}] Starting MQTT publish loop")

        while self._running:
            if self._state == self.STATE_ARMED:
                if self._mqtt is None:
                    self._init_mqtt()

            own_reading = self.get_reading()
            if own_reading is not None and self._mqtt is not None:
                package = self._build_package(own_reading)
                payload = json.dumps(package).encode("utf-8")
                await self._mqtt_publish(payload)

            await asyncio.sleep_ms(MQTT_PUBLISH_INTERVAL_MS)

    async def _loop_mqtt_commands(self) -> None:
        cmd_topic = f"securifi/config/command/{self._own_mac}"
        last_ping = time.ticks_ms()
        PING_INTERVAL_MS = 15000

        def on_message(topic, msg):
            try:
                data = json.loads(msg.decode("utf-8"))
                command = data.get("cmd")

                if command == "arm":
                        target = data.get("node_id")
                        if target == "master":
                            success = self._resume_sensing() and self._mq2.power_switch(True)
                            if success:
                                self._state = self.STATE_ARMED
                            self._publish_config_confirmation(target, success=success, arm=True)
                        else:
                            self._send_espnow_to(target, {"cmd": "arm"})
                elif command == "standby":
                        target = data.get("node_id")
                        if target == "master":
                            success = self._pause_sensing() and self._mq2.power_switch(False)
                            self._state = self.STATE_STANDBY
                            self._publish_config_confirmation(target, success=success, disarm=True)
                        else:
                            self._send_espnow_to(target, {"cmd": "standby"})
                elif command == "sleep":
                        target = data.get("node_id")
                        if target == "master":
                            self._enter_master_deep_sleep()
                        else:
                            self._send_espnow_to(target, {"cmd": "sleep"})
                elif command == "reboot":
                        target = data.get("node_id")
                        if target == "master":
                            success = self._soft_reboot("server command")
                        else:
                            self._send_espnow_to(target, {"cmd": "reboot"})
            except ValueError as e:
                print(f"[{self._node_id}] Failed to subscribe to cmd topic: {e}")

        if self._mqtt is None:
            return 

        try: 
            self._mqtt.set_callback(on_message)
            self._mqtt.subscribe(cmd_topic)
            print(f"[{self._node_id}] Subscribed to {cmd_topic}")
        except OSError:
            return

        while self._running: 
            try:
                self._mqtt.check_msg()

                if time.ticks_diff(time.ticks_ms(), last_ping) > PING_INTERVAL_MS:
                    self._mqtt.ping()
                    last_ping = time.ticks_ms()
            except OSError:
                await self._mqtt_reconnect()
            await asyncio.sleep_ms(100)

    async def _mqtt_publish(self, payload: bytes) -> None: 
        if self._mqtt is None:
            print(f"[{self._node_id}] Didn't publish: {payload.decode()}")
            return 

        try: 
            self._mqtt.publish(MQTT_TOPIC, payload)
        except OSError:
            await self._mqtt_reconnect()

    async def _mqtt_reconnect(self) -> None: 
        print(f"[{self._node_id}] MQTT lost, attempting reconnect")
        for attempt in range(MQTT_RECONNECT_ATTEMPTS):
            await asyncio.sleep(2)
            try:
                self._mqtt.connect()

                cmd_topic = f"securifi/config/command/{self._own_mac}"
                self._mqtt.subscribe(cmd_topic)

                print(f"[{self._node_id}] MQTT reconnected")
                return
            except OSError:
                print(f"[{self._node_id}] MQTT reconnect attempt {attempt + 1} failed")

        print(f"[{self._node_id}] MQTT reconnect failed, soft rebooting the master...")
        await asyncio.sleep(1)
        self._soft_reboot(self.ERR_MQTT_FAILED)

    def _publish_config_request(self, node_id: str) -> None:
        if self._mqtt is None:
            return
        
        topic = f"securifi/config/request/{self._own_mac}"
        payload = json.dumps({
            "node_id": node_id,
            "master_mac": self._own_mac
        })
        try:
            self._mqtt.publish(topic, payload)
            print(f"[{self._node_id}] Config request sent for node {node_id}")
        except OSError as e:
            print(f"[{self._node_id}] Failed to send config request: {e}")

    def _publish_config_confirmation(self, node_id: str, success: bool, arm: bool = False, disarm: bool = False, deep_sleep: bool = False) -> None:
        if self._mqtt is None:
            return
        
        topic = f"securifi/config/confirm/{self._own_mac}"
        payload = json.dumps({
            "node_id": node_id,
            "master_mac": self._own_mac,
            "arm": arm,
            "disarm": disarm,
            "deep_sleep": deep_sleep,
            "success": success
        })
        try:
            self._mqtt.publish(topic, payload)
            print(f"[{self._node_id}] Config confirmation: node={node_id}, arm={arm}, disarm={disarm}, deep_sleep={deep_sleep}, success={success}")
        except OSError as e:
            print(f"[{self._node_id}] Failed to send config confirmation: {e}")

    # package builder
    def _build_package(self, own_reading: NodeReading) -> dict:
        now_ms = time.ticks_ms()
        nodes = []
        probabilities = []

        own_prob = self._movement_to_probability(own_reading.movement_pct)
        probabilities.append(own_prob)
        nodes.append({
            "node_id": self._node_id,
            "role": "master",
            "state": own_reading.state,
            "movement_pct": own_reading.movement_pct,
            "probability": own_prob,
            "raw_mq2_reading": own_reading.raw_mq2_reading,
            "warnings": {
                "low_battery": own_reading.low_battery,
                "not_transmitting": False,
                "signal_weak": False,
                "sensor_flat": self._sensor_flat
            },
            "sensors":{
                "flame": False, # TODO
                "gas": own_reading.gas_detected,
                "battery_pct": own_reading.battery_pct
            }
        })

        for mac_bytes, state in self._slave_states.items():
            elapsed_ms = time.ticks_diff(now_ms, state.last_seen_ms)
            not_transmitting = (state.last_seen_ms == 0 or elapsed_ms > SLAVE_TIMEOUT_MS)

            if not_transmitting or state.reading is None:
                nodes.append({
                    "node_id": state.node_id,
                    "role": "slave",
                    "state": "IDLE",
                    "movement_pct": 0,
                    "probability": 0.0,
                    "raw_mq2_reading": 0,
                    "warnings": {
                        "low_battery": False, 
                        "not_transmitting": True,
                        "signal_weak": False, 
                        "sensor_flat": False
                    },
                    "sensors":{
                        "flame": False, 
                        "gas": False,
                        "battery_pct": 0
                    }
                })
            else:
                r = state.reading
                prob = self._movement_to_probability(r.get("mvt", 0))
                probabilities.append(prob)
                nodes.append({
                    "node_id": state.node_id,
                    "role": "slave",
                    "state": r.get("st", "IDLE"),
                    "movement_pct": r.get("mvt", 0),
                    "probability": prob,
                    "raw_mq2_reading": r.get("mq2", 0),
                    "warnings": {
                        "low_battery": r.get("low_bat", False),
                        "not_transmitting": False,
                        "signal_weak": False, # TODO
                        "sensor_flat": r.get("sen_flat", False)
                    },
                    "sensors":{
                        "flame": False, # TODO
                        "gas": r.get("gas", False),
                        "battery_pct": r.get("bat", 0)
                    }
                })

        intruder_probability = (sum(probabilities) / len(probabilities) if probabilities else 0.0)
        gas_detected = any(n["sensors"]["gas"] for n in nodes)
        if gas_detected:
            warning_type = "gas"
        elif intruder_probability >= DETECTION_PROBABILITY_THRESHOLD:
            warning_type = "intruder"
        else:
            warning_type = None

        return {
            "master_mac": self._own_mac or "00:00:00:00:00:00",
            "timestamp": str(time.time()),
            "intruder_probability": round(intruder_probability, 4),
            "warning_type": warning_type,
            "nodes": nodes
        }

    # internal helpers:
    @staticmethod
    def _movement_to_probability(movement_pct: int) -> float:
        return 0.0 # TODO

    @staticmethod
    def _parse_mac(mac_str: str) -> bytes:
        parts = mac_str.strip().split(":")
        return bytes(int(p, 16) for p in parts)

    def _read_own_mac(self) -> str:
        try:
            mac_bytes = network.WLAN(network.STA_IF).config("mac")
            return ":".join(f"{b:02X}" for b in mac_bytes)
        except Exception:
            return "00:00:00:00:00:00"

    def _broadcast_espnow(self, cmd: dict) -> None:
        payload = json.dumps(cmd).encode("utf-8")
        for mac_bytes, state in self._slave_states.items():
            try:
                self._espnow.send(mac_bytes, payload)
            except OSError as e:
                print(f"[{self._node_id}] Failed to send {cmd} to {state.node_id}: {e}")

    def _send_espnow_to(self, target: str, cmd: dict) -> None: 
        try:
            index = int(target) - 1
            if index < 0 or index >= len(SLAVE_MACS):
                print(f"[{self.node_id}] Invalid slave target: {target}, known slaves: {len(SLAVE_MACS)}")
                return

            mac_bytes = self._parse_mac(SLAVE_MACS[index])
            payload = json.dumps(cmd).encode("utf-8")
            self._espnow.send(mac_bytes, payload)

            print(f"[{self._node_id}] Sent {cmd} to slave_{target}")
        except (OSError, ValueError, IndexError, TypeError) as e:
            print(f"[{self._node_id}] Failed to send slave {target}: {e}")

    def _enter_master_deep_sleep(self) -> None:
        success = True
        if self._mqtt is not None: 
            try:
                self._mqtt.disconnect()
            except OSError:
                success = False
                pass
        self._publish_config_confirmation(self._node_id,success=success, deep_sleep=True)
        self._enter_deep_sleep()


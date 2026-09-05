import asyncio
import json
import network
import time
import _thread
import  select

from shared.securifi_node import SecuriFiNode, NodeReading
from shared.hardware.button.button import Button
from config import MQTT_BROKER, MQTT_PORT, MQTT_PASSWORD, MQTT_USERNAME, MQTT_TOPIC, MQTT_CLIENT_ID, MQTT_PUBLISH_INTERVAL_MS, ESPNOW_CHANNEL, SLAVE_MACS, SLAVE_TIMEOUT_MS, DETECTION_PROBABILITY_THRESHOLD, MQTT_RECONNECT_ATTEMPTS
#TODO timestamp to real time
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
        self._mqtt_connected = False
        self._mqtt_thread_started = False
        self._mqtt_shutdown = False

        self._mqtt_out_lock = _thread.allocate_lock()
        self._mqtt_out_queue = []          # confirmations/requests — small, sent in order, never dropped
        self._mqtt_latest_telemetry = None  # only the newest telemetry payload matters, so no unbounded growth

        self._mqtt_in_lock = _thread.allocate_lock()
        self._mqtt_in_queue = [] 

        self._slave_states: dict = {}
        for i, mac in enumerate(self._slave_macs):
            mac_bytes = self._parse_mac(mac)
            self._slave_states[mac_bytes] = SlaveState(node_id=f"slave_{i + 1}")

        self._own_mac: str = None
        self._armed: bool = False

    def _subclass_coroutines(self) -> list:
        self._init_espnow()
        self._publish_config_request(self._node_id)
        for state in self._slave_states.values():
            self._publish_config_request(state.node_id)
        return [
            self._loop_espnow_rx(),
            self._loop_mqtt_publish(),
            self._loop_mqtt_commands(),
            self._loop_button_poll()
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
                    if mac is None or data is None:
                        await asyncio.sleep_ms(10)
                        continue
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
                cmd=payload.get("cmd", None),
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
    def _on_wifi_connected(self) -> None:
        self._own_mac = self._read_own_mac()
        if not self._mqtt_thread_started:
            self._mqtt_thread_started = True
            _thread.start_new_thread(self._mqtt_thread_main, ())

    def _mqtt_thread_main(self) -> None:
        from umqtt.simple import MQTTClient
        cmd_topic = f"securifi/config/command/{self._own_mac}"
        last_ping = time.ticks_ms()
        PING_INTERVAL_MS = 15000

        def on_message(topic, msg):
            try:
                data = json.loads(msg.decode("utf-8"))
            except ValueError:
                return
            with self._mqtt_in_lock:
                self._mqtt_in_queue.append(data)

        while True:
            if self._mqtt_shutdown:
                if self._mqtt is not None:
                    try:
                        self._mqtt.disconnect()
                    except OSError:
                        pass
                return

            if self._mqtt is None:
                try:
                    client = MQTTClient(client_id=MQTT_CLIENT_ID, server=MQTT_BROKER, port=MQTT_PORT, user=MQTT_USERNAME or None, password=MQTT_PASSWORD or None, keepalive=30)
                    client.connect()
                    if hasattr(client, "sock") and client.sock is not None:
                        try:
                            client.sock.settimeout(2)
                        except Exception:
                            pass
                    client.set_callback(on_message)
                    client.subscribe(cmd_topic)
                    self._mqtt = client
                    self._mqtt_connected = True
                    last_ping = time.ticks_ms()
                    print(f"[{self._node_id}] MQTT connected (thread)")
                except (OSError, IndexError) as e:
                    print(f"[{self._node_id}] MQTT connect failed (thread) {e}")
                    self._mqtt = None
                    self._mqtt_connected = False
                    time.sleep(2)
                    continue
            try:
                if hasattr(self._mqtt, "sock") and self._mqtt.sock is not None:
                    readable, _, _ = select.select([self._mqtt.sock], [], [], 0.1)
                    if readable:
                        self._mqtt.check_msg()
                else:
                    self._mqtt.check_msg()
    
                if time.ticks_diff(time.ticks_ms(), last_ping) > PING_INTERVAL_MS:
                    print(f"[{self._node_id}] before ping")
                    self._mqtt.ping()
                    print(f"[{self._node_id}] after ping")
                    last_ping = time.ticks_ms()

                with self._mqtt_out_lock:
                    pending = self._mqtt_out_queue[:]
                    self._mqtt_out_queue.clear()
                    telemetry = self._mqtt_latest_telemetry
                    self._mqtt_latest_telemetry = None

                for topic, payload in pending:
                    self._mqtt.publish(topic, payload)

                if telemetry is not None:
                    print(f"[{self._node_id}] before publish telemetry")
                    self._mqtt.publish(MQTT_TOPIC, telemetry)
                    print(f"[{self._node_id}] after publish telemetry")

            except OSError as e:
                print(f"[{self._node_id}] MQTT thread error: {e}")
                try:
                    self._mqtt.disconnect()
                except Exception:
                    pass
                self._mqtt = None
                self._mqtt_connected = False

            time.sleep_ms(100)

    def _mqtt_enqueue(self, topic: str, payload: bytes) -> None:
        with self._mqtt_out_lock:
            self._mqtt_out_queue.append((topic, payload))

    def _mqtt_enqueue_telemetry(self, payload: bytes) -> None:
        with self._mqtt_out_lock:
            self._mqtt_latest_telemetry = payload

    async def _loop_mqtt_publish(self) -> None:
        while not self._detector.is_calibrated:
            await asyncio.sleep_ms(200)

        print(f"[{self._node_id}] Starting MQTT publish loop")

        while self._running:
            if self._state == self.STATE_ARMED:
                own_reading = self.get_reading()
                if own_reading is not None:
                    package = self._build_package(own_reading)
                    payload = json.dumps(package).encode("utf-8")
                    self._mqtt_enqueue_telemetry(payload)
            await asyncio.sleep_ms(MQTT_PUBLISH_INTERVAL_MS)

    async def _loop_mqtt_commands(self) -> None:
        while self._running:
            with self._mqtt_in_lock:
                pending = self._mqtt_in_queue[:]
                self._mqtt_in_queue.clear()

            for data in pending:
                self._handle_mqtt_command(data)

            await asyncio.sleep_ms(100)

    def _handle_mqtt_command(self, data: dict) -> None:
        command = data.get("cmd")
        target = data.get("node_id")

        if command == "arm":
            if target == "master":
                sensing = self._resume_sensing()
                mq2_state = self._mq2.power_switch(True)
                print(f"[{self._node_id}] sensing: {sensing}, mq2 on: {mq2_state}")
                success = sensing and mq2_state
                if success:
                    self._state = self.STATE_ARMED
                self._publish_config_confirmation(target, success=success, cmd="arm")
            else:
                self._send_espnow_to(target, {"cmd": "arm"})
        elif command == "standby":
            if target == "master":
                sensing = self._pause_sensing()
                mq2_state = self._mq2.power_switch(False)
                buzzer_off = self._buzzer.buzzer_stop()
                print(f"[{self._node_id}] sensing paused: {sensing}, mq2 off: {mq2_state}, buzzer: {buzzer_off}")
                success = sensing and mq2_state and buzzer_off
                self._state = self.STATE_STANDBY
                self._publish_config_confirmation(target, success=success, cmd="disarm")
            else:
                self._send_espnow_to(target, {"cmd": "standby"})
        elif command == "buzzer_on_alarm":                        
            if target == "master":
                success = self._buzzer.movement_alarm()
                self._publish_config_confirmation(target, success=success, cmd="buzzer_on_alarm")
            else:
                self._send_espnow_to(target, {"cmd": "buzzer_on_alarm"})
        elif command == "buzzer_on_warning":                    
            if target == "master":
                success = self._buzzer.gas_alarm()
                self._publish_config_confirmation(target, success=success, cmd="buzzer_on_warning")
            else:
                self._send_espnow_to(target, {"cmd": "buzzer_on_warning"})
        elif command == "buzzer_off":
            if target == "master":
                success = self._buzzer.buzzer_stop()
                self._publish_config_confirmation(target, success=success, cmd="buzzer_off")
            else:
                self._send_espnow_to(target, {"cmd": "buzzer_off"})
        elif command == "sleep":                
            if target == "master":
                self._publish_config_confirmation(self._node_id, success=True, cmd="deep_sleep")
                self._enter_master_deep_sleep()
            else:
                self._send_espnow_to(target, {"cmd": "sleep"})
        elif command == "reboot":                
            if target == "master":
                success = self._soft_reboot("server command")
            else:
                self._send_espnow_to(target, {"cmd": "reboot"})

    def _publish_config_request(self, node_id: str) -> None:
        topic = f"securifi/config/request/{self._own_mac}"
        payload = json.dumps({
            "node_id": node_id,
            "role": "master" if node_id == self._node_id else "slave",
            "master_mac": self._own_mac
        }).encode("utf-8")
        self._mqtt_enqueue(topic, payload)
        print(f"[{self._node_id}] Config request queued for node {node_id}")

    def _publish_config_confirmation(self, node_id: str, success: bool, cmd: str) -> None:
        topic = f"securifi/config/confirm/{self._own_mac}"
        payload = json.dumps({
            "node_id": node_id,
            "master_mac": self._own_mac,
            "cmd": cmd,
            "success": success
        }).encode("utf-8")
        self._mqtt_enqueue(topic, payload)
        print(f"[{self._node_id}] Config confirmation queued: node={node_id}, cmd={cmd}, success={success}")

    # package builder
    def _build_package(self, own_reading: NodeReading) -> dict:
        now_ms = time.ticks_ms()
        nodes = []
        probabilities = []

        own_prob = self._movement_to_probability(own_reading.movement_pct)
        probabilities.append(own_prob)
        nodes.append({
            "node_id": self._node_id,
            "movement_pct": own_reading.movement_pct,
            "sensor_reading": own_reading.sensor_reading,
            "battery_pct": own_reading.battery_pct,
            "report_type": own_reading.report_type, #not_transmitting, weak_signal, low_battery
            "warning_type": own_reading.warning_type #fire, gas
        })
        #  nodes: node_id, movement_pct, sensor_reading, battery_pct, report_type, warning_type, is_alarm

        for mac_bytes, state in self._slave_states.items():
            elapsed_ms = time.ticks_diff(now_ms, state.last_seen_ms)
            not_transmitting = (state.last_seen_ms == 0 or elapsed_ms > SLAVE_TIMEOUT_MS)

            if not_transmitting or state.reading is None:
                nodes.append({
                    "node_id": state.node_id,
                    "movement_pct": 0,
                    "sensor_reading": 0,
                    "report_type": None,
                    "warning_type": None,
                    "battery_pct": 0
                })
            else:
                r = state.reading
                prob = self._movement_to_probability(r.get("mvt", 0))
                probabilities.append(prob)
                nodes.append({
                    "node_id": state.node_id,
                    "movement_pct": r.get("mvt", 0),
                    "seonsor_reading": r.get("mq2", 0),
                    "report_type":r.get("rep", None),
                    "warning_type": r.get("war", None),
                    "battery_pct": r.get("bat", 0)
                })

        intruder_probability = (sum(probabilities) / len(probabilities) if probabilities else 0.0)
        gas_detected = any(n["warning_type"] == "gas" for n in nodes)
        if gas_detected:
            warning_type = "gas"
        elif intruder_probability >= DETECTION_PROBABILITY_THRESHOLD:
            warning_type = "intruder"
        else:
            warning_type = None

        return {
            "master_mac": self._own_mac or "00:00:00:00:00:00",
            "timestamp": str(time.time()),
            "warning_type": warning_type,
            "nodes": nodes
        }

    # button:
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
        self._publish_config_confirmation(self._node_id, success=True, cmd="deep_sleep")
        self._enter_master_deep_sleep()

    def _on_long_press(self) -> None:
        print(f"[{self._node_id}] Button: long press - entering boot mode")
        #TODO enter boot mode in onboarding
        self._soft_reboot("onboarding_request")


    # internal helpers:
    @staticmethod
    def _movement_to_probability(movement_pct: int) -> float:
            return 0.0

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
            if not target.startswith("slave_"):
                print(f"[{self._node_id}] Invalid slave target: {target}")
                return
            
            index = int(target.split("_")[1]) - 1
            print(f"[{self._node_id}] ESP-NOW index={index}")
            if index < 0 or index >= len(SLAVE_MACS):
                print(f"[{self._node_id}] Invalid slave target: {target}, known slaves: {len(SLAVE_MACS)}")
                return

            mac_bytes = self._parse_mac(SLAVE_MACS[index])
            payload = json.dumps(cmd).encode("utf-8")
            self._espnow.send(mac_bytes, payload)

            print(f"[{self._node_id}] Sent {cmd} to slave_{target}")
        except (OSError, ValueError, IndexError, TypeError) as e:
            print(f"[{self._node_id}] Failed to send slave {target}: {e}")

    def _enter_master_deep_sleep(self) -> None:
        self._mqtt_shutdown = True
        time.sleep_ms(200)
        self._enter_deep_sleep()


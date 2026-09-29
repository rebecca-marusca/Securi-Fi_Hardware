import time #TODO fix gas alarm

DEFAULT_BUZZER_PIN = 8
BEEP_TIME_MS = 1000

class Buzzer:
    def __init__(self):
        self._buz_pin = None
        self._beep_start = None
        self._buz = False
        self._gas_alarm_active = False
        
        self._init_buz_pin()

    # outside functions:
    def movement_alarm(self) -> bool:
        if self._buz_pin is None:
            return False
        try:
            self._buz_pin.value(1)    
            return True
        except Exception:
            return False

    def gas_alarm(self) -> bool:
        if self._buz_pin is None:
            return False
        self._gas_alarm_active = True
        return True

    def update(self) -> None:
        if not self._gas_alarm_active or self._buz_pin is None:
            return
        
        try:
            if self._beep_start is None:
                self._beep_start = time.ticks_ms()
                self._buz_pin.value(0 if self._buz else 1)

            elapsed = time.ticks_diff(time.ticks_ms(), self._beep_start)

            if elapsed >= BEEP_TIME_MS:
                self._buz = not self._buz
                self._beep_start = None
        except Exception:
            pass     

    def buzzer_stop(self) -> None:
        if self._buz_pin is None:
            return False
        try:
            self._buz_pin.value(0)
            self._beep_start = None
            self._buz = False
            self._gas_alarm_active = False
            return True
        except Exception:
            return False
            
    # internal helpers:
    def _init_buz_pin(self) -> None:
        try:
            from machine import Pin
            self._buz_pin = Pin(DEFAULT_BUZZER_PIN, Pin.OUT)
            self._buz_pin.value(0)
        except (ImportError, AttributeError):
            self._buz_pin = None



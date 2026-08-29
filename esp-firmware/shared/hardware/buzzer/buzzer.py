import time

DEFAULT_BUZZER_PIN = 8
BEEP_TIME_MS = 1000

class Buzzer:
    def __init__(self):
        self._buz_pin = None
        self._beep_start = None
        self._buz = False

        self._init_buz_pin()

    # outside functions:
    def toggle_buzzer(self, toggle: bool) -> bool:
        if self._buz_pin is None:
            return False
        try:
            if toggle:
                self._buz_pin.value(1)
            else:
                self._buz_pin.value(0)
            return True
        except Exception:
            return False

    def gas_alarm(self, toggle:bool) -> bool:
        if self._buz_pin is None:
            return False
        
        try:
            if toggle:
                if self._beep_start is None:
                    self._beep_start = time.ticks_ms()
                    self._buz_pin.value(0 if self._buz else 1)

                elapsed = time.ticks_diff(time.ticks_ms(), self._beep_start)

                if elapsed >= BEEP_TIME_MS:
                    self._buz = not self._buz
                    self._beep_start = None
            else:
                self._buz_pin.value(0)
                self._beep_start = None
                self._buz = False
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



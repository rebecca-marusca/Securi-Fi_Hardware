import time

DEFAULT_BUTTON_PIN = 3
LONG_PRESS_TIME = 3

class Button:
    def __init__(self):
        self._button_pin = None
        self._press_start = None

        self._init_button_pin()

    # outside functions:
    def press_check(self):
        pressed = self._is_pressed()

        if pressed and self._press_start is None:
            self._press_start = time.time()

        elif not pressed and self._press_start is not None:
            duration = time.time() - self._press_start
            self._press_start = None

            if duration >= LONG_PRESS_TIME:
                return "long"
            else:
                return "short"

        return None
    
    # internal helpers:
    def _init_button_pin(self):
        try:
            from machine import Pin
            self._button_pin = Pin(DEFAULT_BUTTON_PIN, Pin.IN, Pin.PULL_UP)
        except (ImportError, AttributeError):
            self._button_pin = None

    def _is_pressed(self) -> int:
        if self._button_pin is None:
            return False
        
        return self._button_pin.value() == 0
    
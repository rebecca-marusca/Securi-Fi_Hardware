# cand e eroare la import-uri, ignorati-le ca apar pt ca sunteti in python env si nu micro python
#OBS: DACA SENZORUL NU E CONECTAT LA D0, CONECTATI D0 LA UN GND CA SA NU AVETI NOISE 
import time 

WARMUP_SECONDS = 30
DEFAULT_ADC_PIN = 1
DEFAULT_THRESHOLD = 1500
DEFAULT_POWER_PIN = 2
CONSECUTIVE_TRIGGER_COUNT = 3


class MQ2Reading:
    __slots__ = (
        "raw_value",
        "gas_detected",
        "is_ready"
    )

    def __init__(self, raw_value: int, gas_detected: bool, is_ready: bool):
        self.raw_value = raw_value
        self.gas_detected = gas_detected
        self.is_ready = is_ready

    def __repr__(self):
        return (f"MQ2Reading(raw={self.raw_value}, gas={self.gas_detected}, ready={self.is_ready})")

class MQ2Sensor:
    def __init__(self, pin: int = DEFAULT_ADC_PIN, threshold: int = DEFAULT_THRESHOLD):
        self._pin_num = pin
        self._threshold = threshold
        self._adc = None
        self._warmup_start = None
        self._consecutive_count = 0
        self._power_pin = None

        self._last_raw = 0
        self._last_gas_detected = False
        self._init_adc()
        self._init_power_pin()


    # outside functions:
    @property
    def is_ready(self) -> bool:
        if self._warmup_start is None:
            return False

        elapsed = time.time() - self._warmup_start
        return elapsed >= WARMUP_SECONDS

    @property
    def warmup_remaining(self) -> int:
        if self._warmup_start is None:
            return WARMUP_SECONDS

        elapsed = time.time() - self._warmup_start
        remaining = WARMUP_SECONDS - elapsed

        return max(0, int(remaining))

    def start_warmup(self) -> None:
        if self._warmup_start is None:
            self._warmup_start = time.time()


    def read(self) -> MQ2Reading:
        if self._adc is None:
            return MQ2Reading(raw_value=0, gas_detected=False, is_ready=False)

        raw = self._adc.read()
        self._last_raw = raw

        if raw >= self._threshold:
            self._consecutive_count += 1
        else:
            self._consecutive_count = 0

        ready = self.is_ready
        if self._consecutive_count >= CONSECUTIVE_TRIGGER_COUNT and ready:
            gas_detected = True
        else:
            gas_detected = False

        self._last_gas_detected = gas_detected

        return MQ2Reading(raw_value=self.normalize_mq2_reading(raw), gas_detected=gas_detected, is_ready=ready)

    def last_reading(self) -> MQ2Reading:
        return MQ2Reading(raw_value=self._last_raw, gas_detected=self._last_gas_detected, is_ready=self.is_ready)

    def power_switch(self, switch: bool) -> bool:
        if self._power_pin is None:
            return False
        try:
            if switch:
                self._power_pin.value(1)
                if self._warmup_start is None:
                    self._warmup_start = time.time()
                return self._power_pin.value() == 1
            else:
                self._power_pin.value(0)
                self._warmup_start = 0
                self._consecutive_count = 0
                self._last_raw = 0
                self._last_gas_detected = False
                return self._power_pin.value() == 0
        except Exception:
            return False

    # internal helpers:
    def _init_adc(self) -> None:
        try:
            from machine import ADC, Pin
            pin = Pin(self._pin_num)
            self._adc = ADC(pin)

            # full scale de ~ 3.3V
            self._adc.atten(ADC.ATTN_11DB)
            self._adc.width(ADC.WIDTH_12BIT)
        except (ImportError, AttributeError):
            self._adc = None

    def _init_power_pin(self)  -> None:
        try:
            from machine import Pin
            self._power_pin = Pin(DEFAULT_POWER_PIN, Pin.OUT)
            self._power_pin.value(0)
        except (ImportError, AttributeError):
            self._power_pin = None
    
    @staticmethod
    def normalize_mq2_reading(raw_val: int) -> int: # din cauza voltage divider-ului voltajul dat de mq2 e redus ca urmare trebuie sa normalizam valoarea data
        # pt putin context Vs = Vcc * R2 / (R1 + R2), unde noi avem Vcc = 5V, R1 = 10k, R2 = 15k, Vs =  3V (nu 3.3V ca sa lasam un pic de gap)
        ratio = 5 / 3

        return int(raw_val * ratio)


        
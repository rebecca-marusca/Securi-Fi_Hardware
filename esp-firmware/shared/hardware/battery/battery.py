import time

DEFAULT_ADC_PIN = 3
SAMPLE_COUNT = 10
MAX_JUMP_PCT = 15
EMA_ALPHA = 0.3

_VOLTAGE_CURVE = [
    (4.20, 100),
    (4.00, 85),
    (3.85, 70),
    (3.75, 50),  
    (3.65, 30),
    (3.50, 15),
    (3.30, 5),
    (3.00, 0),
]
DIVIDER_RATIO = 2.0
ADC_REF_VOLTAGE = 3.3
ADC_MAX_RAW = 4095

class BatteryReading:
    __slots__ = (
        "voltage",
        "percentage",
        "is_low"
    )

    def __init__(self, voltage: float, percentage: int, is_low: bool):
        self.voltage = voltage
        self.percentage = percentage
        self.is_low = is_low

    def __repr__(self):
        return (f"BatteryReading(voltage={self.voltage}, percentage={self.percentage}, is_low={self.is_low})")

class BatteryMonitor:
    def __init__(self, pin: int = DEFAULT_ADC_PIN):
        self._pin_num = pin
        self._adc = None
        self._smoothed_pct = None
        self._init_adc()

    #outside functions:
    def read(self) -> BatteryReading:
        if self._adc is None:
            return BatteryReading(voltage=0.0, percentage=0, is_low=False)

        samples = []
        for _ in range(SAMPLE_COUNT):
            samples.append(self._adc.read())
            time.sleep_ms(2)

        samples.sort()
        raw_median = samples[len(samples) // 2]

        v_adc = (raw_median / ADC_MAX_RAW) * ADC_REF_VOLTAGE
        v_batt = v_adc * DIVIDER_RATIO
        raw_pct = self._voltage_to_percentage(v_batt)

        if self._smoothed_pct is None:
            self._smoothed_pct = raw_pct
        elif abs(raw_pct - self._smoothed_pct) > MAX_JUMP_PCT:
            pass
        else:
            self._smoothed_pct = (EMA_ALPHA * raw_pct) + ((1- EMA_ALPHA) * self._smoothed_pct)

        percentage = int(self._smoothed_pct)
        return BatteryReading(voltage=round(v_batt, 2), percentage=percentage, is_low=(percent < 20))

    
            
    #internal helpers:
    def _init_adc(self):
        try:
            from machine import ADC, Pin
            pin = Pin(self._pin_num)
            self._adc = ADC(pin)

            self._adc.atten(ADC.ATTN_11DB)
            self._adc.width(ADC.WIDTH_12BIT)
        except (ImportError, AttributeError):
            self._adc = None

    @staticmethod
    def _voltage_to_percentage(voltage: float) -> int:
        curve = _VOLTAGE_CURVE
        if voltage >= curve [0][0]:
            return curve [0][1]
        if voltage <= curve [-1][0]:
            return curve [-1][1]

        for i in range(len(curve) - 1):
            v_high, p_high = curve[i]
            v_low, p_low = curve[i + 1]
            if v_low <= voltage <= v_high:
                span = v_high - v_low
                frac = (voltage - v_low) / span if span else 0
                return int(p_low + frac * (p_high - p_low))
        return 0  # Fallback, should not reach here
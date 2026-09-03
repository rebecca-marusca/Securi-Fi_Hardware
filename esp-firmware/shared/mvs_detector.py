# layer 3 + 4, partea de motion detection math, stripped down din especture
# core 0 - partea de mq2, esp now, mqtt, watchdog
# core 1 - partea de csi traffic generator & mvs detection

# 52 data + 4 pilot = 56 total, but ESPectre uses 52 data subcarriers
NUM_SUBCARRIERS = 32
 
WINDOW_SIZE = 30 # TODO

GAIN_LOCK_PACKETS = 100 # TODO
 
THRESHOLD_MULTIPLIER = 1.0 # TODO
 
MOTION_TRIGGER_PCT = 100 # TODO
  
 
class MVSDetector:
    def __init__(self):
        self._window: list = []

        # calibration baseline variance sum, set after the gain lock is completed
        self._baseline: float = 0.0
        # detection threshold = baseline * THRESHOLD_MULTIPLIER
        self._threshold: float = 0.0

        # packet count during gain lock
        self._gain_lock_accumulator: float = 0.0
        self._gain_lock_count: int = 0

        self._calibrated: bool = False

        self._movement: float = 0.0
        self._state: str = "IDLE"

        self._lock = self._make_lock()


# Outside functions:
    @property # cu proprety poti face gen MVSDetector.function in loc de MVSDetector.function(), de ce ne trebuie asta? idk, era in cod, ramane acolo
    def is_calibrated(self) -> bool:
        return self._calibrated

    @property
    def threshold(self) -> float:
        return self._threshold

    def feed(self, csi_amplitudes: list) -> None:
        """
        Ingest one CSI packet.
 
        Args:
            csi_amplitudes: List of floats, one per subcarrier.
                            Length must be NUM_SUBCARRIERS (52).
                            Values are linear amplitudes, not dB.
                            The CSI capture layer is responsible for
                            converting raw I/Q pairs to amplitudes before
                            calling feed().
 
        This method is designed to be called from the CSI interrupt callback.
        It does minimal work: update window, compute variance sum, update
        shared state under lock. No allocation after __init__ in the hot path
        (window slots are reused once the window is full).
        """
        if len(csi_amplitudes) != NUM_SUBCARRIERS:
            return

        if len(self._window) >= WINDOW_SIZE:
            self._window.pop(0)

        self._window.append(csi_amplitudes)

        if len(self._window) < WINDOW_SIZE:
            return

        variance_sum = self._compute_variance_sum()

        if not self._calibrated:
            self._gain_lock_accumulator += variance_sum
            self._gain_lock_count += 1

            if self._gain_lock_count >= GAIN_LOCK_PACKETS:
                self._finish_gain_lock()
            return

        if self._threshold > 0:
            movement_pct = int((variance_sum / self._threshold) * 100)
        else:
            movement_pct = 0

        if movement_pct >= MOTION_TRIGGER_PCT:
            state = "MOTION"
        else:
            state = "IDLE"

        with self._lock:
            self._movement = variance_sum
            self._state = state

    def get_reading(self) -> tuple:
        if not self._calibrated:
            return (0, "IDLE")

        with self._lock:
            movement = self._movement
            state = self._state

        if self._threshold > 0:
            movement_pct = int((movement / self._threshold) * 100)
        else:
            movement_pct = 0
        movement_pct = min(movement_pct, 200)

        return (movement_pct, state)

    def reset(self) -> None:
        with self._lock:
            self._window = []

            self._baseline = 0.0
            self._threshold = 0.0

            self._gain_lock_accumulator = 0.0
            self._gain_lock_count = 0

            self._calibrated = False

            self._movement = 0.0
            self._state = "IDLE"


# internal helpers: 
    def _compute_variance_sum(self) -> float:
        """
        Compute the sum of per-subcarrier variances across the current window.
        This is the core MVS operation. Called once per incoming packet
        once the window is full.
 
        Returns:
            Float scalar representing total signal movement energy.
        """

        total_variance = 0.0
        n = len(self._window)

        for sc in range(NUM_SUBCARRIERS):
            values = [self._window[frame][sc] for frame in range(n)]

            mean = sum(values) / n
            variance = sum((v - mean) ** 2 for v in values) / n
            total_variance += variance

        return total_variance

    def _finish_gain_lock(self) -> None:
        """
        Complete gain lock calibration.
 
        Computes the mean variance sum over the GAIN_LOCK_PACKETS collected,
        then sets threshold = baseline * THRESHOLD_MULTIPLIER.
 
        After this call, is_calibrated becomes True and feed() switches
        from accumulation mode to detection mode.
        """

        self._baseline = self._gain_lock_accumulator / self._gain_lock_count
        self._threshold = self._baseline * THRESHOLD_MULTIPLIER
        self._calibrated = True

        self._gain_lock_accumulator = 0.0
        self._gain_lock_count = 0

    @staticmethod # nu are nevoie de self sau cls
    def _make_lock():
        """
        Return a MicroPython thread lock if available, else a no-op shim.
        This lets the file be imported and unit-tested outside MicroPython
        without crashing on the missing _thread module.
        """

        try:
            import _thread
            return _thread.allocate_lock()
        except ImportError:
            # Not running on MicroPython — return a context manager no-op.
            class _NoOpLock:
                def __enter__(self):
                    return self
                def __exit__(self, *_):
                    pass
                def acquire(self):
                    pass
                def release(self):
                    pass
            return _NoOpLock()  
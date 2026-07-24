# layer 4, partea de motion detection math, stripped down din especture
# core 0 - partea de mq2, esp now, mqtt, watchdog
# core 1 - partea de csi traffic generator & mvs detection

# ---------------------------------------------------------------------------
# Constants — tuned for ESP32-C6 + indoor single-room detection
# ---------------------------------------------------------------------------
 
# Number of CSI subcarriers the C6 exposes on 2.4 GHz HT20.
# 52 data + 4 pilot = 56 total, but ESPectre uses 52 data subcarriers.
NUM_SUBCARRIERS = 52
 
# Sliding window size for variance computation.
# Larger = smoother but slower to react. 30 is ESPectre default.
WINDOW_SIZE = 30
 
# How many packets to collect during gain lock calibration.
# Original ESPectre uses 300 — at 20pps that is 15 seconds of blocking startup.
# 100 packets (5 seconds) is sufficient for a stable indoor baseline.
GAIN_LOCK_PACKETS = 100
 
# Multiplier applied to the calibrated baseline variance to set the
# detection threshold. Higher = less sensitive, fewer false positives.
# 1.8 matches ESPectre default sensitivity for a living-room sized space.
THRESHOLD_MULTIPLIER = 1.8
 
# Movement percentage at which state flips from IDLE to MOTION.
# 100% means movement == threshold exactly. Kept at 100 intentionally —
# the threshold_multiplier above is where you tune sensitivity, not here.
MOTION_TRIGGER_PCT = 100



class MVSDetector:
    """
    Moving Variance Segmentation detector
 
    Lifecycle:
        detector = MVSDetector()
        detector.feed(csi_amplitudes)   # call once per received CSI packet
        ...repeat during gain lock (detector.is_calibrated stays False)...
        ...once calibrated, feed() continues and reading becomes valid...
        reading = detector.get_reading()  # returns (movement_pct, state)
 
    Thread safety:
        feed() is called from the CSI capture callback on Core 1.
        get_reading() is called from the asyncio loop on Core 0.
        A simple lock is used around the shared state (_movement, _state).
        MicroPython's _thread.allocate_lock() is used — import handled
        by the caller environment. To keep this file importable in tests
        outside MicroPython, the lock degrades gracefully to a no-op.
    """

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
        """
        Return the latest detection result.
 
        Returns:
            (movement_pct: int, state: str)
            movement_pct is (movement / threshold) * 100.
                0–99   → IDLE
                100+   → MOTION (capped display at 200 by convention)
            state is "MOTION" or "IDLE".
 
        Returns (0, "IDLE") if not yet calibrated.
        Safe to call from any thread.
        """

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
        """
        Full reset — clears calibration and window. Use when rebooting
        or when the environment has changed significantly (e.g. furniture moved).
        Node will go through gain lock again on next packet feed.
        """
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
 
        For each of the NUM_SUBCARRIERS subcarriers:
            1. Collect the amplitude value from each window frame.
            2. Compute mean across frames.
            3. Compute variance = mean of squared deviations from mean.
        Sum all subcarrier variances into one scalar.
 
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
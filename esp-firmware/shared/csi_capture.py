import math
import struct
import network

_SUBCARRIER_COUNT = 52
_BYTES_PER_SAMPLE = 4  # 2 bytes I + 2 bytes Q, signed int16

class CSICapture:
    """
    Polls the ESP32 WiFi driver for CSI data via wlan.csi_read()
    and feeds MVSDetector.

    API on this firmware build is polling-based, not callback-based:
        wlan.csi_available() -> bool
        wlan.csi_read()      -> (mac_bytes, data_bytes) or None

    This runs on Core 1 alongside TrafficGenerator in a tight poll loop.
    SecuriFiNode starts this via _thread.start_new_thread(capture.run, ())
    instead of capture.start() registering a callback.

    Usage:
        capture = CSICapture(detector, router_mac="AA:BB:CC:DD:EE:FF")
        capture.start()   # initializes wlan CSI, sets active=True
        _thread.start_new_thread(capture.run, ())  # starts poll loop
        ...
        capture.stop()
    """

    def __init__(self, detector, router_mac: str = None):
        self._detector = detector
        self._router_mac_bytes = self._parse_mac(router_mac) if router_mac else None
        self._active = False
        self._running = False

        self._wlan = None

        self._packets_captured = 0
        self._packets_filtered = 0
        self._packets_malformed = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def packets_captured(self) -> int:
        return self._packets_captured

    @property
    def packets_filtered(self) -> int:
        return self._packets_filtered

    @property
    def packets_malformed(self) -> int:
        return self._packets_malformed

    @property
    def is_active(self) -> bool:
        return self._active

    def start(self) -> None:
        """
        Enable CSI on the WLAN interface.
        Must be called after WiFi is connected.
        Does NOT start the poll loop — call run() in a thread after this.
        """
        if self._active:
            return

        try:
            self._wlan = network.WLAN(network.STA_IF)
            self._wlan.csi_enable()
            self._active = True
            self._running = True
            print("[CSICapture] CSI enabled on WLAN interface")
        except Exception as e:
            print(f"[CSICapture] Failed to enable CSI: {e}")
            self._active = False

    def stop(self) -> None:
        """Disable CSI and stop the poll loop."""
        self._running = False
        if self._wlan and self._active:
            try:
                self._wlan.csi_disable()
            except Exception:
                pass
        self._active = False

    def run(self) -> None:
        """
        Poll loop — runs on Core 1 via _thread.start_new_thread().

        Polls wlan.csi_available() in a tight loop. When data is ready,
        reads it with wlan.csi_read(), filters by router MAC if set,
        parses amplitudes, and feeds the detector.

        No sleep between polls — we want maximum CSI throughput.
        The TrafficGenerator on Core 1 runs in its own thread;
        this runs in a separate thread also on Core 1 (MicroPython
        schedules them cooperatively).
        """
        if not self._active or self._wlan is None:
            print("[CSICapture] run() called but CSI not active, exiting")
            return

        while self._running:
            try:
                if not self._wlan.csi_available():
                    continue

                result = self._wlan.csi_read()
                if result is None:
                    continue

                mac, data = result

                # MAC filter
                if self._router_mac_bytes and mac != self._router_mac_bytes:
                    self._packets_filtered += 1
                    continue

                amplitudes = self._parse_amplitudes(data)
                if amplitudes is None:
                    self._packets_malformed += 1
                    continue

                self._detector.feed(amplitudes)
                self._packets_captured += 1

            except Exception:
                # Never crash the poll loop — log nothing to avoid
                # print() overhead in the hot path
                pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_amplitudes(self, data: bytes):
        """
        Convert raw CSI buffer to amplitude list.

        The C6 in HT20 mode gives 52 data subcarriers.
        Each subcarrier is one I/Q pair: 2x signed int16 little-endian.

        The firmware may return variable-length buffers depending on
        bandwidth and packet type. We accept anything >= 52*4=208 bytes
        and read the first 52 subcarriers. Shorter buffers are dropped.

        Returns list of 52 floats or None on error.
        """
        try:
            needed = _SUBCARRIER_COUNT * _BYTES_PER_SAMPLE
            if len(data) < needed:
                return None

            amplitudes = []
            for i in range(_SUBCARRIER_COUNT):
                offset = i * _BYTES_PER_SAMPLE
                I, Q = struct.unpack_from("<hh", data, offset)
                amplitudes.append(math.sqrt(I * I + Q * Q))
            return amplitudes
        except Exception:
            return None

    @staticmethod
    def _parse_mac(mac_str: str) -> bytes:
        parts = mac_str.strip().split(":")
        if len(parts) != 6:
            raise ValueError(f"Invalid MAC: {mac_str}")
        return bytes(int(p, 16) for p in parts)
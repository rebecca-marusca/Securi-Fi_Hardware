# cand e eroare la import-uri, ignorati-le ca apar pt ca sunteti in python env si nu micro python


"""
Gracias Claude pt rezumat

csi_capture.py — SecuriFi shared layer
Hooks into the ESP32 802.11 CSI callback and converts raw I/Q data
into amplitude arrays for the MVS detector.
 
How CSI works on ESP32-C6:
    The ESP32 WiFi driver exposes a CSI callback that fires for every
    received 802.11 packet. The callback delivers a raw buffer of complex
    I/Q samples — one pair per subcarrier. ESPectre and this module
    register that callback, extract amplitude (sqrt(I²+Q²)) per subcarrier,
    and pass the result to MVSDetector.feed().
 
    On MicroPython, the CSI callback is registered via esp.wifi_csi_enable()
    and esp.wifi_csi_set_callback(). This is an Espressif MicroPython
    extension — not available in standard CPython. The _NoOpCSI shim below
    allows offline testing.
 
Filter: only packets from the router (our ping replies) are processed.
    Passing every overheard 802.11 packet to MVS would pollute the signal
    with neighbor traffic. We filter by source MAC = router MAC, which is
    known at boot from the DHCP lease (network.WLAN().ifconfig() doesn't
    give it directly — we resolve it from the ARP table or config).
 
Threading:
    The CSI callback fires on the WiFi driver's internal task — a third
    context beyond Core 0 (asyncio) and Core 1 (traffic generator).
    To keep the callback fast and non-blocking, it pushes amplitude arrays
    into a Queue. The MVSDetector.feed() call happens in the consumer,
    which runs on Core 1 alongside the traffic generator (they share Core 1
    in a cooperative way since feeding MVS is fast).
"""
 
import math
import struct

# Size of the raw CSI buffer from ESP32-C6 in HT20 mode.
# 52 data subcarriers * 2 (I + Q) * 2 bytes each = 208 bytes.
_RAW_BUFFER_SIZE = 208
_SUBCARRIER_COUNT = 52
_BYTES_PER_SAMPLE = 4 # 2 I + 2 Q

class CSICapture:
    """
    Registers the ESP32 WiFi CSI callback and feeds MVSDetector.
 
    Usage:
        detector = MVSDetector()
        capture = CSICapture(detector, router_mac="AA:BB:CC:DD:EE:FF")
        capture.start()
        # ... traffic generator running on Core 1 ...
        # CSI packets now flow automatically into detector.feed()
        capture.stop()
    """

    def __init__(self, detector, router_mac: str = None):
        self._detector = detector
        if router_mac:
            self._router_mac_bytes = self._parse_mac(router_mac)
        else:
            self._router_mac_bytes = None
        self._active = False

        self._packets_captured = 0
        self._packets_filtered = 0 # MAC mismatch
        self._packets_malformed = 0 # bad buffer / parse error


    # Outside functions:
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
        Enable CSI capture and register the callback with the WiFi driver.
 
        Must be called after the node is connected to WiFi.
        Calling before WiFi connect will raise an OSError from esp module.
        """

        if self._active:
            return

        try:
            import esp 
            esp.wifi_csi_enable(True)
            esp.wifi_csi_set_callback(self._csi_callback)
            
            self._active = True
        except ImportError:
            self._active = True

    def stop(self) -> None:
        if not self._active:
            return

        try:
            import esp 
            esp.wifi_csi_enable(False)
            esp.wifi_csi_set_callback(None)
        except (ImportError, OSError):
            pass
        finally: 
            self._active = False


    # callback:
    def _csi_callback(self, mac: bytes, data: bytes) -> None:
        """
        Called by the ESP32 WiFi driver for every received CSI frame.
 
        Args:
            mac:  6-byte source MAC address of the frame sender.
            data: Raw CSI buffer. Expected length = _RAW_BUFFER_SIZE (208B).
                  Layout: pairs of int16 (I, Q) for each subcarrier,
                  little-endian, 52 pairs = 104 int16s = 208 bytes.
        """

        if self._router_mac_bytes and mac != self._router_mac_bytes:
            self._packets_filtered += 1
            return

        if len(data) < _RAW_BUFFER_SIZE:
            self._packets_malformed += 1
            return

        amplitudes = self._parse_amplitudes(data)
        if amplitudes is None:
            self._packets_malformed += 1
            return

        self._detector.feed(amplitudes)
        self._packets_captured += 1


    # internal helpers: 
    def _parse_amplitudes(self, data: bytes):
        """
        Convert raw CSI buffer to a list of linear amplitudes.
 
        For each subcarrier: amplitude = sqrt(I² + Q²)
        I and Q are signed 16-bit integers, little-endian.
 
        Returns list of _SUBCARRIER_COUNT floats, or None on parse error.
        """

        try:
            amplitudes = []
            for i in range(_SUBCARRIER_COUNT):
                offset = i * _BYTES_PER_SAMPLE
                I, Q = struct.unpack_from("<hh", data, offset)
                amplitude = math.sqrt(I*I + Q*Q)
                amplitudes.append(amplitude)

            return amplitudes
        except Exception:
            return None

    @staticmethod
    def _parse_mac(mac_str: str) -> bytes: 
        """
        Convert "AA:BB:CC:DD:EE:FF" string to 6-byte bytes object.
        Raises ValueError if the format is wrong.
        """

        parts = mac_str.strip().split(":")
        if len(parts) != 6:
            raise ValueError(f"Invalid MAC adress: {mac_str}")
        
        return bytes(int(p, 16) for p in parts)
        
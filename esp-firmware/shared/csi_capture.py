import math
import struct
import network

# csi_read() on this firmware returns a 24-element list:
#   [0]  RSSI 
#   [1]  noise floor 
#   [2]  source MAC 
#   [3]  timestamp_1 
#   [4]  timestamp_2 
#   [5]  CSI data (bytearray, 128 bytes = 32 subcarriers * 4 bytes each)
#   [6..23] channel/antenna metadata 

_CSI_DATA_INDEX = 5
_MAC_INDEX = 2
_SUBCARRIER_COUNT = 32  
_BYTES_PER_SAMPLE = 4  


class CSICapture:
    def __init__(self, detector, router_mac: str = None):
        self._detector = detector
        self._router_mac_bytes = self._parse_mac(router_mac) if router_mac else None
        self._active = False
        self._running = False
        self._wlan = None

        self._packets_captured = 0
        self._packets_filtered = 0
        self._packets_malformed = 0

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
        Does NOT start the poll loop
        """
        if self._active:
            return
        try:
            self._wlan = network.WLAN(network.STA_IF)
            self._wlan.csi_enable()
            self._active = True
            self._running = True
            print("[CSICapture] CSI enabled")
        except Exception as e:
            print(f"[CSICapture] Failed to enable CSI: {e}")
            self._active = False

    def stop(self) -> None:
        self._running = False
        if self._wlan and self._active:
            try:
                self._wlan.csi_disable()
            except Exception:
                pass
        self._active = False

    def run(self) -> None:
        """
        Poll loop: runs on Core 1 via _thread.start_new_thread()
        Polls csi_available(), reads with csi_read(), filters by
        router MAC if set, parses amplitudes, feeds detector
        """
        if not self._active or self._wlan is None:
            print("[CSICapture] run() called but CSI not active")
            return

        while self._running:
            try:
                if not self._wlan.csi_available():
                    continue

                result = self._wlan.csi_read()
                if result is None or len(result) < 6:
                    continue

                mac = result[_MAC_INDEX]
                data = result[_CSI_DATA_INDEX]

                # MAC filter
                if self._router_mac_bytes and mac != self._router_mac_bytes:
                    self._packets_filtered += 1
                    continue

                if not isinstance(data, (bytes, bytearray)):
                    self._packets_malformed += 1
                    continue

                amplitudes = self._parse_amplitudes(data)
                if amplitudes is None:
                    self._packets_malformed += 1
                    continue

                self._detector.feed(amplitudes)
                self._packets_captured += 1

            except Exception:
                pass

    def _parse_amplitudes(self, data):
        """
        Convert CSI bytearray to amplitude list
        128 bytes = 32 subcarriers * 4 bytes
        Returns list of 32 floats or None on error
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
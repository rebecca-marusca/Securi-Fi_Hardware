# layer 1, ping sender, comunicarea cu router-ul
# totul pe core 1

"""
Sends periodic ICMP pings to the router to provoke CSI packet replies.
 
Why this exists:
    WiFi CSI is only readable when packets are being transmitted/received.
    In an idle home network there may be no natural traffic, so SecuriFi
    nodes actively generate their own traffic by pinging the router.
    Each ping reply from the router carries fresh CSI that the capture
    layer reads via the 802.11 callback.
 
Design:
    TrafficGenerator runs as a plain synchronous loop on Core 1 (_thread).
    It is deliberately NOT async — the tight timing of pings matters for
    consistent pps, and asyncio introduces jitter from other coroutines.
    The caller (securifi_node.py) spawns it via _thread.start_new_thread().
 
"""

import socket  # networking module
import struct
import time 

# Internet Control Message Protocol (ICMP) echo request vars:
_ICMP_ECHO_REQUEST = 8 # cod special pt ping
_ICMP_CODE = 0


class TrafficGenerator:
    """
    Sends ICMP echo requests (pings) to a target IP at a fixed rate.
 
    Usage:
        import _thread
        tg = TrafficGenerator(target_ip="192.168.1.1", rate_pps=20)
        _thread.start_new_thread(tg.run, ())
 
    The run() loop blocks indefinitely. To stop it, call stop() from
    another thread — the loop checks _running on each iteration.
    """

    def __init__(self, target_ip: str, rate_pps: int = 20):
        """
        Args:
            target_ip: Router IP to ping. Typically the default gateway.
                       The node reads this from config at boot via
                       network.WLAN().ifconfig()[2].
            rate_pps:  Packets per second.
        """

        self._target_ip = target_ip
        self._interval_ms = 1000 // rate_pps

        self._running = False
        self._sequence = 0
        self._identifier = 0x5346  # "SF" in ASCII — SecuriFi marker

        self._packets_sent = 0
        self._packets_dropped = 0


# Outside functions:
    @property
    def packets_sent(self) -> int:
        return self._packets_sent

    @property
    def packets_dropped(self) -> int:
        return self._packets_dropped

    @property
    def pps(self) -> int:
        return 1000 // self._interval_ms

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        """
        Main ping loop. Runs indefinitely on Core 1.
 
        Each iteration:
            1. Build an ICMP echo request packet.
            2. Send it via a raw socket to the router.
            3. Sleep for the remainder of the interval.
 
        Socket errors (network blip, router unreachable) are caught and
        counted as drops rather than crashing the thread. The loop
        continues regardless — losing a few pings is fine, the MVS
        window averages over WINDOW_SIZE frames anyway.
        """

        self._running = True
        sock = None

        try:
            sock = self._open_socket()

            while self._running:
                start_ms = time.ticks_ms()

                try:
                    packet = self._build_icmp_packet()
                    sock.sendto(packet, (self._target_ip, 1))
                    self._packets_sent += 1
                    self._sequence = (self._sequence + 1) & 0xFFFF # ca sa il itna in 16 bit valid range
                except OSError:
                    # Network error — socket may have gone stale.
                    # Try to reopen once; if that fails, count drop and continue.

                    self._packets_dropped += 1
                    try:
                        if sock:
                            sock.close()
                        sock = self._open_socket()
                    except OSError:
                        pass

                elapsed_ms = time.ticks_diff(time.ticks_ms(), start_ms)
                sleep_ms = self._interval_ms - elapsed_ms

                if sleep_ms > 0:
                    time.sleep_ms(sleep_ms)
        finally: 
            if sock:
                try:
                        sock.close()
                except OSError:
                    pass
            self._running = False


# internal helpers:
    def _open_socket(self) -> socket.socket:
        """
            Open a raw ICMP socket.
    
            SOCK_RAW with IPPROTO_ICMP requires no bind, we just sendto
            the target address. MicroPython's socket module supports this
            on ESP32 with the right network config.
        """

        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, 1) # 1 = IPPROTO_ICMP
        sock.setblocking(False)
        sock.settimeout(0.1)
        return sock

    def _build_icmp_packet(self) -> bytes:
        """
            Build a minimal ICMP echo request packet.
    
            Structure (8 bytes header + 16 bytes payload = 24 bytes total):
                Type (1B) | Code (1B) | Checksum (2B) | ID (2B) | Seq (2B) | Payload (16B)
    
            Payload is a fixed pattern — content does not matter for CSI generation,
            only the packet length and timing matter.
        """

        header = struct.pack(
            "!BBHHH",
            _ICMP_ECHO_REQUEST, # type 8
            _ICMP_CODE, # code 0
            0,                   # checksum placeholder
            self._identifier,    # identifier
            self._sequence,      # sequence number
        )    
        payload = b"SecuriFi-Ping!!!"

        checksum = self._checksum(header + payload)

        # Rebuild header with real checksum.
        header = struct.pack(
            "!BBHHH",
            _ICMP_ECHO_REQUEST,
            _ICMP_CODE,
            checksum,
            self._identifier,
            self._sequence,
        )

        return header + payload


    # Internet checksum algorithm RFC1071, cred ca suntem la fel de confuzi
    @staticmethod
    def _checksum(data: bytes) -> int:
        s = 0 
        n = len(data)

        for i in range(0, n - 1, 2):
            s += (data[i] << 8) + data[i + 1]
        if n % 2:
            s += (data[-1] << 8)

        while s >> 16:
            s = (s & 0xFFFF) + (s >> 16)

        return ~s & 0xFFFF
"""
core/traffic_generator.py - Synthetic & Real Traffic Injector for CN Lab Demos.
Allows generating real ICMP, UDP, and TCP packets to demonstrate live reactivity.
"""

import sys
import time
import socket
import threading
import subprocess
from typing import Optional


class TrafficGenerator:
    """
    Generates controlled network traffic for testing and live demonstrations.
    All generator routines run asynchronously in background threads.
    """

    def __init__(self):
        self._active_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.last_action_message = ""

    def is_running(self) -> bool:
        return self._active_thread is not None and self._active_thread.is_alive()

    def stop(self):
        self._stop_event.set()
        if self._active_thread and self._active_thread.is_alive():
            self._active_thread.join(timeout=1.0)
        self.last_action_message = "Traffic generation stopped."

    def trigger_icmp_ping(self, count: int = 5, target: str = "8.8.8.8"):
        """Fires system ICMP ping packets."""
        def run():
            self.last_action_message = f"Sending {count} ICMP echo requests to {target}..."
            try:
                if sys.platform == "win32":
                    cmd = ["ping", "-n", str(count), target]
                else:
                    cmd = ["ping", "-c", str(count), target]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.last_action_message = f"Completed {count} ICMP pings to {target}."
            except Exception as e:
                self.last_action_message = f"Ping failed: {e}"

        t = threading.Thread(target=run, daemon=True)
        t.start()
        self._active_thread = t

    def trigger_udp_burst(self, packets: int = 500, target_ip: str = "127.0.0.1", port: int = 49555):
        """Sends a burst of UDP datagrams to loopback or LAN socket."""
        def run():
            self.last_action_message = f"Sending burst of {packets} UDP datagrams..."
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                payload = b"X" * 1024  # 1 KB datagram
                for _ in range(packets):
                    if self._stop_event.is_set():
                        break
                    sock.sendto(payload, (target_ip, port))
                    time.sleep(0.002)
                sock.close()
                self.last_action_message = f"Completed {packets} UDP datagrams."
            except Exception as e:
                self.last_action_message = f"UDP burst error: {e}"

        self._stop_event.clear()
        t = threading.Thread(target=run, daemon=True)
        t.start()
        self._active_thread = t

    def trigger_tcp_download(self, duration_sec: int = 5):
        """Generates realistic TCP streaming traffic via standard HTTP streaming."""
        def run():
            self.last_action_message = f"Generating TCP streaming traffic ({duration_sec}s)..."
            try:
                import urllib.request
                test_url = "https://speed.cloudflare.com/__down?bytes=15000000"
                start = time.time()
                req = urllib.request.Request(test_url, headers={"User-Agent": "CN-Bandwidth-Monitor/1.0"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    while time.time() - start < duration_sec and not self._stop_event.is_set():
                        chunk = response.read(65536)
                        if not chunk:
                            break
                self.last_action_message = "TCP download test completed."
            except Exception:
                # Fallback: local TCP loopback streaming
                self._run_local_tcp_stream(duration_sec)

        self._stop_event.clear()
        t = threading.Thread(target=run, daemon=True)
        t.start()
        self._active_thread = t

    def _run_local_tcp_stream(self, duration_sec: int):
        """Fallback local high-speed TCP socket streaming."""
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)
            port = srv.getsockname()[1]

            def srv_worker():
                conn, _ = srv.accept()
                buf = b"T" * 65536
                start = time.time()
                while time.time() - start < duration_sec and not self._stop_event.is_set():
                    try:
                        conn.sendall(buf)
                    except Exception:
                        break
                conn.close()
                srv.close()

            th = threading.Thread(target=srv_worker, daemon=True)
            th.start()

            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(("127.0.0.1", port))
            start = time.time()
            while time.time() - start < duration_sec and not self._stop_event.is_set():
                data = client.recv(65536)
                if not data:
                    break
            client.close()
            self.last_action_message = "Local TCP test completed."
        except Exception as e:
            self.last_action_message = f"TCP test finished: {e}"

    def trigger_speed_benchmark(self, duration_sec: int = 6):
        """
        Runs a high-throughput multi-stream download benchmark
        designed to saturate up to 100+ Mbps bandwidth.
        """
        def run():
            self.last_action_message = f"Running 100+ Mbps Speed Benchmark ({duration_sec}s)..."
            import urllib.request
            stop_benchmark = threading.Event()

            def stream_worker(url):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=10) as r:
                        while not stop_benchmark.is_set() and not self._stop_event.is_set():
                            chunk = r.read(256 * 1024)
                            if not chunk:
                                break
                except Exception:
                    pass

            urls = [
                "https://speed.cloudflare.com/__down?bytes=50000000",
                "https://speed.cloudflare.com/__down?bytes=50000000",
                "https://speed.cloudflare.com/__down?bytes=50000000",
                "https://speed.cloudflare.com/__down?bytes=50000000",
            ]
            threads = [threading.Thread(target=stream_worker, args=(u,), daemon=True) for u in urls]
            for t in threads:
                t.start()

            start_t = time.time()
            while time.time() - start_t < duration_sec and not self._stop_event.is_set():
                time.sleep(0.2)

            stop_benchmark.set()
            self.last_action_message = "100+ Mbps Speed Benchmark completed."

        self._stop_event.clear()
        t = threading.Thread(target=run, daemon=True)
        t.start()
        self._active_thread = t


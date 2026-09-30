"""
monitor.py - Network Bandwidth & Protocol Monitor (CLI Application)
Computer Networks Lab Project

Usage:
    python monitor.py               # Starts monitor in enhanced terminal view
    python monitor.py --compact     # Starts in strict assignment format
    python monitor.py --demo        # Starts in demo mode with sample values
    python monitor.py --web         # Launches modern browser Web GUI dashboard
    python monitor.py --interface "Wi-Fi"
"""

import sys
import os
import time
import argparse
import threading
from typing import Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.collector import NetworkTrafficCollector, NetworkSnapshot
from core.utils import (
    TerminalColors,
    render_compact_display,
    render_enhanced_display,
    format_bytes,
)
from core.traffic_generator import TrafficGenerator

# Check for non-blocking keyboard input on Windows / Unix
_HAS_MSVCRT = False
if sys.platform == "win32":
    try:
        import msvcrt
        _HAS_MSVCRT = True
    except ImportError:
        pass


class NetworkMonitorCLI:
    """Console application for real-time network monitoring."""

    def __init__(
        self,
        interface: Optional[str] = None,
        interval: float = 1.0,
        compact_mode: bool = False,
        demo_mode: bool = False,
        auto_test_traffic: bool = False,
    ):
        self.interval = max(0.2, interval)
        self.compact_mode = compact_mode
        self.demo_mode = demo_mode
        self.collector = NetworkTrafficCollector(
            interface=interface,
            max_bar_length=18,
            demo_mode=demo_mode,
        )
        self.traffic_gen = TrafficGenerator()
        self.auto_test = auto_test_traffic

        self.running = False
        self.paused = False
        self.last_status_msg = ""
        self.status_msg_expires = 0.0

        # Session tracking
        self.session_start = time.time()
        self.initial_snapshot: Optional[NetworkSnapshot] = None
        self.latest_snapshot: Optional[NetworkSnapshot] = None

    def start(self):
        """Main loop that samples metrics and updates terminal."""
        self.running = True

        # Initial baseline sample
        self.initial_snapshot = self.collector.get_snapshot()
        time.sleep(0.5)

        if self.auto_test:
            self.traffic_gen.trigger_udp_burst(300)

        # Clear terminal screen initially
        os.system("cls" if os.name == "nt" else "clear")

        try:
            while self.running:
                loop_start = time.time()

                # Process keyboard input if available
                self._handle_input()

                if not self.paused:
                    snapshot = self.collector.get_snapshot()
                    self.latest_snapshot = snapshot
                    self._render_screen(snapshot)

                # Maintain exact sampling frequency
                elapsed = time.time() - loop_start
                sleep_time = max(0.05, self.interval - elapsed)
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
            self._render_exit_summary()

    def stop(self):
        self.running = False
        self.traffic_gen.stop()

    def set_status(self, msg: str, duration: float = 3.0):
        self.last_status_msg = msg
        self.status_msg_expires = time.time() + duration

    def _handle_input(self):
        """Reads non-blocking keystrokes on Windows."""
        if not _HAS_MSVCRT:
            return

        while msvcrt.kbhit():
            ch = msvcrt.getch()
            # Handle special or arrow keys
            if ch in [b"\x00", b"\xe0"]:
                msvcrt.getch()
                continue
            key = ch.decode("utf-8", errors="ignore").lower()

            if key == "q":
                self.running = False
            elif key == "m":
                self.compact_mode = not self.compact_mode
                os.system("cls" if os.name == "nt" else "clear")
                self.set_status(f"Switched to {'Compact' if self.compact_mode else 'Enhanced'} mode")
            elif key == "d":
                self.demo_mode = not self.demo_mode
                self.collector.demo_mode = self.demo_mode
                os.system("cls" if os.name == "nt" else "clear")
                self.set_status(f"Demo mode {'ENABLED' if self.demo_mode else 'DISABLED'}")
            elif key == "b":
                self.traffic_gen.trigger_speed_benchmark(duration_sec=6)
                self.set_status("Running 100+ Mbps Speed Benchmark (6s)...")
            elif key == "r":
                self.collector.reset_peaks()
                self.set_status("Reset peak speed counters to 0.0 Mbps.")
            elif key == "t":
                self.traffic_gen.trigger_icmp_ping(count=4)
                self.traffic_gen.trigger_udp_burst(packets=250)
                self.set_status("Injected test ICMP and UDP traffic!")
            elif key == "h":
                self.set_status("[Q] Quit | [M] Mode | [B] 100M Test | [R] Reset Peak | [T] Traffic | [D] Demo | [P] Pause")

    def _render_screen(self, snapshot: NetworkSnapshot):
        """Renders either compact or enhanced view with cursor home."""
        # Use ANSI home sequence to prevent flickering
        sys.stdout.write(TerminalColors.CURSOR_HOME)

        if self.compact_mode:
            content = render_compact_display(snapshot)
            # Add small status indicator if active
            if time.time() < self.status_msg_expires:
                content += f"\n\n\033[33m>> {self.last_status_msg}\033[0m"
            else:
                content += "\n\n\033[90m(Press 'M' for full dashboard, 'Q' to quit)\033[0m"
        else:
            content = render_enhanced_display(snapshot)
            if time.time() < self.status_msg_expires:
                content += f"\n\033[33m>> {self.last_status_msg}\033[0m"
            elif self.traffic_gen.last_action_message:
                content += f"\n\033[90mTraffic Gen: {self.traffic_gen.last_action_message}\033[0m"

        sys.stdout.write(content + "\n")
        sys.stdout.flush()

    def _render_exit_summary(self):
        """Prints a clean session summary on exit."""
        C = TerminalColors
        duration = int(time.time() - self.session_start)
        minutes, seconds = divmod(duration, 60)

        print("\n" + C.DIM + "═" * 59 + C.RESET)
        print(f" {C.BOLD}SESSION SUMMARY{C.RESET} (Duration: {minutes}m {seconds}s)")
        if self.latest_snapshot and self.initial_snapshot:
            rx_delta = max(0, self.latest_snapshot.total_bytes_recv - self.initial_snapshot.total_bytes_recv)
            tx_delta = max(0, self.latest_snapshot.total_bytes_sent - self.initial_snapshot.total_bytes_sent)
            print(f"  • Total Downloaded: {C.GREEN}{format_bytes(rx_delta)}{C.RESET}")
            print(f"  • Total Uploaded:   {C.CYAN}{format_bytes(tx_delta)}{C.RESET}")
        print(f"  • Mode:             {'Demo Mode' if self.demo_mode else 'Live Physical Network'}")
        print(f"  • Interface:        {self.collector.interface or 'Default / All'}")
        print(C.DIM + "═" * 59 + C.RESET)
        print(" Monitor closed successfully.\n")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Network Bandwidth & Protocol Monitor - CN Lab Project",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-c", "--compact",
        action="store_true",
        help="Display in exact compact problem statement format",
    )
    parser.add_argument(
        "-d", "--demo",
        action="store_true",
        help="Run in demo mode with sample values (42.5 Mbps, 1240 pps, etc.)",
    )
    parser.add_argument(
        "-i", "--interface",
        type=str,
        default=None,
        help="Network interface name (e.g. 'Wi-Fi' or 'Ethernet'). Use --list-interfaces to inspect.",
    )
    parser.add_argument(
        "-t", "--interval",
        type=float,
        default=1.0,
        help="Update interval in seconds (default: 1.0)",
    )
    parser.add_argument(
        "-w", "--web",
        action="store_true",
        help="Launch the modern Web Dashboard GUI (FastAPI + WebSocket)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for the Web GUI server (default: 8000)",
    )
    parser.add_argument(
        "--list-interfaces",
        action="store_true",
        help="List available network interfaces and exit",
    )
    parser.add_argument(
        "--test-traffic",
        action="store_true",
        help="Automatically trigger background test packets on launch",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.list_interfaces:
        interfaces = NetworkTrafficCollector.get_available_interfaces()
        print("Available Network Interfaces:")
        for idx, iface in enumerate(interfaces, 1):
            print(f"  [{idx}] {iface}")
        sys.exit(0)

    if args.web:
        print(f"\033[1;36mStarting Network Monitor Web Dashboard on http://localhost:{args.port}...\033[0m")
        from web.server import start_web_server
        start_web_server(port=args.port, demo_mode=args.demo, interface=args.interface)
        return

    # CLI Terminal Mode
    app = NetworkMonitorCLI(
        interface=args.interface,
        interval=args.interval,
        compact_mode=args.compact,
        demo_mode=args.demo,
        auto_test_traffic=args.test_traffic,
    )
    app.start()


if __name__ == "__main__":
    main()

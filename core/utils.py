"""
core/utils.py - Terminal formatting, ANSI colors, and bar rendering.
"""

import sys
import os

# Initialize UTF-8 and ANSI terminal on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        os.system("")  # Enables VT100 ANSI sequences on Windows 10/11
    except Exception:
        pass


class TerminalColors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright foreground
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Cursor controls
    CLEAR_SCREEN = "\033[2J"
    CURSOR_HOME = "\033[H"
    CLEAR_LINE = "\033[K"


def format_bytes(num_bytes: int) -> str:
    """Formats raw bytes into human readable KB, MB, GB."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def format_speed(mbps: float) -> str:
    """Formats speed string with Mbps suffix."""
    return f"{mbps:.1f} Mbps"


def render_bar(count: int, char: str = "█", color: str = "") -> str:
    """Renders a block bar string with optional color."""
    if count <= 0:
        return ""
    bar = char * count
    if color:
        return f"{color}{bar}{TerminalColors.RESET}"
    return bar


def render_compact_display(snapshot) -> str:
    """
    Renders the exact format specified in the problem statement:

    Network Monitor

    Download:  42.5 Mbps
    Upload:    8.2 Mbps

    Packets/sec:  1240

    TCP:  ████████████
    UDP:  ████
    ICMP: ██
    """
    tcp_blocks = "█" * snapshot.tcp_bars
    udp_blocks = "█" * snapshot.udp_bars
    icmp_blocks = "█" * snapshot.icmp_bars

    lines = [
        "Network Monitor",
        "",
        f"Download:  {snapshot.download_mbps:.1f} Mbps",
        f"Upload:    {snapshot.upload_mbps:.1f} Mbps",
        "",
        f"Packets/sec:  {snapshot.packets_per_sec}",
        "",
        f"TCP:  {tcp_blocks}",
        f"UDP:  {udp_blocks}",
        f"ICMP: {icmp_blocks}",
    ]
    return "\n".join(lines)


def render_enhanced_display(snapshot, session_recv: int = 0, session_sent: int = 0) -> str:
    """
    Renders a colored, comprehensive terminal dashboard with headers,
    rate statistics, percentages, and session totals.
    """
    C = TerminalColors

    # Header
    mode_tag = f"{C.BRIGHT_MAGENTA}[DEMO MODE]{C.RESET}" if snapshot.is_demo else f"{C.BRIGHT_GREEN}[LIVE ACTIVE]{C.RESET}"
    header = (
        f"{C.BRIGHT_CYAN}{C.BOLD}"
        f"╔═══════════════════════════════════════════════════════════╗\n"
        f"║                  NETWORK BANDWIDTH MONITOR                ║\n"
        f"╚═══════════════════════════════════════════════════════════╝{C.RESET}\n"
        f" Interface: {C.BRIGHT_WHITE}{snapshot.active_interface}{C.RESET} | "
        f"IP: {C.YELLOW}{snapshot.local_ip}{C.RESET} | Status: {mode_tag}\n"
        f"{C.DIM}{'─' * 59}{C.RESET}"
    )

    # Bandwidth section
    down_bar_len = min(20, int(snapshot.download_mbps / 5.0))
    up_bar_len = min(20, int(snapshot.upload_mbps / 5.0))
    down_visual = render_bar(down_bar_len, "■", C.BRIGHT_GREEN) + ("·" * max(0, 20 - down_bar_len))
    up_visual = render_bar(up_bar_len, "■", C.BRIGHT_CYAN) + ("·" * max(0, 20 - up_bar_len))

    bandwidth = (
        f" {C.BOLD}Download:{C.RESET}  {C.BRIGHT_GREEN}{snapshot.download_mbps:5.1f} Mbps{C.RESET}  [{down_visual}]  {C.DIM}(Peak: {snapshot.peak_download_mbps:.1f} Mbps){C.RESET}\n"
        f" {C.BOLD}Upload:{C.RESET}    {C.BRIGHT_CYAN}{snapshot.upload_mbps:5.1f} Mbps{C.RESET}  [{up_visual}]  {C.DIM}(Peak: {snapshot.peak_upload_mbps:.1f} Mbps){C.RESET}\n"
        f"\n"
        f" {C.BOLD}Packets/sec:{C.RESET}  {C.BRIGHT_YELLOW}{snapshot.packets_per_sec:<6}{C.RESET} "
        f"{C.DIM}(Rx: {snapshot.packets_recv_per_sec}/s, Tx: {snapshot.packets_sent_per_sec}/s | Peak: {snapshot.peak_pps} pps){C.RESET}"
    )

    # Protocol Distribution section
    tcp_bar_str = render_bar(snapshot.tcp_bars, "█", C.BRIGHT_GREEN)
    udp_bar_str = render_bar(snapshot.udp_bars, "█", C.BRIGHT_CYAN)
    icmp_bar_str = render_bar(snapshot.icmp_bars, "█", C.BRIGHT_MAGENTA)

    protocols = (
        f"{C.DIM}{'─' * 59}{C.RESET}\n"
        f" {C.BOLD}Protocol Breakdown:{C.RESET}\n"
        f"  {C.BOLD}TCP:{C.RESET}   {tcp_bar_str:<22} {C.DIM}({snapshot.tcp_pct:4.1f}% | {snapshot.tcp_rate} pkts/s){C.RESET}\n"
        f"  {C.BOLD}UDP:{C.RESET}   {udp_bar_str:<22} {C.DIM}({snapshot.udp_pct:4.1f}% | {snapshot.udp_rate} pkts/s){C.RESET}\n"
        f"  {C.BOLD}ICMP:{C.RESET}  {icmp_bar_str:<22} {C.DIM}({snapshot.icmp_pct:4.1f}% | {snapshot.icmp_rate} pkts/s){C.RESET}"
    )

    # Session totals and controls
    session_info = (
        f"{C.DIM}{'─' * 59}{C.RESET}\n"
        f" Total Rx: {C.WHITE}{format_bytes(snapshot.total_bytes_recv)}{C.RESET} | "
        f"Total Tx: {C.WHITE}{format_bytes(snapshot.total_bytes_sent)}{C.RESET}\n"
        f"{C.DIM}[Q] Quit  [M] Mode  [B] 100M Test  [T] Traffic  [R] Reset Peak  [D] Demo{C.RESET}\n"
        f"{C.DIM}{'═' * 59}{C.RESET}"
    )

    return f"{header}\n{bandwidth}\n{protocols}\n{session_info}"

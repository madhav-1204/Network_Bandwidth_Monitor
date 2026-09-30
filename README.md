# Network Bandwidth Monitor 🌐

> **Computer Networks Lab Project #**  
> A high-performance real-time network traffic and protocol analyzer built with Python, OS Kernel Counters (Windows IP Helper API & Linux procfs), WebSocket streaming, and a modern glassmorphic dashboard.

---

## 📋 Problem Statement

```text
10. Network Bandwidth Monitor

Create an application that monitors network traffic.

Display:

Network Monitor

Download:  42.5 Mbps
Upload:    8.2 Mbps

Packets/sec:  1240

TCP:  ████████████
UDP:  ████
ICMP: ██
```

---

## ✨ Features

- **Exact Problem Statement Display**: Built-in `--compact` mode that formats the console screen precisely as requested.
- **Kernel-Level Precision**: Queries the OS network stack directly via Windows IP Helper API (`iphlpapi.dll`) and Linux `/proc/net/snmp` — **no external WinPcap/Npcap driver installation required**.
- **Real-Time Bandwidth**: Live Download and Upload throughput calculation in **Mbps** ($10^6$ bits/sec).
- **Packet Velocity**: Calculates total packets transferred per second ($\text{PPS}$).
- **Protocol Decomposition**: Deconstructs network traffic into **TCP**, **UDP**, and **ICMP** with dynamic Unicode block meters (`█`).
- **Interactive Keyboard Controls**:
  - `M` — Toggle between Compact view and Enhanced dashboard view
  - `D` — Toggle between Live OS hardware metrics and Demo mode
  - `T` — Inject live test traffic (ICMP ping & UDP burst)
  - `P` — Pause / Resume monitoring
  - `Q` — Gracefully quit with session statistics summary
- **Modern Web Dashboard**: Real-time browser UI (FastAPI + WebSockets + Canvas waveform charts + Sockets inspector).
- **Built-in Lab Traffic Injector**: Test real ping, UDP burst, or TCP download traffic on command during lab evaluation.

---

## 🚀 Quick Start

### 1. Requirements
Ensure Python 3.8+ is installed. Install the minimal dependencies:

```bash
pip install -r requirements.txt
```

### 2. Run in Terminal (CLI Mode)

#### A. Enhanced Live Dashboard
```bash
python monitor.py
# Or double-click: run_monitor.bat
```

#### B. Strict Assignment Compact View
```bash
python monitor.py --compact
# Or double-click: run_compact.bat
```

#### C. Assignment Demo Mode (Displays 42.5 Mbps, 8.2 Mbps, 1240 PPS)
```bash
python monitor.py --demo --compact
# Or double-click: run_demo.bat
```

### 3. Run Modern Web Dashboard GUI
```bash
python monitor.py --web
# Or double-click: run_web.bat
```
Then open your browser at **`http://localhost:8000`**.

---

## 🖥️ Command Line Options

| Argument | Shorthand | Description |
|---|---|---|
| `--compact` | `-c` | Renders strictly the exact compact layout from the lab prompt |
| `--enhanced` | `-e` | Renders the full colored ANSI dashboard (default) |
| `--demo` | `-d` | Runs simulation matching the exact figures from assignment prompt |
| `--interface <NIC>` | `-i` | Binds to a specific network interface (e.g. `"Wi-Fi"`) |
| `--interval <sec>` | `-t` | Sets sampling interval (default: `1.0` second) |
| `--web` | `-w` | Starts the browser GUI server on `http://localhost:8000` |
| `--port <num>` | | Sets custom port for the web dashboard (default: `8000`) |
| `--list-interfaces`| | Displays all network adapters detected on this PC |
| `--test-traffic` | | Fires test UDP/ICMP packets on start to show dynamic meters |

---

## 📂 Project Architecture

```text
CN_project/
├── monitor.py               # Main CLI Terminal Application & launcher
├── run_monitor.bat          # 1-click launcher for Enhanced CLI
├── run_compact.bat          # 1-click launcher for Compact Assignment View
├── run_demo.bat             # 1-click launcher for Demo Simulation View
├── run_web.bat              # 1-click launcher for Modern Web GUI
├── requirements.txt         # Project dependencies
├── CN_LAB_REPORT.md         # Full Academic Laboratory Report
│
├── core/
│   ├── collector.py         # OS Kernel Network & Protocol collector (ctypes iphlpapi + procfs)
│   ├── utils.py             # Unicode block rendering, ANSI colors, screen formatting
│   └── traffic_generator.py # Asynchronous ICMP, UDP, and TCP traffic injector
│
├── web/
│   ├── server.py            # FastAPI + WebSocket backend server
│   └── static/
│       ├── index.html       # Responsive glassmorphism dashboard
│       ├── style.css        # Premium dark tech theme & animations
│       └── app.js           # Real-time WebSocket consumer & canvas waveform
│
└── tests/
    └── test_collector.py    # Unit tests verifying math, blocks, and renderers
```

---

## 🧮 Mathematical Formulations

Given two sampling timestamps $t_1$ and $t_2$ with sampling interval $\Delta t = t_2 - t_1$ seconds:

1. **Download Throughput (Mbps)**:
   $$\text{Download (Mbps)} = \frac{(B_{rx, 2} - B_{rx, 1}) \times 8}{10^6 \times \Delta t}$$

2. **Upload Throughput (Mbps)**:
   $$\text{Upload (Mbps)} = \frac{(B_{tx, 2} - B_{tx, 1}) \times 8}{10^6 \times \Delta t}$$

3. **Packet Velocity (Packets/sec)**:
   $$\text{Packets/sec} = \frac{(P_{rx, 2} - P_{rx, 1}) + (P_{tx, 2} - P_{tx, 1})}{\Delta t}$$

4. **Protocol Bar Scaling**:
   $$\text{Bar Blocks}_{proto} = \text{round}\left(\frac{\Delta \text{Proto}}{\Delta \text{TCP} + \Delta \text{UDP} + \Delta \text{ICMP}} \times 18\right)$$

---

## 🧪 Running Unit Tests

Run the test suite to verify metric calculations and display formatting:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

All 6 unit tests run and pass in $< 0.5$ seconds.

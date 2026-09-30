/**
 * app.js - Real-Time Network Bandwidth & Protocol Monitor Frontend
 */

(function () {
  'use strict';

  // State
  let ws = null;
  let isDemoMode = false;
  let activeInterface = "All";
  const historyLimit = 35;
  const historyData = {
    timestamps: [],
    download: [],
    upload: [],
  };

  // DOM Elements
  const elDownload = document.getElementById("val-download");
  const elUpload = document.getElementById("val-upload");
  const elPps = document.getElementById("val-pps");
  const elRxPps = document.getElementById("val-rx-pps");
  const elTxPps = document.getElementById("val-tx-pps");
  const elTotalRx = document.getElementById("val-total-rx");
  const elTotalTx = document.getElementById("val-total-tx");

  // Peak Elements
  const elPeakDownload = document.getElementById("val-peak-download");
  const elPeakUpload = document.getElementById("val-peak-upload");
  const elPeakPps = document.getElementById("val-peak-pps");

  // Protocol Elements
  const elTotalProto = document.getElementById("val-total-proto");
  const elBlocksTcp = document.getElementById("blocks-tcp");
  const elBlocksUdp = document.getElementById("blocks-udp");
  const elBlocksIcmp = document.getElementById("blocks-icmp");

  const elBarTcp = document.getElementById("bar-tcp");
  const elBarUdp = document.getElementById("bar-udp");
  const elBarIcmp = document.getElementById("bar-icmp");

  const elRibbonTcp = document.getElementById("ribbon-tcp");
  const elRibbonUdp = document.getElementById("ribbon-udp");
  const elRibbonIcmp = document.getElementById("ribbon-icmp");

  const elPctTcp = document.getElementById("pct-tcp");
  const elPctUdp = document.getElementById("pct-udp");
  const elPctIcmp = document.getElementById("pct-icmp");

  const elRateTcp = document.getElementById("rate-tcp");
  const elRateUdp = document.getElementById("rate-udp");
  const elRateIcmp = document.getElementById("rate-icmp");

  // Navigation & Controls
  const elInterfaceSelect = document.getElementById("interface-select");
  const btnLive = document.getElementById("btn-mode-live");
  const btnDemo = document.getElementById("btn-mode-demo");
  const wsStatus = document.getElementById("ws-status");
  const wsStatusText = document.getElementById("ws-status-text");

  // Traffic Injector
  const btnInjectSpeedtest = document.getElementById("btn-inject-speedtest");
  const btnInjectIcmp = document.getElementById("btn-inject-icmp");
  const btnInjectUdp = document.getElementById("btn-inject-udp");
  const btnInjectTcp = document.getElementById("btn-inject-tcp");
  const btnResetPeaks = document.getElementById("btn-reset-peaks");
  const injectFeedback = document.getElementById("inject-feedback");

  // Sockets Table
  const btnRefreshConns = document.getElementById("btn-refresh-conns");
  const connsTbody = document.getElementById("conns-tbody");

  // Canvas
  const canvas = document.getElementById("traffic-canvas");
  const ctx = canvas.getContext("2d");

  // Initialize
  function init() {
    setupCanvasDPI();
    loadInterfaces();
    connectWebSocket();
    loadConnections();
    bindEvents();
    window.addEventListener("resize", setupCanvasDPI);
  }

  function setupCanvasDPI() {
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    drawWaveform();
  }

  // Format Helper
  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return "0.0 MB";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }

  // Load Interfaces
  async function loadInterfaces() {
    try {
      const res = await fetch("/api/interfaces");
      const data = await res.json();
      elInterfaceSelect.innerHTML = "";
      data.interfaces.forEach((iface) => {
        const opt = document.createElement("option");
        opt.value = iface;
        opt.textContent = iface;
        if (iface === data.current_interface) opt.selected = true;
        elInterfaceSelect.appendChild(opt);
      });
      isDemoMode = data.demo_mode;
      updateModeButtons();
    } catch (e) {
      console.warn("Could not fetch interfaces:", e);
    }
  }

  function updateModeButtons() {
    if (isDemoMode) {
      btnDemo.classList.add("active");
      btnLive.classList.remove("active");
    } else {
      btnLive.classList.add("active");
      btnDemo.classList.remove("active");
    }
  }

  // WebSocket Connection
  function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/traffic`;

    wsStatus.className = "status-badge connecting";
    wsStatusText.textContent = "Connecting...";

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      wsStatus.className = "status-badge";
      wsStatusText.textContent = "Live Stream Active";
    };

    ws.onmessage = (event) => {
      try {
        const snapshot = JSON.parse(event.data);
        renderSnapshot(snapshot);
      } catch (err) {
        console.error("Snapshot parse error:", err);
      }
    };

    ws.onclose = () => {
      wsStatus.className = "status-badge connecting";
      wsStatusText.textContent = "Reconnecting...";
      setTimeout(connectWebSocket, 1500);
    };

    ws.onerror = (err) => {
      console.warn("WS error:", err);
      ws.close();
    };
  }

  // Render Incoming Snapshot
  function renderSnapshot(data) {
    // Primary metrics
    elDownload.textContent = data.download_mbps.toFixed(1);
    elUpload.textContent = data.upload_mbps.toFixed(1);
    elPps.textContent = data.packets_per_sec.toLocaleString();
    elRxPps.textContent = data.packets_recv_per_sec.toLocaleString();
    elTxPps.textContent = data.packets_sent_per_sec.toLocaleString();
    elTotalRx.textContent = formatBytes(data.total_bytes_recv);
    elTotalTx.textContent = formatBytes(data.total_bytes_sent);

    // Peak metrics
    if (elPeakDownload && data.peak_download_mbps !== undefined) {
      elPeakDownload.textContent = `${data.peak_download_mbps.toFixed(1)} Mbps`;
    }
    if (elPeakUpload && data.peak_upload_mbps !== undefined) {
      elPeakUpload.textContent = `${data.peak_upload_mbps.toFixed(1)} Mbps`;
    }
    if (elPeakPps && data.peak_pps !== undefined) {
      elPeakPps.textContent = data.peak_pps.toLocaleString();
    }

    // Protocol distribution metrics
    elTotalProto.textContent = data.total_proto_rate.toLocaleString();

    // Render Unicode blocks: '█' * bars
    elBlocksTcp.textContent = "█".repeat(Math.max(1, data.tcp_bars));
    elBlocksUdp.textContent = "█".repeat(Math.max(1, data.udp_bars));
    elBlocksIcmp.textContent = "█".repeat(Math.max(1, data.icmp_bars));

    // Percentages
    const tcpPct = data.tcp_pct.toFixed(1);
    const udpPct = data.udp_pct.toFixed(1);
    const icmpPct = data.icmp_pct.toFixed(1);

    elPctTcp.textContent = `${tcpPct}%`;
    elPctUdp.textContent = `${udpPct}%`;
    elPctIcmp.textContent = `${icmpPct}%`;

    // Rates
    elRateTcp.textContent = `${data.tcp_rate} pkts/s`;
    elRateUdp.textContent = `${data.udp_rate} pkts/s`;
    elRateIcmp.textContent = `${data.icmp_rate} pkts/s`;

    // Individual progress bars
    elBarTcp.style.width = `${Math.min(100, tcpPct)}%`;
    elBarUdp.style.width = `${Math.min(100, udpPct)}%`;
    elBarIcmp.style.width = `${Math.min(100, icmpPct)}%`;

    // Ribbon continuous segments
    elRibbonTcp.style.width = `${tcpPct}%`;
    elRibbonUdp.style.width = `${udpPct}%`;
    elRibbonIcmp.style.width = `${icmpPct}%`;

    // History for canvas waveform
    historyData.timestamps.push(data.timestamp);
    historyData.download.push(data.download_mbps);
    historyData.upload.push(data.upload_mbps);

    if (historyData.timestamps.length > historyLimit) {
      historyData.timestamps.shift();
      historyData.download.shift();
      historyData.upload.shift();
    }

    drawWaveform();
  }

  // Draw Smooth Waveform Graph on Canvas
  function drawWaveform() {
    const rect = canvas.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;

    ctx.clearRect(0, 0, w, h);

    // Background grid lines
    ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
    ctx.lineWidth = 1;
    const gridLines = 4;
    for (let i = 1; i < gridLines; i++) {
      const y = (h / gridLines) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    if (historyData.download.length < 2) return;

    // Determine scale ceiling
    const maxVal = Math.max(
      ...historyData.download,
      ...historyData.upload,
      10.0 // minimum 10 Mbps scale
    ) * 1.15;

    // Helper to plot a series
    function plotSeries(data, strokeColor, fillColor) {
      const pts = [];
      const step = w / (historyLimit - 1);
      const offset = (historyLimit - data.length) * step;

      for (let i = 0; i < data.length; i++) {
        const x = offset + i * step;
        const y = h - (data[i] / maxVal) * (h - 16) - 8;
        pts.push({ x, y });
      }

      if (pts.length < 2) return;

      // Draw filled area under curve
      ctx.beginPath();
      ctx.moveTo(pts[0].x, h);
      ctx.lineTo(pts[0].x, pts[0].y);

      for (let i = 0; i < pts.length - 1; i++) {
        const mx = (pts[i].x + pts[i + 1].x) / 2;
        const my = (pts[i].y + pts[i + 1].y) / 2;
        ctx.quadraticCurveTo(pts[i].x, pts[i].y, mx, my);
      }
      const last = pts[pts.length - 1];
      ctx.lineTo(last.x, last.y);
      ctx.lineTo(last.x, h);
      ctx.closePath();

      ctx.fillStyle = fillColor;
      ctx.fill();

      // Draw line stroke
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 0; i < pts.length - 1; i++) {
        const mx = (pts[i].x + pts[i + 1].x) / 2;
        const my = (pts[i].y + pts[i + 1].y) / 2;
        ctx.quadraticCurveTo(pts[i].x, pts[i].y, mx, my);
      }
      ctx.lineTo(last.x, last.y);
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 2.5;
      ctx.stroke();

      // Pulsing point on current value
      ctx.beginPath();
      ctx.arc(last.x, last.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = strokeColor;
      ctx.fill();
    }

    // Gradient fills
    const downGradient = ctx.createLinearGradient(0, 0, 0, h);
    downGradient.addColorStop(0, "rgba(16, 185, 129, 0.35)");
    downGradient.addColorStop(1, "rgba(16, 185, 129, 0.0)");

    const upGradient = ctx.createLinearGradient(0, 0, 0, h);
    upGradient.addColorStop(0, "rgba(99, 102, 241, 0.3)");
    upGradient.addColorStop(1, "rgba(99, 102, 241, 0.0)");

    // Plot Upload first then Download on top
    plotSeries(historyData.upload, "#818cf8", upGradient);
    plotSeries(historyData.download, "#10b981", downGradient);
  }

  // Load Active Socket Connections
  async function loadConnections() {
    try {
      const res = await fetch("/api/connections");
      const data = await res.json();
      connsTbody.innerHTML = "";

      if (!data || !data.connections || data.connections.length === 0) {
        connsTbody.innerHTML = `<tr><td colspan="5" class="table-loading">No active TCP/UDP sockets found.</td></tr>`;
        return;
      }

      data.connections.forEach((c) => {
        if (!c || c.error) return;

        const proto = String(c.proto || "TCP").toUpperCase();
        const local = String(c.local || "-");
        const remote = String(c.remote || "-");
        const status = String(c.status || (proto === "TCP" ? "ESTABLISHED" : "STATELESS")).toUpperCase();
        const pid = String(c.pid || "-");

        let stateClass = "state-est";
        if (status.includes("LISTEN")) {
          stateClass = "state-listen";
        } else if (status.includes("WAIT") || status.includes("TIME")) {
          stateClass = "state-wait";
        } else if (status.includes("ESTAB")) {
          stateClass = "state-est";
        }

        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${proto}</strong></td>
          <td>${local}</td>
          <td>${remote}</td>
          <td><span class="state-badge ${stateClass}">${status}</span></td>
          <td>${pid}</td>
        `;
        connsTbody.appendChild(tr);
      });

      if (connsTbody.children.length === 0) {
        connsTbody.innerHTML = `<tr><td colspan="5" class="table-loading">No active TCP/UDP sockets found.</td></tr>`;
      }
    } catch (e) {
      connsTbody.innerHTML = `<tr><td colspan="5" class="table-loading">Error loading sockets: ${e.message}</td></tr>`;
    }
  }

  // Inject Traffic Helper
  async function triggerTraffic(type, param) {
    injectFeedback.textContent = `Injecting ${type.toUpperCase()} traffic...`;
    try {
      const res = await fetch("/api/traffic/inject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type, param }),
      });
      const data = await res.json();
      injectFeedback.textContent = data.message || "Traffic injection dispatched!";
    } catch (e) {
      injectFeedback.textContent = `Injection failed: ${e.message}`;
    }
  }

  // Bind UI Events
  function bindEvents() {
    // Interface switch
    elInterfaceSelect.addEventListener("change", async (e) => {
      const target = e.target.value;
      await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ interface: target }),
      });
      activeInterface = target;
    });

    // Mode Buttons
    btnLive.addEventListener("click", async () => {
      isDemoMode = false;
      updateModeButtons();
      await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ demo_mode: false }),
      });
    });

    btnDemo.addEventListener("click", async () => {
      isDemoMode = true;
      updateModeButtons();
      await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ demo_mode: true }),
      });
    });

    // Traffic generator triggers
    if (btnInjectSpeedtest) {
      btnInjectSpeedtest.addEventListener("click", () => triggerTraffic("speedtest", 6));
    }
    btnInjectIcmp.addEventListener("click", () => triggerTraffic("icmp", 5));
    btnInjectUdp.addEventListener("click", () => triggerTraffic("udp", 350));
    btnInjectTcp.addEventListener("click", () => triggerTraffic("tcp", 4));

    // Reset peaks
    if (btnResetPeaks) {
      btnResetPeaks.addEventListener("click", async () => {
        try {
          await fetch("/api/peaks/reset", { method: "POST" });
          if (elPeakDownload) elPeakDownload.textContent = "0.0 Mbps";
          if (elPeakUpload) elPeakUpload.textContent = "0.0 Mbps";
          if (elPeakPps) elPeakPps.textContent = "0";
          injectFeedback.textContent = "Peak speeds have been reset.";
        } catch (e) {
          console.warn("Reset peak error:", e);
        }
      });
    }

    // Refresh connections
    btnRefreshConns.addEventListener("click", loadConnections);
  }

  // Boot
  document.addEventListener("DOMContentLoaded", init);
})();

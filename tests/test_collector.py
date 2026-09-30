"""
tests/test_collector.py - Unit and Integration Tests for Network Bandwidth Monitor
"""

import unittest
import time
from core.collector import NetworkTrafficCollector, NetworkSnapshot
from core.utils import render_compact_display, render_enhanced_display
from core.traffic_generator import TrafficGenerator


class TestNetworkCollector(unittest.TestCase):

    def test_demo_snapshot_values(self):
        """Verifies that demo mode produces metrics matching the assignment problem statement."""
        collector = NetworkTrafficCollector(demo_mode=True)
        snapshot = collector.get_snapshot()

        self.assertTrue(snapshot.is_demo)
        # Should be centered around 42.5 Mbps
        self.assertAlmostEqual(snapshot.download_mbps, 42.5, delta=3.0)
        # Should be centered around 8.2 Mbps
        self.assertAlmostEqual(snapshot.upload_mbps, 8.2, delta=2.0)
        # Should be centered around 1240 pps
        self.assertAlmostEqual(snapshot.packets_per_sec, 1240, delta=100)

        # Expected block count ratio: 12 TCP, 4 UDP, 2 ICMP
        self.assertEqual(snapshot.tcp_bars, 12)
        self.assertEqual(snapshot.udp_bars, 4)
        self.assertEqual(snapshot.icmp_bars, 2)

    def test_live_snapshot_generation(self):
        """Tests that a live hardware snapshot returns valid non-negative numbers."""
        collector = NetworkTrafficCollector(demo_mode=False)
        time.sleep(0.2)
        snapshot = collector.get_snapshot()

        self.assertIsInstance(snapshot, NetworkSnapshot)
        self.assertGreaterEqual(snapshot.download_mbps, 0.0)
        self.assertGreaterEqual(snapshot.upload_mbps, 0.0)
        self.assertGreaterEqual(snapshot.packets_per_sec, 0)
        self.assertGreaterEqual(snapshot.tcp_bars, 0)
        self.assertGreaterEqual(snapshot.udp_bars, 0)
        self.assertGreaterEqual(snapshot.icmp_bars, 0)

    def test_bar_scaling_logic(self):
        """Verifies proportional scaling of bar lengths."""
        collector = NetworkTrafficCollector(max_bar_length=18)

        # Case 1: Proportions matching 6:2:1 (like 12:4:2 out of 18)
        t, u, i = collector._compute_bar_lengths(600, 200, 100, 900)
        self.assertEqual(t, 12)
        self.assertEqual(u, 4)
        self.assertEqual(i, 2)

        # Case 2: Zero traffic
        t0, u0, i0 = collector._compute_bar_lengths(0, 0, 0, 0)
        self.assertEqual((t0, u0, i0), (0, 0, 0))

        # Case 3: 1 packet in ICMP gets at least 1 bar
        t1, u1, i1 = collector._compute_bar_lengths(10000, 50, 1, 10051)
        self.assertGreaterEqual(i1, 1)

    def test_compact_display_format(self):
        """Ensures the compact display exactly matches the lab problem statement layout."""
        collector = NetworkTrafficCollector(demo_mode=True)
        snapshot = collector.get_snapshot()
        output = render_compact_display(snapshot)

        lines = output.splitlines()
        self.assertEqual(lines[0], "Network Monitor")
        self.assertEqual(lines[1], "")
        self.assertTrue(lines[2].startswith("Download:  "))
        self.assertTrue(lines[3].startswith("Upload:    "))
        self.assertEqual(lines[4], "")
        self.assertTrue(lines[5].startswith("Packets/sec:  "))
        self.assertEqual(lines[6], "")
        self.assertTrue(lines[7].startswith("TCP:  "))
        self.assertTrue(lines[8].startswith("UDP:  "))
        self.assertTrue(lines[9].startswith("ICMP: "))

        # Check block characters
        self.assertIn("████████████", lines[7])
        self.assertIn("████", lines[8])
        self.assertIn("██", lines[9])

    def test_enhanced_display(self):
        """Tests that enhanced display renders header and sections."""
        collector = NetworkTrafficCollector(demo_mode=True)
        snapshot = collector.get_snapshot()
        output = render_enhanced_display(snapshot)

        self.assertIn("NETWORK BANDWIDTH MONITOR", output)
        self.assertIn("Download:", output)
        self.assertIn("Upload:", output)
        self.assertIn("Protocol Breakdown:", output)

    def test_traffic_generator_lifecycle(self):
        """Tests traffic generator initialization and non-blocking safety."""
        tg = TrafficGenerator()
        self.assertFalse(tg.is_running())
        tg.stop()


if __name__ == "__main__":
    unittest.main()

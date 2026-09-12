"""
MakiAI — System Health & Hardware Monitor
Provides real-time introspection into laptop hardware metrics (battery status,
power states, CPU/RAM utilization, storage) with proactive spoken background alerts.
"""

import time
import threading
from typing import Optional, Dict, Callable
import psutil


class SystemHealthMonitor:
    """
    Hardware and battery health monitoring service.
    Features:
      - On-demand hardware vitals introspection (Battery, CPU, RAM, Disk).
      - Low-overhead background daemon (180s interval).
      - Proactive audio alerts with cooldown protection for critical power levels (<20%).
    """

    def __init__(self, tts_callback: Optional[Callable[[str], None]] = None):
        self.tts_callback = tts_callback
        self._daemon_thread: Optional[threading.Thread] = None
        self._running = False
        self._poll_interval = 180  # 3 minutes

        # Cooldown state flags
        self._last_critical_alert_time = 0.0
        self._critical_cooldown = 900  # 15 minutes between repeated alerts
        self._last_plugged_state: Optional[bool] = None

        self.start_monitoring()

    def set_tts_callback(self, callback: Callable[[str], None]) -> None:
        """Inject TTS speaker callback for proactive audio announcements."""
        self.tts_callback = callback

    # ─── Vitals Metrics Introspection ─────────────────────────────────────────

    def get_battery(self) -> Dict:
        """Query laptop battery percentage, power plugged state, and estimated time."""
        try:
            bat = psutil.sensors_battery()
            if not bat:
                return {
                    "available": False,
                    "percent": 100,
                    "plugged": True,
                    "status_text": "Desktop power supply (no battery detected)",
                }

            percent = int(bat.percent)
            plugged = bool(bat.power_plugged)
            secs_left = bat.secsleft

            time_str = ""
            if plugged:
                time_str = "fully charged" if percent >= 99 else "charging"
            elif secs_left > 0 and secs_left != psutil.POWER_TIME_UNLIMITED:
                mins = secs_left // 60
                hrs = mins // 60
                rem_mins = mins % 60
                time_str = f"{hrs}h {rem_mins}m remaining" if hrs > 0 else f"{rem_mins} minutes remaining"
            else:
                time_str = "on battery power"

            return {
                "available": True,
                "percent": percent,
                "plugged": plugged,
                "secs_left": secs_left,
                "time_str": time_str,
                "is_critical": percent <= 20 and not plugged,
                "is_low": percent <= 30 and not plugged,
            }
        except Exception as e:
            print(f"[SystemHealth] Battery query error: {e}")
            return {"available": False, "percent": 100, "plugged": True, "time_str": "unknown"}

    def get_cpu_ram(self) -> Dict:
        """Query CPU utilization and RAM memory statistics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            ram_percent = mem.percent
            ram_used_gb = round(mem.used / (1024 ** 3), 1)
            ram_total_gb = round(mem.total / (1024 ** 3), 1)

            return {
                "cpu_percent": cpu_percent,
                "ram_percent": ram_percent,
                "ram_used_gb": ram_used_gb,
                "ram_total_gb": ram_total_gb,
            }
        except Exception as e:
            print(f"[SystemHealth] CPU/RAM query error: {e}")
            return {"cpu_percent": 0.0, "ram_percent": 0.0, "ram_used_gb": 0.0, "ram_total_gb": 0.0}

    def get_disk(self) -> Dict:
        """Query primary storage disk space."""
        try:
            disk = psutil.disk_usage("C:\\")
            free_gb = round(disk.free / (1024 ** 3), 1)
            total_gb = round(disk.total / (1024 ** 3), 1)
            used_percent = disk.percent
            return {"free_gb": free_gb, "total_gb": total_gb, "used_percent": used_percent}
        except Exception as e:
            print(f"[SystemHealth] Disk query error: {e}")
            return {"free_gb": 0.0, "total_gb": 0.0, "used_percent": 0.0}

    def get_vitals_summary(self) -> str:
        """Return conversational, natural Jarvis-style hardware vitals overview."""
        bat = self.get_battery()
        perf = self.get_cpu_ram()
        disk = self.get_disk()

        parts = []
        if bat.get("available"):
            plug_desc = "plugged into AC power" if bat["plugged"] else "running on battery"
            parts.append(f"Your battery is at {bat['percent']} percent and {plug_desc} ({bat['time_str']}).")

        parts.append(f"CPU utilization is currently at {perf['cpu_percent']} percent, with RAM usage at {perf['ram_percent']} percent ({perf['ram_used_gb']} of {perf['ram_total_gb']} GB).")

        if disk.get("free_gb"):
            parts.append(f"Your primary drive has {disk['free_gb']} GB of free storage remaining.")

        return f"Sir, here are your current system vitals: {' '.join(parts)}"

    # ─── Background Polling Daemon ───────────────────────────────────────────

    def start_monitoring(self) -> None:
        """Start low-priority background hardware monitoring thread."""
        if self._running:
            return
        self._running = True
        self._daemon_thread = threading.Thread(target=self._monitor_loop, daemon=True, name="MakiAI-SystemHealthDaemon")
        self._daemon_thread.start()
        print("[SystemHealth] Hardware monitoring daemon started (180s interval).")

    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._running = False

    def _monitor_loop(self) -> None:
        """Low-frequency polling loop for battery and critical hardware warnings."""
        while self._running:
            try:
                bat = self.get_battery()
                now = time.time()

                if bat.get("available"):
                    # Detect charger unplugged vs plugged transitions
                    if self._last_plugged_state is not None and bat["plugged"] != self._last_plugged_state:
                        if bat["plugged"]:
                            print(f"[SystemHealth] AC Power Connected. Battery at {bat['percent']}%.")
                        else:
                            print(f"[SystemHealth] AC Power Disconnected. Running on Battery ({bat['percent']}%).")
                    self._last_plugged_state = bat["plugged"]

                    # Check for Critical Battery Alert (< 20% and not charging)
                    if bat["percent"] <= 20 and not bat["plugged"]:
                        if (now - self._last_critical_alert_time) > self._critical_cooldown:
                            self._last_critical_alert_time = now
                            alert_msg = f"Warning sir, battery level is critical at {bat['percent']} percent. Please connect your charger."
                            print(f"[SystemHealth] PROACTIVE ALERT: {alert_msg}")
                            if self.tts_callback:
                                try:
                                    self.tts_callback(alert_msg)
                                except Exception as err:
                                    print(f"[SystemHealth] TTS callback error: {err}")

            except Exception as e:
                print(f"[SystemHealth] Daemon error: {e}")

            # Sleep in small slices to allow clean shutdown
            for _ in range(self._poll_interval):
                if not self._running:
                    break
                time.sleep(1)

"""
MakiAI — Window Manager & Inter-Monitor Relocation Service
Provides visual window dragging and multi-monitor management.
Enables MakiAI to physically un-maximize, grab, and visually drag active windows
across the virtual desktop coordinate space between primary and secondary monitors.
"""

import time
import re
import ctypes
from ctypes import wintypes
from typing import Optional, List, Dict, Tuple
from pathlib import Path

user32 = ctypes.windll.user32
shcore = getattr(ctypes.windll, "shcore", None)

# Enable per-monitor DPI awareness
try:
    if shcore:
        shcore.SetProcessDpiAwareness(2)  # Per-monitor aware v2
    else:
        user32.SetProcessDPIAware()
except Exception:
    pass

# Windows Constants
SW_RESTORE = 9
SW_MAXIMIZE = 3
SW_MINIMIZE = 6
SWP_NOZORDER = 0x0004
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class WindowManager:
    """
    Service for inspecting, moving, visually dragging, and auto-tiling
    application windows across multi-monitor virtual desktop coordinates.
    """

    def __init__(self):
        self._ensure_desktop_access()

    def _ensure_desktop_access(self) -> None:
        """Attach thread to interactive window station (WinSta0\\Default)."""
        try:
            hwinsta = user32.OpenWindowStationW("WinSta0", False, 0x000F037F)
            if hwinsta:
                user32.SetProcessWindowStation(hwinsta)
                hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
                if hdesk:
                    user32.SetThreadDesktop(hdesk)
        except Exception as e:
            print(f"[WindowManager] Desktop access attach warning: {e}")

    # ─── Monitor Detection & Calibration ─────────────────────────────────────

    def get_monitors(self) -> List[Dict]:
        """
        Detect and calibrate all physical monitors in the virtual desktop space,
        including precise usable work area dimensions (accounting for taskbars).

        Returns:
            List of dicts with monitor boundaries, usable work areas, and primary flags.
        """
        monitors = []

        def _enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi))

            r = mi.rcMonitor
            w = r.right - r.left
            h = r.bottom - r.top

            rw = mi.rcWork
            work_w = rw.right - rw.left
            work_h = rw.bottom - rw.top

            is_primary = (r.left == 0 and r.top == 0)
            monitors.append({
                "left": r.left,
                "top": r.top,
                "right": r.right,
                "bottom": r.bottom,
                "width": w,
                "height": h,
                "work_left": rw.left,
                "work_top": rw.top,
                "work_right": rw.right,
                "work_bottom": rw.bottom,
                "work_width": work_w,
                "work_height": work_h,
                "center_x": r.left + w // 2,
                "center_y": r.top + h // 2,
                "is_primary": is_primary,
            })
            return 1

        MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
        user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(_enum_proc), 0)

        # Sort left to right
        monitors.sort(key=lambda m: m["left"])
        for idx, m in enumerate(monitors):
            m["index"] = idx + 1
            if m["is_primary"]:
                m["label"] = f"Monitor {m['index']} (Primary / Main)"
            elif m["left"] < 0:
                m["label"] = f"Monitor {m['index']} (Left / Secondary)"
            else:
                m["label"] = f"Monitor {m['index']} (Right / Secondary)"

        return monitors

    def get_monitor_count(self) -> int:
        return len(self.get_monitors())

    def get_monitor_for_rect(self, rect: Tuple[int, int, int, int]) -> Optional[Dict]:
        """Determine which monitor contains the center of the given rectangle."""
        cx = rect[0] + (rect[2] - rect[0]) // 2
        cy = rect[1] + (rect[3] - rect[1]) // 2
        for m in self.get_monitors():
            if m["left"] <= cx <= m["right"] and m["top"] <= cy <= m["bottom"]:
                return m
        return self.get_monitors()[0] if self.get_monitors() else None

    # ─── Window Resolution & Filtering ───────────────────────────────────────

    def get_visible_windows(self, include_minimized: bool = False) -> List[Dict]:
        """
        Enumerate all active visible application windows.
        Filters out background OS shells, overlays, cloaked UWP apps, and toolbars.
        """
        self._ensure_desktop_access()
        windows = []
        dwmapi = getattr(ctypes.windll, "dwmapi", None)

        def _is_cloaked(hwnd):
            if dwmapi:
                cloaked = ctypes.c_int(0)
                DWMWA_CLOAKED = 14
                hr = dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
                if hr == 0 and cloaked.value != 0:
                    return True
            return False

        def _enum_windows_proc(hwnd, lParam):
            if not user32.IsWindowVisible(hwnd):
                return True

            is_minimized = bool(user32.IsIconic(hwnd))
            if is_minimized and not include_minimized:
                return True

            if _is_cloaked(hwnd):
                return True

            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value.strip()

                # Filter out system utility overlays
                ignored_titles = (
                    "Program Manager", "Settings", "Windows Input Experience",
                    "Task Switching", "TranslucentTB", "NVIDIA GeForce Overlay",
                    "MakiAI Overlay", "PopupHost", "Setup", "Default IME"
                )
                if title and not any(ign in title for ign in ignored_titles):
                    rect = wintypes.RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    w = rect.right - rect.left
                    h = rect.bottom - rect.top
                    if (w > 120 and h > 120) or is_minimized:
                        is_maximized = bool(user32.IsZoomed(hwnd))
                        windows.append({
                            "hwnd": hwnd,
                            "title": title,
                            "rect": (rect.left, rect.top, rect.right, rect.bottom),
                            "width": w,
                            "height": h,
                            "is_maximized": is_maximized,
                            "is_minimized": is_minimized,
                        })
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(_enum_windows_proc), 0)
        return windows

    def find_window(self, query: str = "") -> Optional[Dict]:
        """
        Match an application window by title, process keyword, or active state.
        """
        windows = self.get_visible_windows(include_minimized=True)
        if not windows:
            return None

        q = query.lower().strip()

        # If active / current window requested
        if not q or q in ("active", "current", "this window", "this app", "here"):
            fg_hwnd = user32.GetForegroundWindow()
            for w in windows:
                if w["hwnd"] == fg_hwnd:
                    return w
            return windows[0]

        # Aliases mapping
        alias_map = {
            "chrome": ["google chrome", "chrome"],
            "vscode": ["visual studio code", "antigravity ide", "code", "vs code"],
            "code": ["visual studio code", "antigravity ide", "code", "vs code"],
            "editor": ["visual studio code", "antigravity ide", "code", "notepad"],
            "browser": ["chrome", "edge", "firefox", "brave"],
            "makiai": ["makiai"],
            "notepad": ["notepad"],
            "spotify": ["spotify"],
            "explorer": ["file explorer", "explorer"],
        }

        search_terms = alias_map.get(q, [q])

        # Match search terms
        for term in search_terms:
            for w in windows:
                if term in w["title"].lower():
                    return w

        # Fallback substring match
        for w in windows:
            if any(word in w["title"].lower() for word in q.split() if len(word) > 2):
                return w

        return None

    # ─── Visual Dragging & Relocation Engine ──────────────────────────────────

    def move_window_to_monitor(
        self,
        app_query: str = "",
        target_monitor: str = "other",
        visual_drag: bool = True
    ) -> str:
        """
        Relocate a window to the target monitor with visual dragging agency.

        Args:
            app_query: Target application name e.g. "Chrome", "VS Code", "active"
            target_monitor: "other", "secondary", "primary", "1", "2", "left", "right"
            visual_drag: Whether to physically animate cursor movement and dragging.

        Returns:
            Spoken feedback confirmation.
        """
        monitors = self.get_monitors()
        if len(monitors) < 2:
            return "I only detected a single monitor plugged in, sir. Please connect a second display to move windows."

        # Find target window
        win = self.find_window(app_query)
        if not win:
            return f"I couldn't find an active window matching '{app_query}', sir."

        hwnd = win["hwnd"]
        current_mon = self.get_monitor_for_rect(win["rect"])

        # Determine destination monitor
        dest_mon = None
        tm = str(target_monitor).lower().strip()

        if tm in ("other", "next", "second", "secondary", "2", "monitor 2"):
            # Pick monitor different from current
            for m in monitors:
                if current_mon and m["left"] != current_mon["left"]:
                    dest_mon = m
                    break
        elif tm in ("primary", "main", "1", "monitor 1"):
            for m in monitors:
                if m["is_primary"]:
                    dest_mon = m
                    break
        elif tm in ("left", "screen 1", "left screen"):
            dest_mon = monitors[0]
        elif tm in ("right", "screen 2", "right screen"):
            dest_mon = monitors[-1]

        if not dest_mon:
            # Fallback to alternate monitor
            dest_mon = monitors[0] if current_mon and current_mon["left"] == monitors[-1]["left"] else monitors[-1]

        if current_mon and dest_mon["left"] == current_mon["left"]:
            return f"{win['title'][:30]} is already on {dest_mon['label']}, sir."

        # Activate and restore if maximized
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.1)

        if win["is_maximized"]:
            user32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.15)

        # Re-read bounding box after restore
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        cur_left, cur_top = rect.left, rect.top
        cur_w = rect.right - rect.left
        cur_h = rect.bottom - rect.top

        # Visual Drag using PyAutoGUI
        dragged_visually = False
        if visual_drag:
            try:
                import pyautogui
                pyautogui.FAILSAFE = True
                pyautogui.PAUSE = 0.02

                # Start drag from window titlebar center
                start_x = cur_left + cur_w // 2
                start_y = max(cur_top + 18, cur_top + 10)

                # Target coordinates on destination monitor
                end_x = dest_mon["left"] + cur_w // 2 + 50
                end_y = dest_mon["top"] + 100

                # Ensure within destination boundaries
                end_x = max(dest_mon["left"] + 50, min(end_x, dest_mon["right"] - 100))
                end_y = max(dest_mon["top"] + 50, min(end_y, dest_mon["bottom"] - 100))

                # Physical cursor tweening
                pyautogui.moveTo(start_x, start_y, duration=0.3, tween=pyautogui.easeInOutQuad)
                pyautogui.mouseDown(button='left')
                time.sleep(0.05)
                pyautogui.moveTo(end_x, end_y, duration=0.8, tween=pyautogui.easeInOutQuad)
                time.sleep(0.05)
                pyautogui.mouseUp(button='left')
                dragged_visually = True
                print(f"[WindowManager] Visual drag complete: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
            except Exception as e:
                print(f"[WindowManager] PyAutoGUI visual drag error: {e}")

        # Direct API Fallback / Coordinate Enforcement
        new_x = dest_mon["left"] + (dest_mon["width"] - cur_w) // 2
        new_y = dest_mon["top"] + (dest_mon["height"] - cur_h) // 3
        user32.SetWindowPos(hwnd, 0, new_x, new_y, cur_w, cur_h, SWP_NOZORDER | SWP_SHOWWINDOW)

        clean_title = re.sub(r"[\-_|].*$", "", win["title"]).strip() or "The window"
        dest_name = "secondary monitor" if not dest_mon["is_primary"] else "main monitor"

        return f"Done, sir. I've moved {clean_title} to your {dest_name}."

    # ─── Dynamic Auto-Tiling & Workspace Fitting ─────────────────────────────

    # ─── Dynamic Auto-Tiling & Multi-Monitor Workspace Fitting ───────────────

    def auto_tile(
        self,
        target_monitor: str = "auto",
        layout: str = "auto",
        priority_apps: Optional[List[str]] = None,
        max_windows: int = 4
    ) -> str:
        """
        Partition, maximize, and snap up to 4 active windows across dual monitors
        (or a single target monitor) with zero overlap and full-screen fitting.

        Multi-Monitor Logic (Dual Display):
          - N = 1: 1 Window maximized on Main Monitor.
          - N = 2: 1 Window on Secondary Monitor (Full screen), 1 Window on Main Monitor (Full screen).
          - N = 3: 1 Window on Secondary Monitor (Full screen), 2 Windows on Main Monitor (50/50 side-by-side).
          - N = 4: 2 Windows on Secondary Monitor (50/50), 2 Windows on Main Monitor (50/50).
          - N > 4: First 4 active windows fitted; all remaining 5+ windows minimized.

        Args:
            target_monitor: "auto", "all", "workspace", "1", "2", "main", "secondary", "left", "right"
            layout: "auto", "split", "quadrant", "columns"
            priority_apps: Optional list of app aliases to prioritize
            max_windows: Cap to 4 windows maximum
        """
        monitors = self.get_monitors()
        if not monitors:
            return "No displays detected to tile windows, sir."

        tm = str(target_monitor).lower().strip()
        all_visible = self.get_visible_windows(include_minimized=False)

        # Gather target windows
        windows_to_tile = []
        if priority_apps:
            for app_query in priority_apps:
                w = self.find_window(app_query)
                if w and not any(existing["hwnd"] == w["hwnd"] for existing in windows_to_tile):
                    windows_to_tile.append(w)

        # Add other visible windows up to max_windows (4)
        for w in all_visible:
            if len(windows_to_tile) >= max_windows:
                break
            if not any(existing["hwnd"] == w["hwnd"] for existing in windows_to_tile):
                windows_to_tile.append(w)

        # Minimize extra background windows beyond the top 4
        if len(all_visible) > max_windows:
            tiled_hwnds = {w["hwnd"] for w in windows_to_tile}
            for w in all_visible:
                if w["hwnd"] not in tiled_hwnds:
                    user32.ShowWindow(w["hwnd"], SW_MINIMIZE)

        n = len(windows_to_tile)
        if n == 0:
            return "There are no active application windows open to arrange, sir."

        # ─── Dual Monitor Auto-Distribution ──────────────────────────────────
        is_multi_mon_mode = (len(monitors) >= 2 and tm in ("auto", "all", "workspace", "both", "monitors", "screens", "2 monitors", "current"))

        if is_multi_mon_mode:
            sec_mon = monitors[0] if not monitors[0]["is_primary"] else monitors[-1]
            main_mon = [m for m in monitors if m["is_primary"]][0] if any(m["is_primary"] for m in monitors) else monitors[-1]

            # Secondary usable bounds
            sx_left = sec_mon.get("work_left", sec_mon["left"])
            sx_top = sec_mon.get("work_top", sec_mon["top"])
            sx_w = sec_mon.get("work_width", sec_mon["width"])
            sx_h = sec_mon.get("work_height", sec_mon["height"])

            # Main usable bounds
            mx_left = main_mon.get("work_left", main_mon["left"])
            mx_top = main_mon.get("work_top", main_mon["top"])
            mx_w = main_mon.get("work_width", main_mon["width"])
            mx_h = main_mon.get("work_height", main_mon["height"])

            assignments = []  # List of (window_dict, (x, y, w, h))

            if n == 1:
                assignments.append((windows_to_tile[0], (mx_left, mx_top, mx_w, mx_h)))

            elif n == 2:
                # 1 on Secondary (Full), 1 on Main (Full)
                assignments.append((windows_to_tile[0], (sx_left, sx_top, sx_w, sx_h)))
                assignments.append((windows_to_tile[1], (mx_left, mx_top, mx_w, mx_h)))

            elif n == 3:
                # 1 on Secondary (Full), 2 on Main (50/50 side-by-side)
                # If a browser is in the list, prioritize placing browser on secondary monitor
                browser_win = None
                for w in windows_to_tile:
                    if any(b in w["title"].lower() for b in ("chrome", "gemini", "facebook", "edge", "firefox", "brave")):
                        browser_win = w
                        break

                sec_win = browser_win if browser_win else windows_to_tile[0]
                main_wins = [w for w in windows_to_tile if w["hwnd"] != sec_win["hwnd"]][:2]

                # Secondary Monitor (Full screen)
                assignments.append((sec_win, (sx_left, sx_top, sx_w, sx_h)))

                # Main Monitor (50/50 split)
                half_mw = mx_w // 2
                assignments.append((main_wins[0], (mx_left, mx_top, half_mw, mx_h)))
                assignments.append((main_wins[1], (mx_left + half_mw, mx_top, mx_w - half_mw, mx_h)))

            elif n >= 4:
                # 2 on Secondary (50/50), 2 on Main (50/50)
                half_sw = sx_w // 2
                assignments.append((windows_to_tile[0], (sx_left, sx_top, half_sw, sx_h)))
                assignments.append((windows_to_tile[1], (sx_left + half_sw, sx_top, sx_w - half_sw, sx_h)))

                half_mw = mx_w // 2
                assignments.append((windows_to_tile[2], (mx_left, mx_top, half_mw, mx_h)))
                assignments.append((windows_to_tile[3], (mx_left + half_mw, mx_top, mx_w - half_mw, mx_h)))

            # Execute positioning
            for win, (x, y, w, h) in assignments:
                hwnd = win["hwnd"]
                if win.get("is_maximized"):
                    user32.ShowWindow(hwnd, SW_RESTORE)
                    time.sleep(0.04)
                user32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_NOZORDER | SWP_SHOWWINDOW)

            app_titles = [re.sub(r"[\-_|].*$", "", w["title"]).strip() for w, _ in assignments]
            desc = ", ".join(app_titles[:3])
            if len(app_titles) > 3:
                desc += f" and {app_titles[3]}"

            return f"Done, sir. I've maximized and fitted {desc} across both your monitors with zero overlap."

        # ─── Single Monitor Tiling Fallback ──────────────────────────────────
        mon = None
        if tm in ("1", "primary", "main", "monitor 1", "screen 1"):
            for m in monitors:
                if m["is_primary"]:
                    mon = m
                    break
        elif tm in ("2", "second", "secondary", "monitor 2", "screen 2"):
            for m in monitors:
                if not m["is_primary"]:
                    mon = m
                    break

        if not mon:
            mon = monitors[0]

        work_x = mon.get("work_left", mon["left"])
        work_y = mon.get("work_top", mon["top"])
        work_w = mon.get("work_width", mon["width"])
        work_h = mon.get("work_height", mon["height"])

        slots = []
        if n == 1:
            slots.append((work_x, work_y, work_w, work_h))
        elif n == 2:
            col_w = work_w // 2
            slots.append((work_x, work_y, col_w, work_h))
            slots.append((work_x + col_w, work_y, work_w - col_w, work_h))
        elif n == 3:
            col_w = work_w // 3
            slots.append((work_x, work_y, col_w, work_h))
            slots.append((work_x + col_w, work_y, col_w, work_h))
            slots.append((work_x + 2 * col_w, work_y, work_w - 2 * col_w, work_h))
        else:
            half_w = work_w // 2
            half_h = work_h // 2
            slots.append((work_x, work_y, half_w, half_h))
            slots.append((work_x + half_w, work_y, work_w - half_w, half_h))
            slots.append((work_x, work_y + half_h, half_w, work_h - half_h))
            slots.append((work_x + half_w, work_y + half_h, work_w - half_w, work_h - half_h))

        for i, win in enumerate(windows_to_tile[:len(slots)]):
            hwnd = win["hwnd"]
            sx, sy, sw, sh = slots[i]
            if win.get("is_maximized"):
                user32.ShowWindow(hwnd, SW_RESTORE)
                time.sleep(0.04)
            user32.SetWindowPos(hwnd, 0, sx, sy, sw, sh, SWP_NOZORDER | SWP_SHOWWINDOW)

        app_names = [re.sub(r"[\-_|].*$", "", w["title"]).strip() for w in windows_to_tile[:len(slots)]]
        return f"Done, sir. I've tiled {', '.join(app_names)} onto {mon['label']}."

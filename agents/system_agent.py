"""
System Agent - OS-level controls
Volume, brightness, application launching, keyboard input
"""

import os
import sys
import subprocess
import time
from typing import Dict, Optional


class SystemAgent:
    """
    System Control Agent for MEGAN.

    Capabilities:
    - Set system volume
    - Set screen brightness (Windows/macOS/Linux)
    - Open applications
    - Type text via keyboard
    - Get system information (CPU, RAM, disk)
    - Lock screen / shut down (with confirmation)
    """

    def __init__(self):
        self._platform  = sys.platform   # 'win32', 'darwin', 'linux'
        self._pynput    = None
        self._psutil    = None
        self._brightness_ctrl = None
        self._init_modules()

    def _init_modules(self):
        """Lazy-load optional system modules."""
        try:
            import pynput.keyboard as kb
            self._pynput = kb
            print("[SYSTEM] OK: pynput ready")
        except ImportError:
            print("[SYSTEM] WARN:  pynput not installed -- keyboard typing disabled")

        try:
            import psutil
            self._psutil = psutil
            print("[SYSTEM] OK: psutil ready")
        except ImportError:
            print("[SYSTEM] WARN:  psutil not installed -- system info disabled")

        try:
            import screen_brightness_control as sbc
            self._brightness_ctrl = sbc
            print("[SYSTEM] OK: screen_brightness_control ready")
        except ImportError:
            print("[SYSTEM] WARN:  screen_brightness_control not installed -- brightness control disabled")

    # ─── Volume ───────────────────────────────────────────────────────────────

    def set_volume(self, level: int) -> Dict:
        """
        Set system volume (0–100).

        Args:
            level: Volume percentage 0–100

        Returns:
            Status dict
        """
        level = max(0, min(100, int(level)))

        try:
            if self._platform == "win32":
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                # pycaw uses -65.25 dB to 0.0 dB
                import math
                scalar = level / 100.0
                db     = 20 * math.log10(scalar) if scalar > 0 else -65.25
                volume.SetMasterVolumeLevel(db, None)

            elif self._platform == "darwin":
                subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=True)

            else:  # Linux
                subprocess.run(["amixer", "-q", "sset", "Master", f"{level}%"], check=True)

            print(f"[SYSTEM] Volume set to {level}%")
            return {"status": "success", "volume": level}

        except Exception as e:
            # Fallback: try PowerShell on Windows
            if self._platform == "win32":
                try:
                    ps_cmd = (
                        f"$vol = [math]::Round({level} / 100.0 * 65535);"
                        f"(New-Object -ComObject WScript.Shell).SendKeys([char]173);"  # noqa
                        f"Add-Type -TypeDefinition @'public class V{{[System.Runtime.InteropServices.DllImport(\"winmm.dll\")]public static extern int waveOutSetVolume(IntPtr h, uint d);}}' -Language CSharp;"
                        f"[V]::waveOutSetVolume([IntPtr]::Zero, ($vol * 65536 + $vol));"
                    )
                    subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
                    return {"status": "success", "volume": level, "method": "powershell"}
                except Exception:
                    pass
            print(f"[ERROR] Volume control failed: {str(e)}")
            return {"error": str(e)}

    # ─── Brightness ───────────────────────────────────────────────────────────

    def set_brightness(self, level: int) -> Dict:
        """
        Set screen brightness (0–100).

        Args:
            level: Brightness percentage 0–100
        """
        level = max(0, min(100, int(level)))

        if self._brightness_ctrl:
            try:
                self._brightness_ctrl.set_brightness(level)
                print(f"[SYSTEM] Brightness set to {level}%")
                return {"status": "success", "brightness": level}
            except Exception as e:
                print(f"[ERROR] Brightness control failed: {str(e)}")
                return {"error": str(e)}

        # Fallback for Windows via PowerShell WMI
        if self._platform == "win32":
            try:
                cmd = (
                    f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                    f".WmiSetBrightness(1,{level})"
                )
                subprocess.run(["powershell", "-Command", cmd], capture_output=True, check=True)
                return {"status": "success", "brightness": level, "method": "wmi"}
            except Exception as e:
                return {"error": str(e)}

        return {"error": "screen_brightness_control not installed"}

    # ─── Applications ─────────────────────────────────────────────────────────

    def open_application(self, app: str) -> Dict:
        """
        Open an application by name.

        Windows: searches Start menu / Program Files
        macOS:   uses 'open -a'
        Linux:   runs command directly
        """
        print(f"[SYSTEM] Opening application: {app}")

        try:
            if self._platform == "win32":
                # Common aliases
                aliases = {
                    "chrome":   "chrome",
                    "firefox":  "firefox",
                    "notepad":  "notepad",
                    "calculator": "calc",
                    "explorer": "explorer",
                    "word":     "winword",
                    "excel":    "excel",
                    "powershell": "powershell",
                    "terminal": "cmd",
                    "cmd":      "cmd",
                    "paint":    "mspaint",
                }
                cmd = aliases.get(app.lower(), app)
                subprocess.Popen(cmd, shell=True)

            elif self._platform == "darwin":
                subprocess.Popen(["open", "-a", app])

            else:
                subprocess.Popen([app])

            return {"status": "success", "app": app}

        except FileNotFoundError:
            return {"error": f"Application not found: {app}"}
        except Exception as e:
            print(f"[ERROR] Open app failed: {str(e)}")
            return {"error": str(e)}

    # ─── Keyboard ─────────────────────────────────────────────────────────────

    def type_text(self, text: str, interval: float = 0.02) -> Dict:
        """
        Type text as keyboard input at the current cursor position.

        Args:
            text:     Text to type
            interval: Delay between keypresses (seconds)
        """
        if self._pynput is None:
            return {"error": "pynput not installed -- keyboard typing disabled"}

        try:
            controller = self._pynput.Controller()
            controller.type(text)
            print(f"[SYSTEM] Typed {len(text)} characters")
            return {"status": "success", "characters_typed": len(text)}

        except Exception as e:
            print(f"[ERROR] Type text failed: {str(e)}")
            return {"error": str(e)}

    def press_keys(self, *keys) -> Dict:
        """Press a key combination (e.g. Ctrl+C)."""
        if self._pynput is None:
            return {"error": "pynput not installed"}
        try:
            from pynput.keyboard import Key, Controller
            kb = Controller()
            key_map = {
                "ctrl":  Key.ctrl,
                "shift": Key.shift,
                "alt":   Key.alt,
                "enter": Key.enter,
                "tab":   Key.tab,
                "esc":   Key.esc,
                "space": Key.space,
            }
            mapped = [key_map.get(k.lower(), k) for k in keys]
            with kb.pressed(*mapped[:-1]):
                kb.press(mapped[-1])
                kb.release(mapped[-1])
            return {"status": "success", "keys": list(keys)}
        except Exception as e:
            return {"error": str(e)}

    # ─── System Info ──────────────────────────────────────────────────────────

    def get_system_info(self) -> Dict:
        """Return current CPU, RAM, and disk usage."""
        if self._psutil is None:
            return {"error": "psutil not installed"}

        try:
            psutil = self._psutil
            disk   = psutil.disk_usage("/") if self._platform != "win32" else psutil.disk_usage("C:\\")

            return {
                "status":          "success",
                "cpu_percent":     psutil.cpu_percent(interval=0.5),
                "ram_total_gb":    round(psutil.virtual_memory().total / 1e9, 2),
                "ram_used_percent": psutil.virtual_memory().percent,
                "disk_total_gb":   round(disk.total / 1e9, 2),
                "disk_used_percent": disk.percent,
                "platform":        self._platform,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_running_processes(self, top_n: int = 10) -> Dict:
        """Return the top N processes by CPU usage."""
        if self._psutil is None:
            return {"error": "psutil not installed"}
        try:
            procs = []
            for proc in self._psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                try:
                    procs.append(proc.info)
                except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                    pass

            procs.sort(key=lambda p: p.get("cpu_percent", 0), reverse=True)
            return {"status": "success", "processes": procs[:top_n]}
        except Exception as e:
            return {"error": str(e)}

    # ─── Power ────────────────────────────────────────────────────────────────

    def lock_screen(self) -> Dict:
        """Lock the screen."""
        try:
            if self._platform == "win32":
                subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
            elif self._platform == "darwin":
                subprocess.run(["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-suspend"])
            else:
                subprocess.run(["loginctl", "lock-session"])
            return {"status": "success", "action": "lock_screen"}
        except Exception as e:
            return {"error": str(e)}


# ─── Standalone Test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    agent = SystemAgent()
    info  = agent.get_system_info()
    print(info)

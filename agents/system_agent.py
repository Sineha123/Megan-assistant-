"""
System Agent - Full OS-level controls for MEGAN
Covers: volume, brightness, open apps, open files, run CMD commands,
        VS Code / editor integration, system info, lock/power, media keys
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional


class SystemAgent:
    """
    System Control Agent for MEGAN.

    Capabilities:
    - Set/get system volume
    - Set/get screen brightness
    - Open any application by name or path
    - Open any file with default or specified app
    - Open project/folder in VS Code / any editor
    - Run CMD / PowerShell commands
    - Media controls (play/pause, next, prev, mute)
    - Get system information (CPU, RAM, disk, battery)
    - Running processes
    - Lock screen
    - Shutdown / restart (with confirmation)
    """

    # ── App aliases for Windows ────────────────────────────────────────────────
    WIN_ALIASES: Dict[str, str] = {
        # Browsers
        "chrome":       "chrome",
        "google chrome":"chrome",
        "firefox":      "firefox",
        "edge":         "msedge",
        "brave":        "brave",
        # Editors
        "vscode":       "code",
        "vs code":      "code",
        "visual studio code": "code",
        "code":         "code",
        "sublime":      "subl",
        "atom":         "atom",
        "notepad":      "notepad",
        "notepad++":    "notepad++",
        # System
        "explorer":     "explorer",
        "file explorer":"explorer",
        "files":        "explorer",
        "calculator":   "calc",
        "calc":         "calc",
        "paint":        "mspaint",
        "task manager": "taskmgr",
        "taskmgr":      "taskmgr",
        "control panel":"control",
        "settings":     "ms-settings:",
        "device manager":"devmgmt.msc",
        "registry":     "regedit",
        # Office
        "word":         "winword",
        "excel":        "excel",
        "powerpoint":   "powerpnt",
        "outlook":      "outlook",
        # Terminal
        "cmd":          "cmd",
        "command prompt":"cmd",
        "terminal":     "wt",        # Windows Terminal (falls back to cmd)
        "powershell":   "powershell",
        "pwsh":         "pwsh",
        # Media
        "vlc":          "vlc",
        "spotify":      "spotify",
        "itunes":       "itunes",
        # Comms
        "teams":        "teams",
        "zoom":         "zoom",
        "discord":      "discord",
        "whatsapp":     "WhatsApp",
        "telegram":     "telegram",
        # Dev
        "git bash":     "git-bash",
        "postman":      "postman",
        "docker":       "docker desktop",
        "android studio":"studio64",
    }

    def __init__(self):
        self._platform = sys.platform          # 'win32', 'darwin', 'linux'
        self._pynput   = None
        self._psutil   = None
        self._sbc      = None
        self._init_modules()

    def _init_modules(self):
        """Lazy-load optional system modules."""
        try:
            import pynput.keyboard as kb
            self._pynput = kb
            print("[SYSTEM] pynput ready")
        except ImportError:
            print("[SYSTEM] WARN: pynput not installed -- keyboard typing disabled")

        try:
            import psutil
            self._psutil = psutil
            print("[SYSTEM] psutil ready")
        except ImportError:
            print("[SYSTEM] WARN: psutil not installed -- system info limited")

        try:
            import screen_brightness_control as sbc
            self._sbc = sbc
            print("[SYSTEM] screen_brightness_control ready")
        except ImportError:
            print("[SYSTEM] WARN: screen_brightness_control not installed -- using WMI fallback")

    # =========================================================================
    # VOLUME
    # =========================================================================

    def set_volume(self, level: int) -> Dict:
        """Set system volume 0-100."""
        level = max(0, min(100, int(level)))
        print(f"[SYSTEM] Setting volume to {level}%")

        # Primary: pycaw (Windows)
        if self._platform == "win32":
            try:
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                import math

                devices   = AudioUtilities.GetSpeakers()
                volume    = devices.EndpointVolume
                scalar    = level / 100.0
                volume.SetMasterVolumeLevelScalar(scalar, None)
                return {"status": "success", "volume": level, "method": "pycaw"}
            except Exception as e:
                print(f"[SYSTEM] pycaw SetVolume failed: {e}")
                pass

            # Fallback: nircmd (if installed)
            try:
                subprocess.run(
                    ["nircmd", "setsysvolume", str(int(level / 100 * 65535))],
                    capture_output=True, check=True
                )
                return {"status": "success", "volume": level, "method": "nircmd"}
            except Exception:
                pass

            # Fallback: PowerShell WScript SendKeys (basic mute toggle)
            try:
                ps = (
                    f"$wsh = New-Object -ComObject WScript.Shell; "
                    f"$vol = [math]::Round({level} / 100 * 65535);"
                    f"Add-Type -TypeDefinition '"
                    f"public class V {{"
                    f"[System.Runtime.InteropServices.DllImport(\"winmm.dll\")]"
                    f"public static extern int waveOutSetVolume(System.IntPtr h, uint d);"
                    f"}}' -Language CSharp; "
                    f"[V]::waveOutSetVolume([System.IntPtr]::Zero, ($vol * 65536 + $vol));"
                )
                subprocess.run(["powershell", "-Command", ps], capture_output=True)
                return {"status": "success", "volume": level, "method": "powershell_winmm"}
            except Exception as e:
                return {"error": f"Volume control failed: {e}"}

        elif self._platform == "darwin":
            subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=True)
            return {"status": "success", "volume": level}

        else:
            subprocess.run(["amixer", "-q", "sset", "Master", f"{level}%"], check=True)
            return {"status": "success", "volume": level}

    def get_volume(self) -> Dict:
        """Get current system volume."""
        if self._platform == "win32":
            try:
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                import math

                devices   = AudioUtilities.GetSpeakers()
                volume    = devices.EndpointVolume
                scalar    = volume.GetMasterVolumeLevelScalar()
                pct       = int(scalar * 100)
                return {"status": "success", "volume": pct}
            except Exception as e:
                return {"error": str(e)}
        return {"error": "get_volume only implemented for Windows"}

    def mute(self, mute_state: bool = True) -> Dict:
        """Mute or unmute the system audio."""
        if self._platform == "win32":
            try:
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

                devices   = AudioUtilities.GetSpeakers()
                volume    = devices.EndpointVolume
                volume.SetMute(1 if mute_state else 0, None)
                return {"status": "success", "muted": mute_state}
            except Exception as e:
                return {"error": str(e)}
        elif self._platform == "darwin":
            state = "true" if mute_state else "false"
            subprocess.run(["osascript", "-e", f"set volume output muted {state}"])
            return {"status": "success", "muted": mute_state}
        return {"error": "Not supported on this platform"}

    # =========================================================================
    # BRIGHTNESS
    # =========================================================================

    def set_brightness(self, level: int) -> Dict:
        """Set screen brightness 0-100."""
        level = max(0, min(100, int(level)))
        print(f"[SYSTEM] Setting brightness to {level}%")

        if self._sbc:
            try:
                self._sbc.set_brightness(level)
                return {"status": "success", "brightness": level, "method": "sbc"}
            except Exception as e:
                print(f"[SYSTEM] sbc failed: {e}, trying WMI...")

        if self._platform == "win32":
            try:
                cmd = (
                    f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                    f".WmiSetBrightness(1,{level})"
                )
                r = subprocess.run(
                    ["powershell", "-Command", cmd],
                    capture_output=True, timeout=5
                )
                if r.returncode == 0:
                    return {"status": "success", "brightness": level, "method": "wmi"}
                return {"error": r.stderr.decode(errors="replace")}
            except Exception as e:
                return {"error": str(e)}

        return {"error": "screen_brightness_control not installed and no WMI fallback"}

    def get_brightness(self) -> Dict:
        """Get current screen brightness."""
        if self._sbc:
            try:
                b = self._sbc.get_brightness(display=0)
                return {"status": "success", "brightness": b[0] if isinstance(b, list) else b}
            except Exception as e:
                return {"error": str(e)}

        if self._platform == "win32":
            try:
                cmd = "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"
                r = subprocess.run(
                    ["powershell", "-Command", cmd],
                    capture_output=True, timeout=5
                )
                val = r.stdout.decode(errors="replace").strip()
                return {"status": "success", "brightness": int(val) if val.isdigit() else val}
            except Exception as e:
                return {"error": str(e)}

        return {"error": "Not supported"}

    # =========================================================================
    # APPLICATION LAUNCHING
    # =========================================================================

    def open_application(self, app: str, args: Optional[List[str]] = None) -> Dict:
        """
        Open an application by name or alias.
        Handles 50+ common apps via alias table + fallback shell launch.
        """
        print(f"[SYSTEM] Opening application: {app}")
        args = args or []
        cmd  = self.WIN_ALIASES.get(app.lower().strip(), app) if self._platform == "win32" else app

        try:
            if self._platform == "win32":
                # For special ms-settings: URIs
                if cmd.startswith("ms-"):
                    subprocess.Popen(f"start {cmd}", shell=True)
                elif cmd.endswith(".msc") or cmd in ("regedit", "taskmgr", "control"):
                    subprocess.Popen(["cmd", "/c", "start", cmd] + args, shell=False)
                else:
                    subprocess.Popen([cmd] + args, shell=True)
            elif self._platform == "darwin":
                subprocess.Popen(["open", "-a", app] + args)
            else:
                subprocess.Popen([cmd] + args)

            return {"status": "success", "app": app, "cmd": cmd}

        except FileNotFoundError:
            return {"error": f"Application not found: {app}. Check if it's installed and in PATH."}
        except Exception as e:
            return {"error": str(e)}

    def open_file(self, file_path: str, app: Optional[str] = None) -> Dict:
        """
        Open a file with its default application, or with a specified app.

        Examples:
            open_file("C:/Users/PMLS/report.pdf")
            open_file("main.py", app="code")
            open_file("project_folder", app="code")
        """
        print(f"[SYSTEM] Opening file: {file_path}" + (f" with {app}" if app else ""))

        # Expand ~ and env variables
        file_path = os.path.expandvars(os.path.expanduser(file_path))

        if not os.path.exists(file_path):
            return {"error": f"File/folder not found: {file_path}"}

        try:
            if app:
                app_cmd = self.WIN_ALIASES.get(app.lower(), app)
                subprocess.Popen([app_cmd, file_path], shell=False)
            else:
                if self._platform == "win32":
                    os.startfile(file_path)
                elif self._platform == "darwin":
                    subprocess.Popen(["open", file_path])
                else:
                    subprocess.Popen(["xdg-open", file_path])

            return {"status": "success", "file": file_path, "opened_with": app or "default"}

        except Exception as e:
            # Try shell=True fallback on Windows
            if self._platform == "win32":
                try:
                    subprocess.Popen(f'"{file_path}"', shell=True)
                    return {"status": "success", "file": file_path, "method": "shell"}
                except Exception:
                    pass
            return {"error": str(e)}

    def open_in_vscode(self, path: str, new_window: bool = False) -> Dict:
        """
        Open a file or folder in VS Code.

        Args:
            path:       File or folder path
            new_window: Open in a new VS Code window
        """
        path = os.path.expandvars(os.path.expanduser(path))
        if not os.path.exists(path):
            return {"error": f"Path not found: {path}"}

        args = ["code"]
        if new_window:
            args.append("--new-window")
        args.append(path)

        try:
            subprocess.Popen(args, shell=True)
            return {"status": "success", "path": path, "editor": "VS Code"}
        except Exception as e:
            return {"error": f"VS Code not found or failed: {e}. Is 'code' in PATH?"}

    def open_in_editor(self, path: str, editor: str = "vscode") -> Dict:
        """Open a file/folder in any editor (vscode, notepad, sublime, atom, etc.)"""
        editor_map = {
            "vscode":   ["code"],
            "vs code":  ["code"],
            "sublime":  ["subl"],
            "atom":     ["atom"],
            "notepad":  ["notepad"],
            "notepad++": ["notepad++"],
            "vim":      ["vim"],
            "nano":     ["nano"],
            "gedit":    ["gedit"],
        }
        cmd = editor_map.get(editor.lower(), [editor])
        path = os.path.expandvars(os.path.expanduser(path))

        if not os.path.exists(path):
            return {"error": f"Path not found: {path}"}

        try:
            subprocess.Popen(cmd + [path], shell=True)
            return {"status": "success", "path": path, "editor": editor}
        except Exception as e:
            return {"error": str(e)}

    def open_folder(self, path: str) -> Dict:
        """Open a folder in File Explorer / Finder."""
        path = os.path.expandvars(os.path.expanduser(path))
        if not os.path.exists(path):
            return {"error": f"Folder not found: {path}"}
        try:
            if self._platform == "win32":
                subprocess.Popen(["explorer", path])
            elif self._platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
            return {"status": "success", "folder": path}
        except Exception as e:
            return {"error": str(e)}

    # =========================================================================
    # CMD / TERMINAL COMMANDS
    # =========================================================================

    def run_command(
        self,
        command: str,
        working_dir: Optional[str] = None,
        timeout: int = 30,
        open_new_window: bool = False,
    ) -> Dict:
        """
        Run a shell command and return its output.

        Args:
            command:         Shell command string
            working_dir:     Directory to run from (default: current dir)
            timeout:         Max seconds to wait (default: 30)
            open_new_window: If True, open in a visible new CMD window

        Returns:
            {status, stdout, stderr, returncode}
        """
        print(f"[SYSTEM] Running command: {command}")

        if open_new_window:
            return self._run_in_new_terminal(command, working_dir)

        try:
            cwd = os.path.expandvars(os.path.expanduser(working_dir)) if working_dir else None

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                encoding="utf-8",
                errors="replace",
            )
            return {
                "status":     "success" if result.returncode == 0 else "error",
                "stdout":     result.stdout.strip(),
                "stderr":     result.stderr.strip(),
                "returncode": result.returncode,
                "command":    command,
            }

        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {timeout}s", "command": command}
        except Exception as e:
            return {"error": str(e), "command": command}

    def _run_in_new_terminal(self, command: str, working_dir: Optional[str] = None) -> Dict:
        """Open a new CMD/Terminal window and run the command visibly."""
        cwd = os.path.expandvars(os.path.expanduser(working_dir)) if working_dir else None

        try:
            if self._platform == "win32":
                # /K keeps the window open after the command finishes
                full_cmd = f'start cmd /K "{command}"'
                subprocess.Popen(full_cmd, shell=True, cwd=cwd)
            elif self._platform == "darwin":
                script = f'tell app "Terminal" to do script "{command}"'
                subprocess.Popen(["osascript", "-e", script])
            else:
                subprocess.Popen(
                    ["x-terminal-emulator", "-e", f"bash -c '{command}; bash'"],
                    cwd=cwd
                )
            return {"status": "success", "command": command, "mode": "new_window"}
        except Exception as e:
            return {"error": str(e)}

    def open_cmd(self, path: Optional[str] = None) -> Dict:
        """Open CMD in a specific directory."""
        cwd = path or os.path.expanduser("~")
        cwd = os.path.expandvars(os.path.expanduser(cwd))
        try:
            if self._platform == "win32":
                subprocess.Popen(["cmd"], cwd=cwd if os.path.exists(cwd) else None)
            elif self._platform == "darwin":
                subprocess.Popen(["open", "-a", "Terminal", cwd])
            else:
                subprocess.Popen(["x-terminal-emulator"], cwd=cwd)
            return {"status": "success", "path": cwd}
        except Exception as e:
            return {"error": str(e)}

    def open_powershell(self, path: Optional[str] = None) -> Dict:
        """Open PowerShell in a specific directory."""
        cwd = path or os.path.expanduser("~")
        cwd = os.path.expandvars(os.path.expanduser(cwd))
        try:
            subprocess.Popen(
                ["powershell", "-NoExit", "-Command", f"Set-Location '{cwd}'"],
                creationflags=subprocess.CREATE_NEW_CONSOLE if self._platform == "win32" else 0
            )
            return {"status": "success", "path": cwd}
        except Exception as e:
            return {"error": str(e)}

    # =========================================================================
    # KEYBOARD INPUT
    # =========================================================================

    def type_text(self, text: str) -> Dict:
        """Type text as keyboard input."""
        if self._pynput is None:
            return {"error": "pynput not installed"}
        try:
            controller = self._pynput.Controller()
            controller.type(text)
            return {"status": "success", "characters_typed": len(text)}
        except Exception as e:
            return {"error": str(e)}

    def press_keys(self, *keys) -> Dict:
        """Press a key combination e.g. ('ctrl', 'c')."""
        if self._pynput is None:
            return {"error": "pynput not installed"}
        try:
            from pynput.keyboard import Key, Controller
            kb      = Controller()
            key_map = {
                "ctrl":  Key.ctrl, "shift": Key.shift, "alt": Key.alt,
                "enter": Key.enter, "tab":  Key.tab,   "esc": Key.esc,
                "space": Key.space, "win":  Key.cmd,   "delete": Key.delete,
                "home":  Key.home,  "end":  Key.end,   "f5": Key.f5,
            }
            mapped = [key_map.get(k.lower(), k) for k in keys]
            with kb.pressed(*mapped[:-1]):
                kb.press(mapped[-1])
                kb.release(mapped[-1])
            return {"status": "success", "keys": list(keys)}
        except Exception as e:
            return {"error": str(e)}

    # =========================================================================
    # MEDIA CONTROLS
    # =========================================================================

    def media_control(self, action: str) -> Dict:
        """
        Control media playback.
        action: play_pause | next | prev | mute | volume_up | volume_down
        """
        print(f"[SYSTEM] Media control: {action}")

        if self._platform == "win32":
            # Virtual key codes for media keys
            VK_MAP = {
                "play_pause":  0xB3,
                "next":        0xB0,
                "prev":        0xB1,
                "stop":        0xB2,
                "mute":        0xAD,
                "volume_up":   0xAF,
                "volume_down": 0xAE,
            }
            vk = VK_MAP.get(action)
            if vk:
                try:
                    import ctypes
                    KEYEVENTF_EXTENDEDKEY = 0x0001
                    KEYEVENTF_KEYUP       = 0x0002
                    ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY, 0)
                    ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                    return {"status": "success", "action": action}
                except Exception as e:
                    return {"error": str(e)}
            return {"error": f"Unknown media action: {action}"}

        elif self._platform == "darwin":
            key_map = {
                "play_pause": "play", "next": "fast forward", "prev": "rewind"
            }
            key = key_map.get(action)
            if key:
                subprocess.run(["osascript", "-e", f"tell application \"Music\" to {key}"])
                return {"status": "success", "action": action}

        return {"error": "Media control not supported on this platform"}

    # =========================================================================
    # SYSTEM INFO
    # =========================================================================

    def get_system_info(self) -> Dict:
        """Return CPU, RAM, disk, battery, and platform info."""
        if self._psutil is None:
            # Minimal fallback without psutil
            import platform
            return {
                "status":   "limited",
                "platform": sys.platform,
                "python":   platform.python_version(),
                "machine":  platform.machine(),
                "note":     "Install psutil for full system info",
            }

        ps = self._psutil
        try:
            disk = ps.disk_usage("C:\\") if self._platform == "win32" else ps.disk_usage("/")
            info = {
                "status":            "success",
                "cpu_percent":       ps.cpu_percent(interval=0.5),
                "cpu_cores":         ps.cpu_count(),
                "ram_total_gb":      round(ps.virtual_memory().total  / 1e9, 2),
                "ram_used_gb":       round(ps.virtual_memory().used   / 1e9, 2),
                "ram_used_percent":  ps.virtual_memory().percent,
                "disk_total_gb":     round(disk.total / 1e9, 2),
                "disk_used_gb":      round(disk.used  / 1e9, 2),
                "disk_used_percent": disk.percent,
                "platform":          self._platform,
            }
            # Battery (laptops)
            try:
                bat = ps.sensors_battery()
                if bat:
                    info["battery_percent"] = bat.percent
                    info["battery_charging"] = bat.power_plugged
            except Exception:
                pass
            return info
        except Exception as e:
            return {"error": str(e)}

    def get_running_processes(self, top_n: int = 10, sort_by: str = "cpu") -> Dict:
        """Return top N processes sorted by cpu or memory."""
        if self._psutil is None:
            return {"error": "psutil not installed"}
        try:
            procs = []
            for proc in self._psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                try:
                    procs.append(proc.info)
                except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                    pass
            key = "cpu_percent" if sort_by == "cpu" else "memory_percent"
            procs.sort(key=lambda p: p.get(key, 0), reverse=True)
            return {"status": "success", "processes": procs[:top_n]}
        except Exception as e:
            return {"error": str(e)}

    def kill_process(self, name_or_pid) -> Dict:
        """Kill a process by name or PID."""
        if self._psutil is None:
            return {"error": "psutil not installed"}
        try:
            killed = []
            for proc in self._psutil.process_iter(["pid", "name"]):
                try:
                    if str(proc.info["pid"]) == str(name_or_pid) or \
                       proc.info["name"].lower() == str(name_or_pid).lower():
                        proc.kill()
                        killed.append(proc.info["name"])
                except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                    pass
            if killed:
                return {"status": "success", "killed": killed}
            return {"error": f"Process not found: {name_or_pid}"}
        except Exception as e:
            return {"error": str(e)}

    # =========================================================================
    # POWER / SCREEN
    # =========================================================================

    def lock_screen(self) -> Dict:
        """Lock the screen."""
        try:
            if self._platform == "win32":
                subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
            elif self._platform == "darwin":
                subprocess.run([
                    "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession",
                    "-suspend"
                ])
            else:
                subprocess.run(["loginctl", "lock-session"])
            return {"status": "success", "action": "lock_screen"}
        except Exception as e:
            return {"error": str(e)}

    def shutdown(self, confirm: bool = False, restart: bool = False) -> Dict:
        """Shutdown or restart (requires confirm=True)."""
        if not confirm:
            action = "restart" if restart else "shutdown"
            return {"status": "needs_confirmation", "message": f"Are you sure you want to {action}?"}
        try:
            if self._platform == "win32":
                if restart:
                    subprocess.run(["shutdown", "/r", "/t", "5"])
                else:
                    subprocess.run(["shutdown", "/s", "/t", "5"])
            elif self._platform == "darwin":
                cmd = "restart" if restart else "shut down"
                subprocess.run(["osascript", "-e", f'tell app "System Events" to {cmd}'])
            else:
                subprocess.run(["systemctl", "reboot" if restart else "poweroff"])
            action = "restarting" if restart else "shutting down"
            return {"status": "success", "action": action}
        except Exception as e:
            return {"error": str(e)}

    def sleep(self) -> Dict:
        """Put the computer to sleep."""
        try:
            if self._platform == "win32":
                subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            elif self._platform == "darwin":
                subprocess.run(["pmset", "sleepnow"])
            else:
                subprocess.run(["systemctl", "suspend"])
            return {"status": "success", "action": "sleep"}
        except Exception as e:
            return {"error": str(e)}

    # =========================================================================
    # CLIPBOARD
    # =========================================================================

    def set_clipboard(self, text: str) -> Dict:
        """Copy text to clipboard."""
        try:
            if self._platform == "win32":
                subprocess.run(["clip"], input=text.encode("utf-8"), check=True)
            elif self._platform == "darwin":
                subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
            else:
                subprocess.run(["xclip", "-selection", "clipboard"],
                                input=text.encode("utf-8"), check=True)
            return {"status": "success", "characters": len(text)}
        except Exception as e:
            return {"error": str(e)}

    def get_clipboard(self) -> Dict:
        """Get clipboard text."""
        try:
            if self._platform == "win32":
                r = subprocess.run(
                    ["powershell", "-Command", "Get-Clipboard"],
                    capture_output=True, text=True
                )
                return {"status": "success", "text": r.stdout.strip()}
            elif self._platform == "darwin":
                r = subprocess.run(["pbpaste"], capture_output=True, text=True)
                return {"status": "success", "text": r.stdout}
            else:
                r = subprocess.run(["xclip", "-selection", "clipboard", "-o"],
                                    capture_output=True, text=True)
                return {"status": "success", "text": r.stdout}
        except Exception as e:
            return {"error": str(e)}


# ─── Standalone Test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    agent = SystemAgent()

    print("\n--- System Info ---")
    print(agent.get_system_info())

    print("\n--- Volume set 50 ---")
    print(agent.set_volume(50))

    print("\n--- Brightness set 70 ---")
    print(agent.set_brightness(70))

    print("\n--- Open Notepad ---")
    print(agent.open_application("notepad"))

    print("\n--- Run command: echo Hello ---")
    print(agent.run_command("echo Hello MEGAN!"))

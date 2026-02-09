"""
Let Me Sleep - Detect applications preventing Windows from sleeping.
Shows blocking applications in the system tray with a modern GUI.

Icon attribution: Sleep icons created by Freepik - Flaticon
https://www.flaticon.com/free-icons/sleep
"""

import subprocess
import threading
import time
import re
import sys
import ctypes
import os
import tkinter as tk
from dataclasses import dataclass
from typing import Optional

import pystray
from PIL import Image, ImageDraw, ImageFont, ImageTk
import customtkinter as ctk

from i18n import t
import scheduler


SINGLE_INSTANCE_MUTEX_NAME = "Local\\LetMeSleep.SingleInstance"
SHOW_GUI_EVENT_NAME = "Local\\LetMeSleep.ShowGui"
ERROR_ALREADY_EXISTS = 183
WAIT_OBJECT_0 = 0
EVENT_MODIFY_STATE = 0x0002

_single_instance_mutex_handle = None


def acquire_single_instance() -> bool:
    """Return True when this process is the primary instance."""
    global _single_instance_mutex_handle
    handle = ctypes.windll.kernel32.CreateMutexW(
        None, False, SINGLE_INSTANCE_MUTEX_NAME
    )
    if not handle:
        return True
    _single_instance_mutex_handle = handle
    return ctypes.windll.kernel32.GetLastError() != ERROR_ALREADY_EXISTS


def signal_existing_instance_show_gui() -> bool:
    """Signal the running instance to open/show its GUI window."""
    for _ in range(20):
        event_handle = ctypes.windll.kernel32.OpenEventW(
            EVENT_MODIFY_STATE, False, SHOW_GUI_EVENT_NAME
        )
        if event_handle:
            try:
                return bool(ctypes.windll.kernel32.SetEvent(event_handle))
            finally:
                ctypes.windll.kernel32.CloseHandle(event_handle)
        time.sleep(0.1)
    return False


def is_admin() -> bool:
    """Check if running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    """Relaunch the script with admin privileges."""
    script = sys.argv[0]
    params = " ".join(sys.argv[1:])

    is_packaged_runtime = (
        getattr(sys, "frozen", False) or globals().get("__compiled__") is not None
    )

    if is_packaged_runtime:
        exe = os.path.abspath(script)
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            exe,
            params,
            None,
            1,
        )
        return ret > 32

    # Use pythonw.exe if available to avoid console window
    python = sys.executable
    if python.endswith("python.exe"):
        pythonw = python.replace("python.exe", "pythonw.exe")
        if os.path.exists(pythonw):
            python = pythonw

    # ShellExecute with "runas" verb for UAC elevation
    ret = ctypes.windll.shell32.ShellExecuteW(
        None,  # hwnd
        "runas",  # operation (run as admin)
        python,  # executable
        f'"{script}" {params}',  # parameters
        None,  # directory
        1,  # show window
    )

    # ShellExecute returns > 32 on success
    return ret > 32


@dataclass
class PowerRequest:
    """Represents a power request blocking sleep."""

    category: str
    process: str
    pid: str
    reason: str


def get_power_requests() -> tuple[list[PowerRequest], str | None]:
    """
    Run powercfg /requests and parse the output.
    Returns (requests, error_message).
    """
    try:
        result = subprocess.run(
            ["powercfg", "/requests"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        if "administrator" in result.stderr.lower():
            return [], "Requires administrator privileges"

        output = result.stdout
    except Exception as e:
        return [], str(e)

    requests = []
    current_category = None
    sleep_categories = {"DISPLAY", "SYSTEM", "AWAYMODE"}

    lines = output.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.endswith(":") and line[:-1] in sleep_categories:
            current_category = line[:-1]
        elif current_category and line and line != "None.":
            process_match = re.match(r"\[(\w+)\]\s*(.+)", line)
            if process_match:
                req_type = process_match.group(1)
                process_path = process_match.group(2).strip()

                reason = ""
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if (
                        next_line
                        and not next_line.endswith(":")
                        and not next_line.startswith("[")
                    ):
                        reason = next_line
                        i += 1

                process_name = get_friendly_name(process_path, req_type)
                pid = find_pid_by_name(process_name) if req_type == "PROCESS" else ""

                requests.append(
                    PowerRequest(
                        category=current_category,
                        process=process_name,
                        pid=pid,
                        reason=reason,
                    )
                )

        if not line:
            current_category = None
        i += 1

    return requests, None


def get_friendly_name(path: str, req_type: str) -> str:
    """Convert a device path or process path to a friendly name."""
    # Known driver/device mappings (key -> i18n key)
    known_names = {
        "srvnet": "smb_network_share",
        "hdaudio": "audio_device",
        "usbhub": "usb_hub",
        "usbxhci": "usb_controller",
        "intelppm": "intel_power_mgmt",
        "amdppm": "amd_power_mgmt",
        "acpi": "acpi_power",
        "ntfs": "ntfs_filesystem",
    }

    # For processes, extract just the exe name
    if req_type == "PROCESS":
        if "\\" in path:
            return path.split("\\")[-1]
        return path

    # For drivers, try to get a friendly name
    path_lower = path.lower()

    # Check known names
    for key, i18n_key in known_names.items():
        if key in path_lower:
            return t(i18n_key)

    # If it's a hardware ID (contains & and numbers), use a generic name based on type
    if "&" in path and any(c.isdigit() for c in path):
        if "hdaudio" in path_lower or "audio" in path_lower:
            return t("audio_device")
        if "usb" in path_lower:
            return t("usb_device")
        if "pci" in path_lower:
            return t("pci_device")
        if "hid" in path_lower:
            return t("input_device")
        # For unrecognized hardware IDs, show a cleaner name
        return t("hardware_device")

    # Extract last component for file system paths
    if "\\" in path:
        name = path.split("\\")[-1]
        # If it still looks like garbage, clean it up
        if name and not any(c.isdigit() for c in name[:3]):
            return name

    # Legacy Kernel Caller is common
    if "legacy kernel caller" in path_lower:
        return t("legacy_kernel_caller")

    return path if len(path) < 30 else path[:27] + "..."


def find_pid_by_name(process_name: str) -> str:
    """Find PID of a process by name."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for line in result.stdout.strip().split("\n"):
            if line and process_name.lower() in line.lower():
                parts = line.replace('"', "").split(",")
                if len(parts) >= 2:
                    return parts[1]
    except:
        pass
    return ""


def kill_process(pid: str) -> bool:
    """Kill a process by PID."""
    if not pid:
        return False
    try:
        result = subprocess.run(
            ["taskkill", "/PID", pid, "/F"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.returncode == 0
    except:
        return False


def get_icon_path(filename: str = "icon.png") -> str:
    """Resolve icon path for source run vs PyInstaller run."""
    meipass_dir = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and meipass_dir:
        # PyInstaller onefile/onedir extraction directory
        return os.path.join(meipass_dir, filename)

    # Direct Python run: keep path relative to this script directory
    script_relative = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    if os.path.exists(script_relative):
        return script_relative

    # Fallback to current working directory
    return os.path.join(os.getcwd(), filename)


def set_windows_app_id():
    """Set explicit Windows AppUserModelID for stable taskbar icon behavior."""
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "CYTsai.LetMeSleep"
        )
    except Exception:
        pass


def apply_window_icon(window):
    """Apply window icon using ico/png with broad Tk compatibility."""
    if getattr(sys, "frozen", False):
        try:
            window.iconbitmap(default=sys.executable)
        except Exception:
            pass

    ico_path = get_icon_path("icon.ico")
    if os.path.exists(ico_path):
        try:
            window.iconbitmap(default=ico_path)
        except Exception:
            pass

    png_path = get_icon_path("icon.png")
    if os.path.exists(png_path):
        try:
            resampling = getattr(Image, "Resampling", Image)
            lanczos = getattr(resampling, "LANCZOS")
            src = Image.open(png_path).convert("RGBA")
            large_icon = ImageTk.PhotoImage(src.resize((32, 32), lanczos))
            small_icon = ImageTk.PhotoImage(src.resize((16, 16), lanczos))
            window.iconphoto(False, large_icon, small_icon)
            return (large_icon, small_icon)
        except Exception:
            return None

    return None


def create_icon_image(actionable_count: int, has_error: bool = False) -> Image.Image:
    """Create a system tray icon. Only actionable items count as blocking."""
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    if has_error:
        draw.ellipse([4, 4, size - 4, size - 4], fill=(128, 128, 128, 255))
        text = "!"
    elif actionable_count == 0:
        draw.ellipse([4, 4, size - 4, size - 4], fill=(76, 175, 80, 255))
        text = "0"
    else:
        draw.ellipse([4, 4, size - 4, size - 4], fill=(244, 67, 54, 255))
        text = str(actionable_count) if actionable_count < 10 else "9+"

    try:
        font = ImageFont.truetype("arial.ttf", 32 if len(text) == 1 else 28)
    except:
        font = ImageFont.load_default()
    draw.text((size // 2, size // 2), text, fill="white", anchor="mm", font=font)

    return image


class ProcessCard(ctk.CTkFrame):
    """A card showing a single blocking process."""

    def __init__(self, master, request: PowerRequest, on_kill_callback):
        super().__init__(master, corner_radius=8)
        self.request = request
        self.on_kill_callback = on_kill_callback

        self.configure(fg_color=("gray90", "gray17"))

        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        name_label = ctk.CTkLabel(
            info_frame,
            text=request.process,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        name_label.pack(fill="x")

        details = f"{request.category}"
        if request.reason:
            details += f" • {request.reason[:50]}"

        detail_label = ctk.CTkLabel(
            info_frame,
            text=details,
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
            anchor="w",
        )
        detail_label.pack(fill="x")

        if request.pid:
            kill_btn = ctk.CTkButton(
                self,
                text=t("end_task"),
                width=80,
                height=32,
                corner_radius=6,
                fg_color=("#dc3545", "#dc3545"),
                hover_color=("#bb2d3b", "#bb2d3b"),
                command=self.on_kill,
            )
            kill_btn.pack(side="right", padx=12, pady=10)
        else:
            driver_label = ctk.CTkLabel(
                self,
                text=t("driver"),
                font=ctk.CTkFont(size=10),
                text_color=("gray50", "gray50"),
            )
            driver_label.pack(side="right", padx=12, pady=10)

    def on_kill(self):
        if kill_process(self.request.pid):
            self.on_kill_callback()


class CollapsibleSection(ctk.CTkFrame):
    """A collapsible section with header and content."""

    def __init__(
        self, master, title: str, count: int, expanded: bool = False, on_toggle=None
    ):
        super().__init__(master, fg_color="transparent")
        self.expanded = expanded
        self.on_toggle = on_toggle

        # Header button
        self.header = ctk.CTkButton(
            self,
            text=f"{'▼' if expanded else '▶'}  {title} ({count})",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            text_color=("gray40", "gray60"),
            anchor="w",
            height=32,
            command=self.toggle,
        )
        self.header.pack(fill="x")

        # Content frame
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        if expanded:
            self.content.pack(fill="x", padx=(16, 0))

    def toggle(self):
        self.expanded = not self.expanded
        title = self.header.cget("text")
        # Update arrow
        if self.expanded:
            self.header.configure(text="▼" + title[1:])
            self.content.pack(fill="x", padx=(16, 0))
        else:
            self.header.configure(text="▶" + title[1:])
            self.content.pack_forget()
        # Notify parent
        if self.on_toggle:
            self.on_toggle(self.expanded)

    def add_widget(self, widget_class, **kwargs):
        """Add a widget to the content area."""
        return widget_class(self.content, **kwargs)


class MainWindow(ctk.CTkToplevel):
    """Main GUI window."""

    def __init__(self, monitor: "SleepMonitor"):
        super().__init__()
        self.monitor = monitor
        self.ignorable_expanded = False  # Track collapsible section state
        self._tk_icon_images = None

        self.title(t("app_name"))
        self.geometry("450x500")
        self.minsize(400, 300)

        self._tk_icon_images = apply_window_icon(self)

        # Hide instead of destroy on close
        self.protocol("WM_DELETE_WINDOW", self.hide)
        # CTkToplevel may override icon after ~200ms on Windows, apply ours later.
        self.after(350, self._apply_icon_late)

        self.create_widgets()
        self.update_ui()

    def _apply_icon_late(self):
        """Re-apply icon after CTk internal delayed icon set."""
        self._tk_icon_images = apply_window_icon(self)

    def create_widgets(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        title = ctk.CTkLabel(
            header, text=t("app_name"), font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(side="left")

        self.refresh_btn = ctk.CTkButton(
            header,
            text="↻",
            width=36,
            height=36,
            corner_radius=18,
            font=ctk.CTkFont(size=18),
            command=self.refresh,
        )
        self.refresh_btn.pack(side="right")

        # Status bar
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Checking...",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray60"),
        )
        self.status_label.pack(side="left")

        # Scrollable list
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def refresh(self):
        """Refresh data from monitor."""
        self.monitor.update()
        self.update_ui()

    def update_ui(self):
        """Update the UI with current data."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if self.monitor.error:
            self.status_label.configure(
                text=f"⚠ {self.monitor.error}", text_color=("#dc3545", "#dc3545")
            )
            error_label = ctk.CTkLabel(
                self.scroll_frame,
                text=t("run_as_admin"),
                font=ctk.CTkFont(size=14),
                text_color=("gray40", "gray60"),
                justify="center",
            )
            error_label.pack(pady=40)
            return

        if not self.monitor.requests:
            self.status_label.configure(
                text=f"✓ {t('ready_to_sleep')}", text_color=("#198754", "#20c997")
            )
            empty_label = ctk.CTkLabel(
                self.scroll_frame,
                text=f"✓ {t('no_apps_blocking')}\n{t('no_apps_blocking_desc')}",
                font=ctk.CTkFont(size=14),
                text_color=("gray40", "gray60"),
                justify="center",
            )
            empty_label.pack(pady=40)
        else:
            # Separate actionable (processes) from ignorable (drivers)
            actionable = [r for r in self.monitor.requests if r.pid]
            ignorable = [r for r in self.monitor.requests if not r.pid]

            self.status_label.configure(
                text=f"⚠ {t('n_apps_blocking', n=len(self.monitor.requests))}",
                text_color=("#dc3545", "#ff6b6b"),
            )

            # Show actionable items first
            for req in actionable:
                card = ProcessCard(self.scroll_frame, req, self.refresh)
                card.pack(fill="x", pady=4)

            # Show ignorable items in collapsed section
            if ignorable:
                if actionable:
                    # Add some spacing
                    spacer = ctk.CTkFrame(
                        self.scroll_frame, height=8, fg_color="transparent"
                    )
                    spacer.pack(fill="x")

                section = CollapsibleSection(
                    self.scroll_frame,
                    t("usually_safe_to_ignore"),
                    len(ignorable),
                    expanded=self.ignorable_expanded,
                    on_toggle=lambda exp: setattr(self, "ignorable_expanded", exp),
                )
                section.pack(fill="x", pady=4)

                for req in ignorable:
                    card = ProcessCard(section.content, req, self.refresh)
                    card.pack(fill="x", pady=2)

    def show(self):
        """Show the window."""
        self.update_ui()
        if self._tk_icon_images is None:
            self._tk_icon_images = apply_window_icon(self)
        self.deiconify()
        self.lift()
        self.focus_force()

    def hide(self):
        """Hide the window."""
        self.withdraw()


class SleepMonitor:
    """Monitors power requests and updates system tray."""

    def __init__(self):
        self.requests: list[PowerRequest] = []
        self.error: str | None = None
        self.icon: Optional[pystray.Icon] = None
        self.window: Optional[MainWindow] = None
        self.running = True
        self.update_interval = 10
        self.ctk_root: Optional[ctk.CTk] = None
        self._root_tk_icon_images = None
        self._show_gui_event_handle = None

    def get_menu(self) -> pystray.Menu:
        """Generate the context menu."""
        items = [
            pystray.MenuItem(t("open"), self.show_window, default=True),
            pystray.Menu.SEPARATOR,
        ]

        if self.error:
            items.append(
                pystray.MenuItem(f"⚠ {t('requires_admin')}", None, enabled=False)
            )
        elif not self.requests:
            items.append(
                pystray.MenuItem(f"✓ {t('no_apps_blocking')}", None, enabled=False)
            )
        else:
            actionable = [r for r in self.requests if r.pid]
            ignorable = [r for r in self.requests if not r.pid]
            items.append(
                pystray.MenuItem(
                    f"⚠ {t('n_apps_blocking', n=len(actionable))}",
                    None,
                    enabled=False,
                )
            )

            for req in actionable:
                label = f"  {req.process}"
                if req.reason:
                    label += f" - {req.reason[:30]}"
                items.append(pystray.MenuItem(label, None, enabled=False))

            if ignorable:
                items.append(
                    pystray.MenuItem(
                        f"  {t('usually_safe_to_ignore')} ({len(ignorable)})",
                        None,
                        enabled=False,
                    )
                )
                for req in ignorable:
                    label = f"    {req.process}"
                    if req.reason:
                        label += f" - {req.reason[:30]}"
                    items.append(pystray.MenuItem(label, None, enabled=False))

        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem(t("refresh"), self.manual_refresh))

        # Start with Windows toggle (checkbox) - requires scheduled task
        if scheduler.is_task_installed():
            items.append(
                pystray.MenuItem(
                    t("start_with_windows"),
                    self.toggle_autostart,
                    checked=lambda item: scheduler.is_autostart_enabled(),
                )
            )
            items.append(
                pystray.MenuItem(t("uninstall_service"), self.uninstall_service)
            )
        else:
            items.append(pystray.MenuItem(t("install_service"), self.install_service))

        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem(t("exit"), self.quit))

        return pystray.Menu(*items)

    def toggle_autostart(self, icon=None, item=None):
        """Toggle start with Windows (via scheduled task)."""
        if scheduler.is_admin():
            new_state = scheduler.toggle_autostart()
            status = t("enabled") if new_state else t("disabled")
            self.icon.notify(f"{t('start_with_windows')} {status}", t("app_name"))
            if self.icon:
                self.icon.menu = self.get_menu()
                self.icon.update_menu()
        else:
            # Need admin to modify task
            self.icon.notify(t("requires_admin"), t("app_name"))

    def install_service(self, icon=None, item=None):
        """Install the scheduled task service."""
        if scheduler.is_admin():
            success, msg = scheduler.install_task()
            if success:
                self.icon.notify(t("service_installed"), t("app_name"))
                if self.icon:
                    self.icon.menu = self.get_menu()
                    self.icon.update_menu()
            else:
                self.icon.notify(f"{t('service_install_failed')}: {msg}", t("app_name"))
        else:
            scheduler.run_as_admin_for_install()

    def uninstall_service(self, icon=None, item=None):
        """Uninstall the scheduled task service."""
        if scheduler.is_admin():
            success, msg = scheduler.uninstall_task()
            if success:
                self.icon.notify(t("service_uninstalled"), t("app_name"))
                if self.icon:
                    self.icon.menu = self.get_menu()
                    self.icon.update_menu()
        else:
            scheduler.run_as_admin_for_uninstall()

    def show_window(self, icon=None, item=None):
        """Show the main window."""
        if self.ctk_root:
            self.ctk_root.after(0, self._show_window_safe)

    def _show_window_safe(self):
        """Show window from main thread."""
        if not self.window:
            self.window = MainWindow(self)
        self.window.show()

    def manual_refresh(self, icon=None, item=None):
        """Manually trigger a refresh."""
        self.update()

    def update(self):
        """Update the power requests and icon."""
        self.requests, self.error = get_power_requests()
        actionable = [r for r in self.requests if r.pid]

        if self.icon:
            self.icon.icon = create_icon_image(len(actionable), self.error is not None)
            self.icon.menu = self.get_menu()

            if self.error:
                tooltip = f"{t('app_name')} - {t('requires_admin')}"
            elif actionable:
                tooltip = f"{t('app_name')} - {t('n_blocking', n=len(actionable))}"
            elif self.requests:
                tooltip = f"{t('app_name')} - {t('ready_drivers_only')}"
            else:
                tooltip = f"{t('app_name')} - {t('ready_to_sleep')}"
            self.icon.title = tooltip

        # Update window if visible
        if self.window and self.window.winfo_viewable():
            self.ctk_root.after(0, self.window.update_ui)

    def monitor_loop(self):
        """Background thread that periodically checks for power requests."""
        while self.running:
            self.update()
            time.sleep(self.update_interval)

    def quit(self, icon=None, item=None):
        """Exit the application."""
        self.running = False
        if self._show_gui_event_handle:
            ctypes.windll.kernel32.CloseHandle(self._show_gui_event_handle)
            self._show_gui_event_handle = None
        if self.ctk_root:
            self.ctk_root.after(0, self.ctk_root.quit)
        if self.icon:
            self.icon.stop()

    def _start_show_gui_listener(self):
        """Listen for external launch requests and open existing GUI."""
        event_handle = ctypes.windll.kernel32.CreateEventW(
            None, False, False, SHOW_GUI_EVENT_NAME
        )
        if not event_handle:
            return

        self._show_gui_event_handle = event_handle

        def _listen():
            while self.running and self._show_gui_event_handle:
                wait_result = ctypes.windll.kernel32.WaitForSingleObject(
                    event_handle, 500
                )
                if wait_result == WAIT_OBJECT_0 and self.ctk_root:
                    self.ctk_root.after(0, self._show_window_safe)

        listener_thread = threading.Thread(target=_listen, daemon=True)
        listener_thread.start()

    def run(self):
        """Start the application."""
        # Initialize CTk (hidden root for window management)
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        self.ctk_root = ctk.CTk()
        self._root_tk_icon_images = apply_window_icon(self.ctk_root)
        self.ctk_root.after(350, lambda: apply_window_icon(self.ctk_root))
        self.ctk_root.withdraw()
        self._start_show_gui_listener()

        # Initial update
        self.update()

        # Create tray icon
        actionable = [r for r in self.requests if r.pid]
        self.icon = pystray.Icon(
            "let-me-sleep",
            create_icon_image(len(actionable), self.error is not None),
            "Let Me Sleep",
            self.get_menu(),
        )

        # Start monitor thread
        monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        monitor_thread.start()

        # Run tray icon in separate thread
        icon_thread = threading.Thread(target=self.icon.run, daemon=True)
        icon_thread.start()

        # Run CTk main loop
        self.ctk_root.mainloop()


def main():
    """Entry point."""
    set_windows_app_id()

    # Handle command line arguments
    if "--install-task-with-autostart" in sys.argv:
        success, msg = scheduler.install_task(enable_autostart=True)
        print(msg)
        sys.exit(0 if success else 1)

    if "--install-task" in sys.argv:
        success, msg = scheduler.install_task(enable_autostart=False)
        print(msg)
        sys.exit(0 if success else 1)

    if "--uninstall-task" in sys.argv:
        success, msg = scheduler.uninstall_task()
        print(msg)
        sys.exit(0 if success else 1)

    if not acquire_single_instance():
        signal_existing_instance_show_gui()
        sys.exit(0)

    # If not admin, try to use scheduled task or request elevation
    if not is_admin():
        # Try to run via scheduled task if installed
        if scheduler.is_task_installed():
            success, _ = scheduler.run_task()
            if success:
                sys.exit(0)

        # Otherwise request admin elevation
        if run_as_admin():
            sys.exit(0)
        # If user declined, continue without admin (limited functionality)

    monitor = SleepMonitor()
    monitor.run()


if __name__ == "__main__":
    main()

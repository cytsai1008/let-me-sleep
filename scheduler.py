"""
Scheduled Task management for Let Me Sleep.
Allows running the app with elevated privileges without UAC prompt.
"""

import subprocess
import sys
import os
import ctypes

TASK_NAME = "LetMeSleep"


def _is_packaged_runtime() -> bool:
    """Detect compiled/runtime-packaged execution (Nuitka/onefile/standalone)."""
    if getattr(sys, "frozen", False):
        return True
    if globals().get("__compiled__") is not None:
        return True

    argv0 = os.path.abspath(sys.argv[0]) if sys.argv else ""
    return argv0.lower().endswith(".exe")


def _nuitka_containing_dir() -> str | None:
    """Return Nuitka executable directory when available."""
    compiled = globals().get("__compiled__")
    if compiled is None:
        return None

    containing_dir = getattr(compiled, "containing_dir", None)
    if not containing_dir:
        return None

    try:
        return os.path.abspath(str(containing_dir))
    except Exception:
        return None


def _guess_app_dir() -> str:
    """Best-effort detection of installed app directory."""
    candidates: list[str] = []

    nuitka_dir = _nuitka_containing_dir()
    if nuitka_dir:
        candidates.append(nuitka_dir)

    for raw in (sys.argv[0], sys.executable, os.getcwd()):
        if not raw:
            continue
        path = os.path.abspath(raw)
        directory = path if os.path.isdir(path) else os.path.dirname(path)
        if directory and directory not in candidates:
            candidates.append(directory)

    for directory in candidates:
        if os.path.exists(os.path.join(directory, "LetMeSleep-Updater.exe")):
            return directory

    for directory in candidates:
        if os.path.exists(os.path.join(directory, "LetMeSleep.exe")):
            return directory

    return candidates[0] if candidates else os.path.abspath(".")


def is_admin() -> bool:
    """Check if running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def get_task_command() -> tuple[str, str]:
    """Get command/arguments for the scheduled task (prefer updater)."""
    if _is_packaged_runtime():
        app_dir = _guess_app_dir()
        updater_exe = os.path.join(app_dir, "LetMeSleep-Updater.exe")

        if os.path.exists(updater_exe):
            return updater_exe, f'"{app_dir}" --no-update'

        # Fallback if updater is missing
        app_exe = os.path.join(app_dir, "LetMeSleep.exe")
        if os.path.exists(app_exe):
            return app_exe, ""
        return os.path.abspath(sys.argv[0]), ""

    script_dir = os.path.dirname(os.path.abspath(__file__))
    updater_exe = os.path.join(
        script_dir, "updater", "target", "release", "letmesleep-updater.exe"
    )

    if os.path.exists(updater_exe):
        return updater_exe, f'"{script_dir}" --no-update'

    # Fallback: run python script directly in development mode
    return sys.executable, f'"{os.path.abspath(sys.argv[0])}"'


def is_task_installed() -> bool:
    """Check if the scheduled task is installed."""
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", TASK_NAME],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.returncode == 0
    except:
        return False


def install_task(enable_autostart: bool = False) -> tuple[bool, str]:
    """
    Install the scheduled task.
    If enable_autostart is True, adds logon trigger to start with Windows.
    Returns (success, message).
    """
    if not is_admin():
        return False, "Requires administrator privileges"

    command, arguments = get_task_command()

    # Add logon trigger if autostart is requested
    triggers_section = ""
    if enable_autostart:
        triggers_section = """
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>"""

    # Create XML for the task
    xml_content = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Let Me Sleep - Sleep blocker monitor</Description>
  </RegistrationInfo>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>{triggers_section}
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>false</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{command}</Command>
      {f"<Arguments>{arguments}</Arguments>" if arguments else ""}
    </Exec>
  </Actions>
</Task>"""

    # Write XML to temp file
    temp_xml = os.path.join(os.environ.get("TEMP", "."), "letmesleep_task.xml")
    try:
        with open(temp_xml, "w", encoding="utf-16") as f:
            f.write(xml_content)

        # Create the task
        result = subprocess.run(
            ["schtasks", "/Create", "/TN", TASK_NAME, "/XML", temp_xml, "/F"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        os.remove(temp_xml)

        if result.returncode == 0:
            return True, "Task installed successfully"
        else:
            return False, result.stderr or "Failed to create task"
    except Exception as e:
        return False, str(e)


def uninstall_task() -> tuple[bool, str]:
    """
    Uninstall the scheduled task.
    Returns (success, message).
    """
    if not is_admin():
        return False, "Requires administrator privileges"

    try:
        result = subprocess.run(
            ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        if result.returncode == 0:
            return True, "Task uninstalled successfully"
        else:
            return False, result.stderr or "Failed to delete task"
    except Exception as e:
        return False, str(e)


def run_task() -> tuple[bool, str]:
    """
    Run the scheduled task (starts updater/app elevated).
    Returns (success, message).
    """
    try:
        result = subprocess.run(
            ["schtasks", "/Run", "/TN", TASK_NAME],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        if result.returncode == 0:
            return True, "Task started"
        else:
            return False, result.stderr or "Failed to run task"
    except Exception as e:
        return False, str(e)


def run_as_admin_for_install():
    """Relaunch with admin to install task."""
    script = sys.argv[0]
    python = sys.executable

    if _is_packaged_runtime():
        # Running as exe
        params = "--install-task"
        app_dir = _guess_app_dir()
        app_exe = os.path.join(app_dir, "LetMeSleep.exe")
        exe = app_exe if os.path.exists(app_exe) else os.path.abspath(sys.argv[0])
    else:
        params = f'"{script}" --install-task'
        exe = python

    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    return ret > 32


def run_as_admin_for_uninstall():
    """Relaunch with admin to uninstall task."""
    script = sys.argv[0]
    python = sys.executable

    if _is_packaged_runtime():
        params = "--uninstall-task"
        app_dir = _guess_app_dir()
        app_exe = os.path.join(app_dir, "LetMeSleep.exe")
        exe = app_exe if os.path.exists(app_exe) else os.path.abspath(sys.argv[0])
    else:
        params = f'"{script}" --uninstall-task'
        exe = python

    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    return ret > 32


def is_autostart_enabled() -> bool:
    """Check if autostart (logon trigger) is enabled in the scheduled task."""
    if not is_task_installed():
        return False

    try:
        # Export task to XML and check for LogonTrigger
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", TASK_NAME, "/XML"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        if result.returncode == 0:
            # Handle possible UTF-16/null-separated output from schtasks
            xml_text = result.stdout.replace("\x00", "")
            # Check if LogonTrigger exists in the XML
            return "<LogonTrigger" in xml_text
        return False
    except:
        return False


def toggle_autostart() -> bool:
    """
    Toggle autostart by reinstalling the task with/without logon trigger.
    Returns new autostart state.
    """
    current_state = is_autostart_enabled()
    new_state = not current_state

    # Reinstall task with new autostart setting
    success, msg = install_task(enable_autostart=new_state)

    if success:
        return new_state
    else:
        # If failed, return current state
        return current_state

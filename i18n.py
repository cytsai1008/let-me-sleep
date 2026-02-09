"""
Internationalization support for Let Me Sleep.
"""

import locale

TRANSLATIONS = {
    "en": {
        "app_name": "Let Me Sleep",
        "ready_to_sleep": "Ready to sleep",
        "ready_drivers_only": "Ready (drivers only)",
        "n_blocking": "{n} blocking",
        "n_apps_blocking": "{n} app(s) blocking sleep",
        "no_apps_blocking": "No apps blocking sleep",
        "no_apps_blocking_desc": "Your PC can sleep peacefully",
        "requires_admin": "Requires administrator privileges",
        "run_as_admin": "Run as Administrator to detect\nsleep-blocking applications",
        "end_task": "End Task",
        "driver": "DRIVER",
        "usually_safe_to_ignore": "Usually safe to ignore",
        "open": "Open",
        "refresh": "Refresh",
        "exit": "Exit",
        # Friendly device names
        "smb_network_share": "SMB Network Share",
        "audio_device": "Audio Device",
        "usb_hub": "USB Hub",
        "usb_controller": "USB Controller",
        "intel_power_mgmt": "Intel Power Management",
        "amd_power_mgmt": "AMD Power Management",
        "acpi_power": "ACPI Power",
        "ntfs_filesystem": "NTFS File System",
        "usb_device": "USB Device",
        "pci_device": "PCI Device",
        "input_device": "Input Device",
        "hardware_device": "Hardware Device",
        "legacy_kernel_caller": "Legacy Kernel Caller",
    },
    "zh_TW": {
        "app_name": "Let Me Sleep",
        "ready_to_sleep": "可以睡眠",
        "ready_drivers_only": "就緒 (僅驅動程式)",
        "n_blocking": "{n} 個阻擋中",
        "n_apps_blocking": "{n} 個程式阻擋睡眠",
        "no_apps_blocking": "沒有程式阻擋睡眠",
        "no_apps_blocking_desc": "您的電腦可以安心睡眠",
        "requires_admin": "需要系統管理員權限",
        "run_as_admin": "請以系統管理員身分執行\n以偵測阻擋睡眠的程式",
        "end_task": "結束工作",
        "driver": "驅動程式",
        "usually_safe_to_ignore": "通常可以忽略",
        "open": "開啟",
        "refresh": "重新整理",
        "exit": "結束",
        # Friendly device names
        "smb_network_share": "SMB 網路共用",
        "audio_device": "音訊裝置",
        "usb_hub": "USB 集線器",
        "usb_controller": "USB 控制器",
        "intel_power_mgmt": "Intel 電源管理",
        "amd_power_mgmt": "AMD 電源管理",
        "acpi_power": "ACPI 電源",
        "ntfs_filesystem": "NTFS 檔案系統",
        "usb_device": "USB 裝置",
        "pci_device": "PCI 裝置",
        "input_device": "輸入裝置",
        "hardware_device": "硬體裝置",
        "legacy_kernel_caller": "舊版核心呼叫程式",
    },
    "zh_CN": {
        "app_name": "Let Me Sleep",
        "ready_to_sleep": "可以睡眠",
        "ready_drivers_only": "就绪 (仅驱动程序)",
        "n_blocking": "{n} 个阻止中",
        "n_apps_blocking": "{n} 个程序阻止睡眠",
        "no_apps_blocking": "没有程序阻止睡眠",
        "no_apps_blocking_desc": "您的电脑可以安心睡眠",
        "requires_admin": "需要管理员权限",
        "run_as_admin": "请以管理员身份运行\n以检测阻止睡眠的程序",
        "end_task": "结束任务",
        "driver": "驱动程序",
        "usually_safe_to_ignore": "通常可以忽略",
        "open": "打开",
        "refresh": "刷新",
        "exit": "退出",
        # Friendly device names
        "smb_network_share": "SMB 网络共享",
        "audio_device": "音频设备",
        "usb_hub": "USB 集线器",
        "usb_controller": "USB 控制器",
        "intel_power_mgmt": "Intel 电源管理",
        "amd_power_mgmt": "AMD 电源管理",
        "acpi_power": "ACPI 电源",
        "ntfs_filesystem": "NTFS 文件系统",
        "usb_device": "USB 设备",
        "pci_device": "PCI 设备",
        "input_device": "输入设备",
        "hardware_device": "硬件设备",
        "legacy_kernel_caller": "旧版内核调用程序",
    },
}

# Detect system language
_system_locale = locale.getdefaultlocale()[0] or "en"
_current_lang = "en"

if _system_locale.startswith("zh_TW") or _system_locale.startswith("zh_Hant"):
    _current_lang = "zh_TW"
elif _system_locale.startswith("zh"):
    _current_lang = "zh_CN"


def get_lang() -> str:
    """Get current language code."""
    return _current_lang


def set_lang(lang: str):
    """Set current language."""
    global _current_lang
    if lang in TRANSLATIONS:
        _current_lang = lang


def t(key: str, **kwargs) -> str:
    """Get translated string."""
    translations = TRANSLATIONS.get(_current_lang, TRANSLATIONS["en"])
    text = translations.get(key, TRANSLATIONS["en"].get(key, key))
    if kwargs:
        text = text.format(**kwargs)
    return text

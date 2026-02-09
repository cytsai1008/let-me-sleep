"""
Test program that blocks Windows sleep using PowerCreateRequest API.
This will show up in 'powercfg /requests'.
Run this to test if let-me-sleep detects it.
"""

import ctypes
from ctypes import wintypes
import time

# Power request types
PowerRequestDisplayRequired = 0
PowerRequestSystemRequired = 1
PowerRequestAwayModeRequired = 2

# Reason context structure
class REASON_CONTEXT(ctypes.Structure):
    _fields_ = [
        ("Version", wintypes.ULONG),
        ("Flags", wintypes.DWORD),
        ("ReasonString", wintypes.LPCWSTR),
    ]

POWER_REQUEST_CONTEXT_VERSION = 0
POWER_REQUEST_CONTEXT_SIMPLE_STRING = 0x1

def create_power_request(reason: str):
    """Create a power request that will show in powercfg /requests."""
    kernel32 = ctypes.windll.kernel32

    # Set up the reason context
    context = REASON_CONTEXT()
    context.Version = POWER_REQUEST_CONTEXT_VERSION
    context.Flags = POWER_REQUEST_CONTEXT_SIMPLE_STRING
    context.ReasonString = reason

    # Create the power request
    kernel32.PowerCreateRequest.restype = wintypes.HANDLE
    kernel32.PowerCreateRequest.argtypes = [ctypes.POINTER(REASON_CONTEXT)]

    handle = kernel32.PowerCreateRequest(ctypes.byref(context))
    if handle == wintypes.HANDLE(-1).value or handle == 0:
        error = ctypes.get_last_error()
        raise OSError(f"PowerCreateRequest failed with error {error}")

    return handle

def set_power_request(handle, request_type):
    """Activate a power request."""
    kernel32 = ctypes.windll.kernel32
    kernel32.PowerSetRequest.restype = wintypes.BOOL
    kernel32.PowerSetRequest.argtypes = [wintypes.HANDLE, ctypes.c_int]

    result = kernel32.PowerSetRequest(handle, request_type)
    if not result:
        error = ctypes.get_last_error()
        raise OSError(f"PowerSetRequest failed with error {error}")

def clear_power_request(handle, request_type):
    """Deactivate a power request."""
    kernel32 = ctypes.windll.kernel32
    kernel32.PowerClearRequest.restype = wintypes.BOOL
    kernel32.PowerClearRequest.argtypes = [wintypes.HANDLE, ctypes.c_int]

    kernel32.PowerClearRequest(handle, request_type)

def close_power_request(handle):
    """Close a power request handle."""
    ctypes.windll.kernel32.CloseHandle(handle)

def main():
    print("Creating power request to block sleep...")

    try:
        handle = create_power_request("Testing let-me-sleep detection")
        set_power_request(handle, PowerRequestSystemRequired)
        print("Sleep blocked! This should show in 'powercfg /requests'")
        print("Press Ctrl+C to stop blocking and exit.")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nClearing power request...")
        clear_power_request(handle, PowerRequestSystemRequired)
        close_power_request(handle)
        print("Done. Sleep is allowed again.")
    except OSError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

# TODO

## Completed

- [x] Implement non-admin mode using Scheduled Task:
  - Added `scheduler.py` with task install/uninstall/run functions
  - Menu options to Install/Uninstall Service
  - App auto-runs via task if installed (no UAC prompt)
  - Command line args: `--install-task`, `--uninstall-task`

- [x] Auto-updater:
  - Added `updater.py` with GitHub release checking
  - Menu option to check for updates
  - Background download and install support

- [x] Installer:
  - Added `installer.iss` (Inno Setup script)
  - Supports multiple languages (EN, zh-TW, zh-CN)
  - Option to start with Windows
  - Auto-cleanup on uninstall

- [x] Build to EXE:
  - Added `letmesleep.spec` (PyInstaller config)
  - Added `build.py` build script
  - Single-file executable, no console

## Future Ideas

- [ ] Add notification when new app starts blocking sleep
- [ ] History log of sleep blockers
- [ ] Custom ignore list for specific processes
- [ ] Portable mode (no install)

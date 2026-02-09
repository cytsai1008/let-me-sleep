# TODO

## For Final Release

- [ ] Implement non-admin mode using Scheduled Task:
  1. On first run (or via menu option), prompt user to register a Scheduled Task
  2. One-time admin elevation to create the task with "Run with highest privileges"
  3. Task launches the tray app (`main.py`) directly with elevated privileges
  4. User can then start the app from Start Menu / shortcut without admin prompt
  5. Add "Install as Scheduled Task" and "Uninstall" options to tray menu

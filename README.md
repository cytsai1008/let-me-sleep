# Let Me Sleep

A Windows system tray application that detects and displays applications preventing your system from sleeping.

## Features

- 🔍 **Real-time Monitoring**: Continuously monitors Windows power requests
- 🎯 **System Tray Integration**: Clean system tray icon with status updates
- 🌐 **Multi-language Support**: i18n support for multiple languages
- 🔄 **Auto-update**: Built-in updater checks for new releases from GitHub
- ⚙️ **Task Scheduler Integration**: Runs with elevated privileges without UAC prompts
- 🚀 **Autostart Support**: Optional Windows logon trigger for automatic startup
- 🎨 **Modern UI**: Built with CustomTkinter for a modern interface

## Requirements

### Runtime Requirements
- Windows 10 or later
- Administrator privileges (required to query power requests)

### Development Requirements
- Python 3.13 or later
- Rust 1.80+ (for building the updater)
- [Inno Setup](https://jrsoftware.org/isinfo.php) (optional, for creating installer)
- [uv](https://docs.astral.sh/uv/) package manager (recommended)

## Installation

### For End Users

Download the latest installer from the [Releases](https://github.com/cytsai1008/let-me-sleep/releases) page and run `LetMeSleep_Setup_x.x.x.exe`.

### For Developers

1. **Clone the repository**
   ```bash
   git clone https://github.com/cytsai1008/let-me-sleep.git
   cd let-me-sleep
   ```

2. **Install Python dependencies**
   ```bash
   # Using uv (recommended)
   uv sync

   # Or using pip
   pip install -e .
   ```

3. **Run from source**
   ```bash
   # With uv
   uv run python main.py

   # Or with your active venv
   python main.py
   ```

## Usage Instructions

1. Launch Let Me Sleep (from Start Menu, installed shortcut, or `python main.py`).
2. Check the tray icon:
   - Green `0` means no blocking process is detected.
   - Red number means one or more processes are blocking sleep.
   - Gray `!` means the app cannot read power requests (usually admin permission issue).
3. Click the tray icon menu and select **Open** to view details.
4. In the app window, review blocking entries:
   - Process entries show an **End Task** button.
   - Driver/system entries are shown under **Usually safe to ignore**.
5. From the tray menu, you can:
   - **Refresh** to manually re-check power requests.
   - **Install service** to create the elevated scheduled task.
   - Toggle **Start with Windows** after service installation.
   - **Exit** to close the app.

## Building

### Quick Build (All Components)

Use the provided build script to build everything at once:

```bash
python build_all.py
```

This will:
1. Build the Python application into a standalone executable
2. Build the Rust updater
3. Optionally create an installer (if Inno Setup is installed)

### Manual Build Steps

#### 1. Build Python Application

```bash
python build.py
```

This creates `dist/LetMeSleep.exe` using PyInstaller.

#### 2. Build Rust Updater

```bash
cargo build --release --manifest-path updater/Cargo.toml
```

The updater executable will be at `updater/target/release/letmesleep-updater.exe`.

#### 3. Create Installer (Optional)

After building both components:

```bash
# Make sure Inno Setup is installed and in PATH
iscc installer.iss
```

The installer will be created in the `installer_output` directory.

## Project Structure

```
let-me-sleep/
├── main.py              # Main application entry point
├── i18n.py              # Internationalization support
├── scheduler.py         # Task Scheduler integration (autostart & elevated privileges)
├── build.py             # Python build script
├── build_all.py         # Complete build script
├── letmesleep.spec      # PyInstaller specification
├── installer.iss        # Inno Setup installer script
├── pyproject.toml       # Python project configuration
├── updater/             # Rust-based auto-updater
│   ├── src/
│   │   └── main.rs      # Updater source code
│   ├── Cargo.toml       # Rust project configuration
│   └── Cargo.lock
└── README.md            # This file
```

## Configuration

### Scheduled Task (Recommended)

The application uses Windows Task Scheduler to run with elevated privileges:
- Install the scheduled task from the system tray menu or during installation
- Once installed, you can enable/disable "Start with Windows" from the tray menu
- Task name: `LetMeSleep`
- Runs with highest available privileges (no UAC prompt)

### Autostart

Enable autostart from the system tray menu (requires scheduled task to be installed first). The application uses a Windows Task Scheduler logon trigger instead of registry-based autostart for better compatibility and admin privilege support.

## Development

### Running in Development Mode

```bash
# Recommended
uv run python main.py
```

### Adding Dependencies

```bash
# Using uv
uv add package-name

# Or edit pyproject.toml and run
uv sync
```

### Updater Configuration

The updater is configured to check releases from:
- Repository: `cytsai1008/let-me-sleep`
- Looks for `.zip` assets in GitHub releases

To change the repository, edit `updater/src/main.rs` and modify the `REPO` constant.

## Building for Release

1. **Update version numbers** in:
   - `pyproject.toml`
   - `installer.iss`
   - `updater/Cargo.toml`

2. **Build all components**:
   ```bash
   python build_all.py
   ```

3. **Test the installer**:
   ```bash
   installer_output\LetMeSleep_Setup_x.x.x.exe
   ```

4. **Create a GitHub release**:
   - Tag the release (e.g., `v0.1.0`)
   - Upload the installer and a `.zip` containing the built files
   - The updater will automatically detect new releases

## Troubleshooting

### "Access Denied" Errors
The application requires administrator privileges to query Windows power requests. Right-click and select "Run as administrator" or allow UAC prompt.

### Updater Not Working
- Ensure the `VERSION` file exists in the application directory
- Check that the repository name in the updater matches your GitHub repository
- Verify internet connectivity and GitHub API access

### Build Errors
- Ensure all dependencies are installed
- For Python: Check Python version is 3.13+
- For Rust: Run `cargo clean` and try again
- For Installer: Verify Inno Setup is installed and in PATH

## License

This project is licensed under the MIT License. See `LICENSE` for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

- Built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- System tray support via [pystray](https://github.com/moses-palmer/pystray)
- Auto-updater written in Rust for reliability and small size

## Support

If you encounter any issues or have questions:
- Open an issue on [GitHub Issues](https://github.com/cytsai1008/let-me-sleep/issues)
- Check existing issues for solutions

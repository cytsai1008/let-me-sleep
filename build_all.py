"""
Complete build script for Let Me Sleep.
Builds the Python application, Rust updater, and optionally creates installer.
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

VERSION = "0.1.1"

def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def check_command(command, name):
    """Check if a command is available."""
    try:
        subprocess.run([command, "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"⚠️  {name} not found in PATH")
        return False


def convert_png_to_ico():
    """Convert icon.png to icon.ico (always regenerate)."""
    icon_png = Path("icon.png")
    if not icon_png.exists():
        print("❌ icon.png not found. Cannot generate icon.ico")
        return False

    print("Converting icon.png -> icon.ico...")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from PIL import Image; img=Image.open('icon.png').convert('RGBA'); img.save('icon.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])",
        ]
    )
    if result.returncode != 0 or not Path("icon.ico").exists():
        print("❌ Failed to generate icon.ico from icon.png")
        return False

    print("✓ icon.ico generated from icon.png")
    return True


def ensure_icon_assets():
    """Ensure icon files exist and are included by the spec."""
    icon_ico = Path("icon.ico")
    spec_path = Path("letmesleep.spec")

    if not icon_ico.exists():
        print("❌ icon.ico not found. Run icon conversion step first.")
        return False

    if not spec_path.exists():
        print("❌ letmesleep.spec not found.")
        return False

    spec = spec_path.read_text(encoding="utf-8")
    required_snippets = [
        "('icon.png', '.')",
        "('icon.ico', '.')",
        "icon='icon.ico'",
    ]
    missing = [s for s in required_snippets if s not in spec]
    if missing:
        print("❌ letmesleep.spec is missing required icon config:")
        for item in missing:
            print(f"   - {item}")
        return False

    print("✓ Icon assets/config verified")
    return True


def build_python_app():
    """Build the Python application using PyInstaller."""
    print_section("Building Python Application")

    if not ensure_icon_assets():
        return False

    # Check for PyInstaller
    try:
        import PyInstaller

        print("✓ PyInstaller found")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller"], check=True
        )

    # Clean previous builds
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"Cleaning {folder}/...")
            shutil.rmtree(folder)

    # Build with PyInstaller
    print("Running PyInstaller...")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            "letmesleep.spec",
        ]
    )

    if result.returncode != 0:
        print("❌ Python build failed!")
        return False

    exe_path = Path("dist/LetMeSleep.exe")
    if not exe_path.exists():
        print("❌ Build completed but exe not found!")
        return False

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"✓ Python build successful! ({size_mb:.1f} MB)")
    return True


def build_rust_updater():
    """Build the Rust updater."""
    print_section("Building Rust Updater")

    if not check_command("cargo", "Rust/Cargo"):
        print("❌ Please install Rust from https://rustup.rs/")
        return False

    updater_dir = Path("updater")
    if not updater_dir.exists():
        print("❌ Updater directory not found!")
        return False

    print("Running cargo build --release...")
    result = subprocess.run(["cargo", "build", "--release"], cwd=updater_dir)

    if result.returncode != 0:
        print("❌ Rust build failed!")
        return False

    updater_exe = updater_dir / "target/release/letmesleep-updater.exe"
    if not updater_exe.exists():
        print("❌ Updater executable not found!")
        return False

    # Copy updater to dist
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)

    dest_updater = dist_dir / "LetMeSleep-Updater.exe"
    shutil.copy2(updater_exe, dest_updater)

    size_kb = dest_updater.stat().st_size / 1024
    print(f"✓ Rust updater built successfully! ({size_kb:.0f} KB)")
    print(f"  Copied to: {dest_updater}")
    return True


def create_version_file():
    """Create VERSION file in dist."""
    print_section("Creating VERSION File")

    # Try to get version from pyproject.toml
    version = VERSION  # default
    try:
        with open("pyproject.toml", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("version = "):
                    version = line.split('"')[1]
                    break
    except Exception as e:
        print(f"⚠️  Could not read version from pyproject.toml: {e}")

    version_file = Path("dist/VERSION")
    version_file.write_text(version, encoding="utf-8")
    print(f"✓ Created VERSION file: v{version}")
    return version


def create_zip_release():
    """Create a ZIP file of the dist folder for releases."""
    print_section("Creating Release ZIP")

    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("❌ Dist directory not found!")
        return False

    # Get version for filename
    version = VERSION
    version_file = dist_dir / "VERSION"
    if version_file.exists():
        version = version_file.read_text(encoding="utf-8").strip()

    zip_name = f"LetMeSleep-v{version}"
    print(f"Creating {zip_name}.zip...")

    # Create zip
    shutil.make_archive(zip_name, "zip", dist_dir)

    zip_path = Path(f"{zip_name}.zip")
    if zip_path.exists():
        size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"✓ Release ZIP created: {zip_path} ({size_mb:.1f} MB)")
        return True

    return False


def create_installer():
    """Create installer using Inno Setup."""
    print_section("Creating Installer")

    """
    if not check_command("iscc", "Inno Setup"):
        print("⚠️  Inno Setup not found. Skipping installer creation.")
        print("   Download from: https://jrsoftware.org/isinfo.php")
        return False
    """

    iss_file = Path("installer.iss")
    if not iss_file.exists():
        print("❌ installer.iss not found!")
        return False

    print("Running Inno Setup compiler...")
    result = subprocess.run(["iscc", str(iss_file)])

    if result.returncode != 0:
        print("❌ Installer creation failed!")
        return False

    # Find the created installer
    output_dir = Path("installer_output")
    if output_dir.exists():
        installers = list(output_dir.glob("*.exe"))
        if installers:
            installer = installers[0]
            size_mb = installer.stat().st_size / (1024 * 1024)
            print(f"✓ Installer created: {installer} ({size_mb:.1f} MB)")
            return True

    print("⚠️  Installer may have been created but could not be verified")
    return False


def main():
    """Main build process."""
    print_section("Let Me Sleep - Complete Build Script")

    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    print(f"Working directory: {script_dir}")

    print_section("Preparing Icon Assets")
    if not convert_png_to_ico():
        print("\n❌ Build process stopped due to icon conversion failure.")
        sys.exit(1)

    # Track success
    success = True

    # Step 1: Build Python application
    if not build_python_app():
        print("\n❌ Build process stopped due to Python build failure.")
        sys.exit(1)

    # Step 2: Build Rust updater
    if not build_rust_updater():
        print("\n⚠️  Continuing without updater...")
        success = False

    # Step 3: Create VERSION file
    create_version_file()

    # Step 4: Create release ZIP
    create_zip_release()

    # Step 5: Create installer (optional)
    create_installer()

    # Summary
    print_section("Build Summary")

    dist_dir = Path("dist")
    if dist_dir.exists():
        print("Built files in dist/:")
        for item in sorted(dist_dir.iterdir()):
            if item.is_file():
                size = item.stat().st_size
                if size > 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{size / 1024:.1f} KB"
                print(f"  • {item.name} ({size_str})")

    print("\n" + "=" * 70)
    if success:
        print("✓ Build process completed successfully!")
    else:
        print("⚠️  Build completed with warnings.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Build cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

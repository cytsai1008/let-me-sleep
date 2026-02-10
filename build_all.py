"""Complete build script for Let Me Sleep."""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

DEFAULT_VERSION = "0.0.0"
APP_EXE = "LetMeSleep.exe"
ENTRY_SCRIPT = "main.py"


def pretty_path(path: Path | str) -> str:
    """Return a cleaner path for console output."""
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(resolved)


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
            "uv",
            "run",
            "python",
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
    """Ensure icon files exist for Nuitka build."""
    icon_png = Path("icon.png")
    icon_ico = Path("icon.ico")

    if not icon_png.exists():
        print("❌ icon.png not found.")
        return False

    if not icon_ico.exists():
        print("❌ icon.ico not found. Run icon conversion step first.")
        return False

    print("✓ Icon assets verified")
    return True


def build_python_app(mode: str):
    """Build the Python application using Nuitka."""
    print_section("Building Python Application")

    if not ensure_icon_assets():
        return False

    # Clean previous builds
    for folder in ["build", "dist", "main.build", "main.dist", "main.onefile-build"]:
        path = Path(folder)
        if path.exists():
            print(f"Cleaning {folder}/...")
            shutil.rmtree(path)

    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)

    cmd = [
        "uv",
        "run",
        "--group",
        "dev",
        "python",
        "-m",
        "nuitka",
        "--windows-console-mode=disable",
        "--assume-yes-for-downloads",
        "--windows-icon-from-ico=icon.ico",
        "--enable-plugin=tk-inter",
        "--include-data-files=icon.png=icon.png",
        "--include-data-files=icon.ico=icon.ico",
        "--output-dir=dist",
        f"--output-filename={APP_EXE}",
        "--remove-output",
    ]

    if mode == "standalone":
        cmd.append("--standalone")
    elif mode == "onefile":
        cmd.append("--onefile")
    else:
        print(f"❌ Unsupported build mode: {mode}")
        return False

    cmd.append(ENTRY_SCRIPT)

    print(f"Running Nuitka ({mode})...")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("❌ Python build failed!")
        return False

    dist_dir = Path("dist")
    exe_path = dist_dir / APP_EXE
    if not exe_path.exists():
        for candidate in sorted(dist_dir.glob("*.dist")):
            preferred = candidate / APP_EXE
            if preferred.exists():
                exe_path = preferred
                break
            fallback = sorted(
                p
                for p in candidate.glob("*.exe")
                if p.name.lower() != "letmesleep-updater.exe"
            )
            if fallback:
                exe_path = fallback[0]
                break

    if not exe_path.exists():
        print("❌ Build completed but app executable not found in dist/")
        return False

    runtime_dirs = []
    if mode == "standalone":
        runtime_dirs = sorted(dist_dir.glob("*.dist"))
        if not runtime_dirs:
            print("❌ Standalone runtime directory not found in dist/")
            return False

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"✓ Python build successful! ({size_mb:.1f} MB)")
    if mode == "standalone":
        print(f"  App executable: {pretty_path(exe_path)}")
        print(f"  Runtime folder: {pretty_path(runtime_dirs[0])}")
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
    print(f"  Copied to: {pretty_path(dest_updater)}")
    return True


def create_version_file():
    """Create VERSION file in dist."""
    print_section("Creating VERSION File")

    # Try to get version from pyproject.toml
    version = DEFAULT_VERSION  # default
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
    """Create a ZIP with app payload under app/ and updater at root."""
    print_section("Creating Release ZIP")

    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("❌ Dist directory not found!")
        return False

    # Get version for filename
    version = DEFAULT_VERSION
    version_file = dist_dir / "VERSION"
    if version_file.exists():
        version = version_file.read_text(encoding="utf-8").strip()

    zip_name = f"LetMeSleep-v{version}"
    print(f"Creating {zip_name}.zip...")

    runtime_dir = dist_dir / "main.dist"
    if not runtime_dir.exists():
        runtime_candidates = sorted(dist_dir.glob("*.dist"))
        if runtime_candidates:
            runtime_dir = runtime_candidates[0]
    onefile_exe = dist_dir / APP_EXE

    zip_path = Path(f"{zip_name}.zip")
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if runtime_dir.exists() and runtime_dir.is_dir():
            print(f"Adding runtime folder to ZIP: {pretty_path(runtime_dir)}")
            for path in runtime_dir.rglob("*"):
                if path.is_file():
                    archive.write(path, Path("app") / path.relative_to(runtime_dir))
        elif onefile_exe.exists():
            print(f"Adding onefile app to ZIP: {pretty_path(onefile_exe)}")
            archive.write(onefile_exe, Path("app") / APP_EXE)
        else:
            print(
                "⚠️  App payload not found (expected dist/main.dist, dist/*.dist, or dist/LetMeSleep.exe)"
            )

        updater_path = dist_dir / "LetMeSleep-Updater.exe"
        if updater_path.exists():
            archive.write(updater_path, updater_path.name)
        else:
            print("⚠️  Updater not found in dist/LetMeSleep-Updater.exe")

        version_path = dist_dir / "VERSION"
        if version_path.exists():
            archive.write(version_path, version_path.name)

    if zip_path.exists():
        size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"✓ Release ZIP created: {pretty_path(zip_path)} ({size_mb:.1f} MB)")
        return True

    return False


def create_installer(_mode: str):
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
            print(f"✓ Installer created: {pretty_path(installer)} ({size_mb:.1f} MB)")
            return True

    print("⚠️  Installer may have been created but could not be verified")
    return False


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Build Let Me Sleep artifacts")
    parser.add_argument(
        "--mode",
        choices=["standalone", "onefile"],
        default="standalone",
        help="Python packaging mode for Nuitka (default: standalone)",
    )
    parser.add_argument(
        "--py",
        action="store_true",
        help="Build Python app (main)",
    )
    parser.add_argument(
        "--rs",
        action="store_true",
        help="Build Rust updater",
    )
    parser.add_argument(
        "--inno",
        action="store_true",
        help="Build Inno Setup installer",
    )
    return parser.parse_args()


def main():
    """Main build process."""
    args = parse_args()

    print_section("Let Me Sleep - Complete Build Script")

    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    print(f"Working directory: {script_dir}")

    selected = []
    if args.py:
        selected.append("py")
    if args.rs:
        selected.append("rs")
    if args.inno:
        selected.append("inno")

    if not selected:
        selected = ["py", "rs", "inno"]

    # Track success
    success = True

    # Step 1: Build Python application
    if "py" in selected:
        print_section("Preparing Icon Assets")
        if not convert_png_to_ico():
            print("\n❌ Build process stopped due to icon conversion failure.")
            sys.exit(1)

        if not build_python_app(args.mode):
            print("\n❌ Build process stopped due to Python build failure.")
            sys.exit(1)

    # Step 2: Build Rust updater
    if "rs" in selected:
        if not build_rust_updater():
            print("\n⚠️  Continuing without updater...")
            success = False

    # Step 3: Create VERSION file (only when building app/updater)
    if "py" in selected or "rs" in selected:
        create_version_file()

    # Step 4: Create release ZIP (only when building app/updater)
    if "py" in selected or "rs" in selected:
        create_zip_release()

    # Step 5: Create installer (optional)
    if "inno" in selected:
        if not create_installer(args.mode):
            success = False

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
            elif item.is_dir():
                print(f"  • {item.name}/")

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

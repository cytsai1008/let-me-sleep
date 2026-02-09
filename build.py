"""
Build script for Let Me Sleep.
Creates a standalone executable using PyInstaller.
"""

import subprocess
import sys
import os
import shutil


def ensure_icon_assets(script_dir: str):
    """Ensure icon files exist and are included by the spec."""
    icon_png = os.path.join(script_dir, "icon.png")
    icon_ico = os.path.join(script_dir, "icon.ico")
    spec_path = os.path.join(script_dir, "letmesleep.spec")

    if not os.path.exists(icon_png):
        print("❌ icon.png not found. Cannot build with app icon.")
        sys.exit(1)

    if not os.path.exists(icon_ico):
        print("icon.ico not found, generating from icon.png...")
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from PIL import Image; img=Image.open('icon.png').convert('RGBA'); img.save('icon.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])",
            ],
            cwd=script_dir,
        )
        if result.returncode != 0 or not os.path.exists(icon_ico):
            print("❌ Failed to generate icon.ico from icon.png")
            sys.exit(1)

    if not os.path.exists(spec_path):
        print("❌ letmesleep.spec not found.")
        sys.exit(1)

    with open(spec_path, "r", encoding="utf-8") as f:
        spec = f.read()

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
        sys.exit(1)

    print("✓ Icon assets/config verified")


def main():
    # Ensure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    print("Building Let Me Sleep...")

    ensure_icon_assets(script_dir)

    # Install pyinstaller if not present
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller"], check=True
        )

    # Clean previous builds
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"Cleaning {folder}...")
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

    if result.returncode == 0:
        exe_path = os.path.join("dist", "LetMeSleep.exe")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\nBuild successful!")
            print(f"Output: {os.path.abspath(exe_path)}")
            print(f"Size: {size_mb:.1f} MB")
        else:
            print("\nBuild completed but exe not found.")
    else:
        print("\nBuild failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

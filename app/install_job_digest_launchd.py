from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
LABEL = "com.limi.resume-tailor.jobdigest"


def build_plist() -> dict[str, object]:
    output_dir = BASE_DIR / "outputs" / "job_digest"
    output_dir.mkdir(parents=True, exist_ok=True)

    return {
        "Label": LABEL,
        "ProgramArguments": [
            str(BASE_DIR / ".venv" / "bin" / "python"),
            "-m",
            "app.run_job_digest",
        ],
        "WorkingDirectory": str(BASE_DIR),
        "StartCalendarInterval": {
            "Hour": 9,
            "Minute": 0,
        },
        "RunAtLoad": False,
        "StandardOutPath": str(output_dir / "launchd.stdout.log"),
        "StandardErrorPath": str(output_dir / "launchd.stderr.log"),
    }


def install() -> Path:
    target = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(plistlib.dumps(build_plist()))

    gui_target = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", gui_target, str(target)], check=False)
    subprocess.run(["launchctl", "bootstrap", gui_target, str(target)], check=True)
    return target


def uninstall() -> Path:
    target = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    gui_target = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", gui_target, str(target)], check=False)
    if target.exists():
        target.unlink()
    return target


def print_plist() -> None:
    sys.stdout.buffer.write(plistlib.dumps(build_plist()))


def main(argv: list[str] | None = None) -> None:
    args = argv or sys.argv[1:]
    if not args or args == ["--install"]:
        path = install()
        print(f"Installed LaunchAgent at {path}")
        return
    if args == ["--uninstall"]:
        path = uninstall()
        print(f"Uninstalled LaunchAgent from {path}")
        return
    if args == ["--print"]:
        print_plist()
        return
    raise SystemExit("Usage: python -m app.install_job_digest_launchd [--install|--uninstall|--print]")


if __name__ == "__main__":
    main()

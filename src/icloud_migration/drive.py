"""iCloud Drive download tool."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloudFailedLoginException

CHUNK_SIZE = 64 * 1024


def authenticate(
    username: str,
    password: str,
    *,
    input_fn=input,
    output=sys.stderr,
) -> PyiCloudService:
    """Authenticate with iCloud, handling 2FA and 2SA prompts interactively.

    `input_fn` and `output` are injected so tests can drive the prompts.
    """
    try:
        api = PyiCloudService(username, password)
    except PyiCloudFailedLoginException as exc:
        raise RuntimeError(
            f"iCloud login failed for {username}: bad Apple ID or password"
        ) from exc

    if api.requires_2fa:
        print("Two-factor authentication required.", file=output)
        code = input_fn("Enter the 2FA code from your trusted device: ").strip()
        if not api.validate_2fa_code(code):
            raise RuntimeError("Invalid 2FA code")
        if not api.is_trusted_session:
            api.trust_session()
    elif api.requires_2sa:
        print("Two-step authentication required.", file=output)
        devices = api.trusted_devices
        for i, device in enumerate(devices):
            label = device.get("deviceName") or device.get("phoneNumber") or "device"
            print(f"  {i}: {label}", file=output)
        choice = int(input_fn("Choose a device index: ").strip())
        device = devices[choice]
        if not api.send_verification_code(device):
            raise RuntimeError("Failed to send 2SA verification code")
        code = input_fn("Enter the verification code: ").strip()
        if not api.validate_verification_code(device, code):
            raise RuntimeError("Invalid 2SA verification code")

    return api


def _is_folder(node) -> bool:
    return getattr(node, "type", None) == "folder"


def download_node(node, dest_dir: str, *, output=sys.stderr) -> int:
    """Recursively mirror a DriveNode at `dest_dir`. Returns # of files downloaded."""
    dest = Path(dest_dir)

    if _is_folder(node):
        dest.mkdir(parents=True, exist_ok=True)
        try:
            children = node.get_children()
        except Exception as exc:
            print(
                f"WARN: failed to list children of {node.name!r}: {exc}",
                file=output,
            )
            return 0
        downloaded = 0
        for child in children:
            downloaded += download_node(child, str(dest / child.name), output=output)
        return downloaded

    if dest.exists() and dest.stat().st_size > 0:
        return 0

    dest.parent.mkdir(parents=True, exist_ok=True)
    with node.open(stream=True) as response:
        with open(dest, "wb") as fp:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    fp.write(chunk)
    return 1


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="icloud-drive",
        description="Download iCloud Drive contents to a local directory.",
    )
    parser.add_argument("--username", help="Apple ID (overrides .env)")
    parser.add_argument("--password", help="iCloud password (overrides .env)")
    parser.add_argument(
        "--dest",
        default="/mnt/usb_migration/icloud_drive",
        help="Destination directory (default: /mnt/usb_migration/icloud_drive)",
    )
    args = parser.parse_args(argv)

    load_dotenv()
    username = args.username or os.environ.get("ICLOUD_USERNAME")
    password = args.password or os.environ.get("ICLOUD_PASSWORD")
    if not username or not password:
        print(
            "ERROR: set ICLOUD_USERNAME and ICLOUD_PASSWORD (in .env or via --username/--password).",
            file=sys.stderr,
        )
        return 2

    api = authenticate(username, password)
    root = api.drive.root
    print(f"Mirroring iCloud Drive → {args.dest}", file=sys.stderr)
    count = download_node(root, args.dest)
    print(f"Downloaded {count} new file(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

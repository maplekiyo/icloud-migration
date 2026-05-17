"""iCloud Drive download tool."""

import argparse
import sys


def authenticate(username: str, password: str):
    """Authenticate with iCloud and return the API object."""
    raise NotImplementedError("Implemented in Phase 2")


def download_node(node, dest_dir: str) -> int:
    """Recursively download a Drive node; returns count of files downloaded."""
    raise NotImplementedError("Implemented in Phase 2")


def main(argv=None):
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
    parser.parse_args(argv)
    print("icloud-drive: Phase 2 not yet implemented.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()

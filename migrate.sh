#!/usr/bin/env bash
# iCloud → USB migration orchestrator.
#
# Loads credentials from .env, mounts the USB drive, downloads iCloud Photos
# and iCloud Drive contents, then unmounts cleanly. Re-runnable: both
# downloaders skip files that already exist.
#
# Usage:
#   sudo ./migrate.sh              # full run
#   sudo ./migrate.sh --dry-run    # mount + space check only, no iCloud calls

set -euo pipefail

# --- config -----------------------------------------------------------------
USB_DEVICE="${USB_DEVICE:-/dev/sdc1}"
USB_MOUNT="${USB_MOUNT:-/mnt/usb_migration}"
PHOTOS_DIR="${PHOTOS_DIR:-${USB_MOUNT}/icloud_photos}"
DRIVE_DIR="${DRIVE_DIR:-${USB_MOUNT}/icloud_drive}"
MIN_FREE_GB="${MIN_FREE_GB:-10}"

DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- env --------------------------------------------------------------------
if [[ ! -f "${PROJECT_DIR}/.env" ]]; then
  echo "ERROR: ${PROJECT_DIR}/.env not found" >&2
  exit 1
fi
# shellcheck disable=SC1091
set -a; source "${PROJECT_DIR}/.env"; set +a

# Accept either APPLE_ID or ICLOUD_USERNAME for the Apple ID.
APPLE_ID="${APPLE_ID:-${ICLOUD_USERNAME:-}}"
if [[ -z "${APPLE_ID}" || -z "${ICLOUD_PASSWORD:-}" ]]; then
  echo "ERROR: set APPLE_ID (or ICLOUD_USERNAME) and ICLOUD_PASSWORD in .env" >&2
  exit 1
fi

# --- unmount trap -----------------------------------------------------------
WE_MOUNTED=0
cleanup() {
  local rc=$?
  if (( WE_MOUNTED )); then
    echo "[cleanup] sync && unmount ${USB_MOUNT}" >&2
    sync || true
    umount "${USB_MOUNT}" 2>/dev/null || umount -l "${USB_MOUNT}" 2>/dev/null || true
  fi
  exit "$rc"
}
trap cleanup EXIT INT TERM

# --- mount ------------------------------------------------------------------
if mountpoint -q "${USB_MOUNT}"; then
  echo "[mount] ${USB_MOUNT} already mounted" >&2
else
  if [[ ! -b "${USB_DEVICE}" ]]; then
    echo "ERROR: ${USB_DEVICE} is not a block device — is the USB plugged in?" >&2
    exit 1
  fi
  mkdir -p "${USB_MOUNT}"
  echo "[mount] mounting ${USB_DEVICE} → ${USB_MOUNT}" >&2
  mount -t ntfs-3g -o "uid=$(id -u "${SUDO_USER:-$USER}"),gid=$(id -g "${SUDO_USER:-$USER}"),umask=0022" \
        "${USB_DEVICE}" "${USB_MOUNT}"
  WE_MOUNTED=1
fi

# --- free-space check -------------------------------------------------------
FREE_KB="$(df --output=avail -k "${USB_MOUNT}" | tail -1 | tr -d ' ')"
FREE_GB=$(( FREE_KB / 1024 / 1024 ))
echo "[space] ${FREE_GB} GB free on ${USB_MOUNT} (require ${MIN_FREE_GB})" >&2
if (( FREE_GB < MIN_FREE_GB )); then
  echo "ERROR: insufficient free space (${FREE_GB} GB < ${MIN_FREE_GB} GB)" >&2
  exit 1
fi

mkdir -p "${PHOTOS_DIR}" "${DRIVE_DIR}"

if (( DRY_RUN )); then
  echo "[dry-run] skipping iCloud downloads" >&2
  echo "[dry-run] would run: icloudpd -d ${PHOTOS_DIR} -u ${APPLE_ID} ..." >&2
  echo "[dry-run] would run: uv run icloud-drive --dest ${DRIVE_DIR}" >&2
  exit 0
fi

# --- photos -----------------------------------------------------------------
echo "[photos] downloading to ${PHOTOS_DIR}" >&2
PHOTOS_BEFORE="$(find "${PHOTOS_DIR}" -type f 2>/dev/null | wc -l)"
(
  cd "${PROJECT_DIR}"
  uv run icloudpd \
    --directory "${PHOTOS_DIR}" \
    --username "${APPLE_ID}" \
    --password "${ICLOUD_PASSWORD}" \
    --password-provider parameter \
    --folder-structure '{:%Y/%m}' \
    --no-progress-bar
)
PHOTOS_AFTER="$(find "${PHOTOS_DIR}" -type f 2>/dev/null | wc -l)"
echo "[photos] files: ${PHOTOS_BEFORE} → ${PHOTOS_AFTER}" >&2

# --- drive ------------------------------------------------------------------
echo "[drive] downloading to ${DRIVE_DIR}" >&2
DRIVE_BEFORE="$(find "${DRIVE_DIR}" -type f 2>/dev/null | wc -l)"
(
  cd "${PROJECT_DIR}"
  uv run icloud-drive --dest "${DRIVE_DIR}"
)
DRIVE_AFTER="$(find "${DRIVE_DIR}" -type f 2>/dev/null | wc -l)"
echo "[drive] files: ${DRIVE_BEFORE} → ${DRIVE_AFTER}" >&2

echo "[done] photos +$((PHOTOS_AFTER - PHOTOS_BEFORE)), drive +$((DRIVE_AFTER - DRIVE_BEFORE))" >&2

# iCloud → USB Migration

Migrate iCloud Photos, Videos, and Drive files to a local USB drive on Linux.

## Environment

| Component | Detail |
|---|---|
| OS | Ubuntu (Linux 5.15) |
| Python | 3.10, `uv` |
| USB | `/dev/sdc1` — 232.9 GB NTFS, mounted at `/mnt/usb_migration` |
| Apple ID | maplekiyo@yahoo.co.jp |

## Output Structure

```
/media/maplekiyo/
├── icloud_photos/YYYY/MM/IMG_*.{jpg,heic,mov,mp4,...}
└── icloud_drive/          # mirrors iCloud Drive folder tree
```

## Project Structure

```
icloud-migration/
├── .env                   # Apple ID credentials (gitignored)
├── .gitignore
├── pyproject.toml         # deps (icloudpd) + icloud-drive entry point
├── CLAUDE.md
├── src/icloud_migration/
│   ├── __init__.py
│   └── drive.py           # Drive download logic
├── tests/
│   └── test_drive.py
└── migrate.sh             # orchestrator: mount → photos → drive → verify → unmount
```

## Development Strategy

1. Track tasks with `[ ]` / `[X]` in each phase below.
2. All acceptance criteria must be `[X]` before starting the next phase.
3. Review and run tests after each task before marking it done.
4. Every non-trivial function needs a unit test in `tests/`.
5. Commit and push to GitHub after each phase completes.
6. Execute each phase in YOLO mode (no confirmation prompts).
7. **Update CLAUDE.md task checkboxes immediately** as each task and acceptance criterion is completed — edit `[ ]` → `[X]` in this file before moving on. Include the CLAUDE.md update in the phase's commit.

---

## Phase 1: Project Scaffold

### Tasks
- [X] Create `pyproject.toml` (`icloudpd` dep, `icloud-drive` entry point, `pytest` dev dep)
- [X] Create `src/icloud_migration/__init__.py`
- [X] Move `download_drive.py` → `src/icloud_migration/drive.py` (created fresh — no prior file existed)
- [X] Create `tests/test_drive.py` with placeholder
- [X] Add `.gitignore` (`.env`, `.venv/`, `__pycache__/`, `*.pyc`)
- [X] Run `uv sync`; confirm structure matches layout above

### Acceptance Criteria
- [X] `uv sync` succeeds
- [X] `uv run icloud-drive --help` prints usage
- [X] `uv run pytest tests/` exits 0
- [X] `.env` is in `.gitignore`

---

## Phase 2: Drive Download Logic

### Tasks
- [ ] Refactor `drive.py` into `authenticate()`, `download_node()`, `main()`
- [ ] Read credentials from `.env` via `python-dotenv`
- [ ] Handle 2FA (`requires_2fa`) and 2SA (`requires_2sa`) flows
- [ ] Skip files that already exist with non-zero size
- [ ] Write unit tests:
  - [ ] `test_download_node_skips_existing_file`
  - [ ] `test_download_node_downloads_missing_file`
  - [ ] `test_download_node_recurses_into_folder`
  - [ ] `test_download_node_handles_folder_listing_error`
- [ ] Review code; run `uv run pytest`

### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Bad credentials raise a clear error (mocked)
- [ ] Existing files are skipped
- [ ] Folder listing errors log to stderr and don't abort the run

---

## Phase 3: Shell Orchestrator

### Tasks
- [ ] Load `APPLE_ID` / `ICLOUD_PASSWORD` from `.env` in `migrate.sh`
- [ ] Replace `python3 download_drive.py` with `uv run icloud-drive`
- [ ] Abort if USB free space < 10 GB
- [ ] Mount USB if not already mounted
- [ ] Print file counts after downloads; run `sync` and unmount
- [ ] Review `migrate.sh`; dry-run test (no iCloud connection)

### Acceptance Criteria
- [ ] Dry run reaches mount step without errors
- [ ] Script aborts clearly when free space is too low
- [ ] `trap` ensures unmount runs even on failure

---

## Phase 4: Integration & End-to-End

### Tasks
- [ ] Test Photos download (small batch first)
- [ ] Test Drive download
- [ ] Spot-check file integrity (open a sample photo/doc)
- [ ] Confirm idempotency: re-run downloads 0 new files
- [ ] Confirm resume: kill mid-run, re-run, verify continuation

### Acceptance Criteria
- [ ] Photos land in `icloud_photos/YYYY/MM/` with correct dates
- [ ] Drive mirrors iCloud Drive tree exactly
- [ ] Re-run downloads 0 files when nothing changed
- [ ] USB unmounts cleanly with no NTFS errors in `dmesg`

---

## How to Run

```bash
sudo ./migrate.sh
# Prompts for 2FA code from iPhone/Mac if required
```

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| USB out of space | Abort if < 10 GB free before starting |
| Interrupted download | Both tools skip existing files — re-run safely |
| 2FA expiry mid-run | Drive script authenticates independently from Photos |
| NTFS write errors | `ntfs-3g` handles NTFS on Linux reliably |
| iCloud rate limiting | `icloudpd` retries automatically |

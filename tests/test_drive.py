"""Unit tests for icloud_migration.drive."""

from __future__ import annotations

import io
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from icloud_migration import drive


def _make_file_node(name: str, content: bytes = b"hello"):
    node = MagicMock()
    node.name = name
    node.type = "file"
    node.size = len(content)

    @contextmanager
    def fake_open(**kwargs):
        response = MagicMock()
        response.iter_content = lambda chunk_size=None: iter([content])
        yield response

    node.open.side_effect = fake_open
    return node


def _make_folder_node(name: str, children):
    node = MagicMock()
    node.name = name
    node.type = "folder"
    node.get_children.return_value = list(children)
    return node


def test_download_node_skips_existing_file(tmp_path: Path):
    target = tmp_path / "existing.txt"
    target.write_bytes(b"already here")
    node = _make_file_node("existing.txt", content=b"new content")

    downloaded = drive.download_node(node, str(target))

    assert downloaded == 0
    assert target.read_bytes() == b"already here"
    node.open.assert_not_called()


def test_download_node_downloads_missing_file(tmp_path: Path):
    target = tmp_path / "subdir" / "fresh.bin"
    payload = b"\x00\x01\x02fresh-bytes"
    node = _make_file_node("fresh.bin", content=payload)

    downloaded = drive.download_node(node, str(target))

    assert downloaded == 1
    assert target.read_bytes() == payload
    node.open.assert_called_once()


def test_download_node_recurses_into_folder(tmp_path: Path):
    child_a = _make_file_node("a.txt", content=b"AAA")
    child_b = _make_file_node("b.txt", content=b"BBB")
    sub_child = _make_file_node("c.txt", content=b"CCC")
    subfolder = _make_folder_node("sub", [sub_child])
    root = _make_folder_node("root", [child_a, child_b, subfolder])

    dest = tmp_path / "mirror"
    downloaded = drive.download_node(root, str(dest))

    assert downloaded == 3
    assert (dest / "a.txt").read_bytes() == b"AAA"
    assert (dest / "b.txt").read_bytes() == b"BBB"
    assert (dest / "sub" / "c.txt").read_bytes() == b"CCC"


def test_download_node_handles_folder_listing_error(tmp_path: Path):
    bad_folder = _make_folder_node("broken", [])
    bad_folder.get_children.side_effect = RuntimeError("network exploded")

    err = io.StringIO()
    downloaded = drive.download_node(bad_folder, str(tmp_path / "out"), output=err)

    assert downloaded == 0
    assert "broken" in err.getvalue()
    assert "network exploded" in err.getvalue()


def test_authenticate_raises_clear_error_on_bad_credentials():
    from pyicloud.exceptions import PyiCloudFailedLoginException

    with patch.object(
        drive, "PyiCloudService", side_effect=PyiCloudFailedLoginException("nope")
    ):
        with pytest.raises(RuntimeError, match="iCloud login failed"):
            drive.authenticate("user@example.com", "wrong-password")

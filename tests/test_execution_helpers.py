"""Unit tests for workflow_execution helper functions."""
import os
import tempfile

from crud.workflow_execution import (
    _parse_exit_code,
    _clean_command,
    _fetch_aiod_content,
)


def test_parse_exit_code():
    assert _parse_exit_code("", "finished") == 0
    assert _parse_exit_code("Exit code: 3 boom", "failed") == 3
    assert _parse_exit_code("no number here", "failed") == 1   # default non-zero
    assert _parse_exit_code("", "running") is None


def test_clean_command_strips_cp_and_cd_prefix():
    # REANA wraps user commands with a 'cd ... &&' prefix and a '; cp -r' suffix
    raw = "cd /var/reana/users/x/run && echo hi ; cp -r /a/* /b"
    assert _clean_command(raw) == "echo hi"


def test_fetch_aiod_content_file(tmp_path):
    p = tmp_path / "data.bin"
    p.write_bytes(b"hello-bytes")
    assert _fetch_aiod_content("file://" + str(p)) == b"hello-bytes"


def test_fetch_aiod_content_http(monkeypatch):
    class _Resp:
        content = b"remote-bytes"

        def raise_for_status(self):
            pass

    monkeypatch.setattr("crud.workflow_execution.requests.get",
                        lambda *a, **k: _Resp())
    assert _fetch_aiod_content("http://host/data") == b"remote-bytes"

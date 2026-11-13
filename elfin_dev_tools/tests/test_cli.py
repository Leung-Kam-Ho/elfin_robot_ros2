import pytest

from elfin_dev_tools.cli import _format_compact, _format_table, main

PAYLOAD = {
    "stale": False,
    "age_sec": 0.031,
    "stamp": {"sec": 1, "nanosec": 0},
    "names": ["elfin_joint1", "elfin_joint2"],
    "positions": [0.0, -0.5235987755982988],
    "positions_deg": [0.0, -30.0],
}


def test_table_contains_joints_and_degrees():
    text = _format_table(PAYLOAD)
    assert "elfin_joint1" in text
    assert "elfin_joint2" in text
    assert "-30.000" in text
    assert "[STALE]" not in text


def test_table_marks_stale_payload():
    text = _format_table({**PAYLOAD, "stale": True})
    assert "[STALE]" in text


def test_compact_output():
    text = _format_compact(PAYLOAD)
    assert text.startswith("age=0.031s j1=0.00 j2=-30.00")


def test_compact_marks_stale_payload():
    text = _format_compact({**PAYLOAD, "stale": True})
    assert text.startswith("stale age=")


def test_version_exits_cleanly(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    assert "elfin" in capsys.readouterr().out

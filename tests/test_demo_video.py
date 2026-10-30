"""Demo video script: slide content comes from the real CLI run, narration stays plain and honest."""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("make_demo_video", ROOT / "scripts" / "make_demo_video.py")
mdv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mdv)

HYPE = re.compile(r"\b(seamless\w*|revolution\w*|leverag\w*|game.?chang\w*|cutting.?edge|unlock\w*|supercharg\w*|effortless\w*)\b", re.I)


def _slides(tmp_path, monkeypatch):
    monkeypatch.setattr(mdv, "screenshot", lambda html, png: False)  # no browser needed in tests
    return mdv.build_slides(tmp_path, "2026-11-01", tests=1)


def test_short_id():
    assert mdv.short("PP-D-SYNTH-0003") == "synthetic dispute 3"


def test_slides_use_cli_output_and_plain_narration(tmp_path, monkeypatch):
    slides = _slides(tmp_path, monkeypatch)
    text = "\n".join("\n".join(body) for _t, body, *_ in slides)
    narration = " ".join(s[3] for s in slides)
    assert "5 disputes from mock -> data/disputes.json" in text
    assert "| PP-D-SYNTH-0003 | 2 | urgent | 310.00 USD |" in text
    assert "recorded approval: provide_evidence on PP-D-SYNTH-0001" in text
    assert "synthetic" in slides[0][3].lower()
    assert not HYPE.search(narration)
    assert "contesting 4 and accepting 1" in narration


def test_cli_runs_do_not_touch_repo_data(tmp_path, monkeypatch):
    repo = [ROOT / "data" / n for n in ("approvals.json", "disputes.json", "dashboard.html")]
    before = {p: p.read_bytes() if p.exists() else None for p in repo}
    _slides(tmp_path, monkeypatch)
    assert (tmp_path / "data" / "approvals.json").exists()
    assert {p: p.read_bytes() if p.exists() else None for p in repo} == before

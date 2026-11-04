import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "at/skills/diagnose/scripts/analyze_deps.py"
PEEK = Path(__file__).parent / "fixtures/peek.json"
CORE = "src/python/klaviyo/core:lib"


def run(*args):
    done = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(PEEK), *args],
        capture_output=True,
        check=False,
        text=True,
    )
    return done.returncode, done.stdout


def test_without_targets_prints_summary_and_asks_for_targets():
    code, out = run()
    assert code == 0
    assert "=== Changeset Summary (7 total targets) ===" in out
    assert "  python_sources: 4" in out
    assert "Pass changed targets as arguments for path analysis." in out
    assert "=== Changed Targets" not in out


def test_changed_target_lists_images_chains_and_fanout():
    code, out = run(CORE)
    assert code == 0
    assert f"  {CORE} [python_sources]" in out
    assert "=== Docker Images Triggered (2) ===" in out
    assert "  Chain (length 3):" in out
    assert "→ src/python/klaviyo/worker:image [docker_image]" in out
    assert "  Chain (length 5):" in out
    assert "=== High-Fanout Intermediaries ===" in out
    assert "1x  src/python/klaviyo/worker:lib [python_sources]" in out


def test_unknown_target_is_reported_and_nothing_else_runs():
    code, out = run("nope:lib")
    assert code == 0
    assert "Warning: targets not found in peek.json: ['nope:lib']" in out
    assert "No matching changed targets found." in out


def test_missing_argument_exits_one_with_usage():
    done = subprocess.run(
        [sys.executable, "-I", str(SCRIPT)], capture_output=True, text=True, check=False
    )
    assert done.returncode == 1
    assert "Usage:" in done.stdout

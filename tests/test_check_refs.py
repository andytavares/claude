import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "at/skills/research/check_refs.py"


def repo(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/cart.py").write_text(
        "def total(items):\n    return sum(items)\n\n\ndef tax(amount):\n    return amount\n"
    )
    return tmp_path


def check(root, text):
    doc = root / "doc.html"
    doc.write_text(text)
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(doc)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_a_valid_reference_passes(tmp_path):
    done = check(repo(tmp_path), "<td><code>src/cart.py:2</code></td>")
    assert done.returncode == 0, done.stdout


def test_a_line_past_the_end_fails(tmp_path):
    done = check(repo(tmp_path), "<td><code>src/cart.py:40</code></td>")
    assert done.returncode == 1
    assert "src/cart.py:40" in done.stdout


def test_a_missing_file_fails(tmp_path):
    done = check(repo(tmp_path), "<td><code>src/basket.py:1</code></td>")
    assert done.returncode == 1
    assert "src/basket.py" in done.stdout


def test_ranges_and_lists_check_every_line(tmp_path):
    root = repo(tmp_path)
    assert check(root, "<code>src/cart.py:1-6</code>").returncode == 0
    assert check(root, "<code>src/cart.py:1,6</code>").returncode == 0
    assert check(root, "<code>src/cart.py:5-9</code>").returncode == 1
    assert check(root, "<code>src/cart.py:2,9</code>").returncode == 1


def test_a_quote_after_a_reference_must_be_on_the_cited_line(tmp_path):
    root = repo(tmp_path)
    assert (
        check(root, "<code>src/cart.py:5</code> <code>def tax</code>").returncode == 0
    )
    done = check(root, "<code>src/cart.py:2</code> <code>def tax</code>")
    assert done.returncode == 1
    assert "def tax" in done.stdout


def test_a_code_span_in_other_text_is_not_a_quote(tmp_path):
    text = "<td><code>src/cart.py:2</code></td><td>Rename to <code>add_tax</code>.</td>"
    assert check(repo(tmp_path), text).returncode == 0

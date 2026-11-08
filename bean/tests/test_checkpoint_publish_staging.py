"""Exercise the actual GitHub Actions checkpoint staging code in an isolated Git repo."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/invoke-bean.yml"

def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout

def snippet():
    text = WORKFLOW.read_text()
    step = text.split("      - name: Save synthetic BEAN brain checkpoint to GitHub main", 1)[1]
    step = step.split("      - name: Preserve verifiable public receipt", 1)[0]
    match = re.search(r"^          python - <<'PY'\n(.*?)^          PY$", step, re.M | re.S)
    assert match, "workflow staging code missing"
    return "\n".join(line[10:] for line in match.group(1).splitlines()) + "\n"

def setup(tmp_path, *, missing=False, rogue=False):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "synthetic@example.invalid")
    git(tmp_path, "config", "user.name", "Synthetic Test")
    (tmp_path / "README.md").write_text("baseline")
    git(tmp_path, "add", "README.md")
    git(tmp_path, "commit", "-qm", "baseline")
    root = tmp_path / "research/github_brain"
    root.mkdir(parents=True)
    core = "bean_memory.sqlite3.g000002.gz"
    reasoning = "bean_reasoning.sqlite3.g000002.gz"
    import gzip
    import hashlib
    import sqlite3
    from scripts.invoke_bean import canonical
    databases = {}
    for name, archive in (("core", core), ("reasoning", reasoning)):
        db = tmp_path / (name + ".sqlite3")
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE receipt (value TEXT)")
            conn.execute("INSERT INTO receipt VALUES ('synthetic')")
        payload = db.read_bytes()
        (root / archive).write_bytes(gzip.compress(payload, mtime=0))
        databases[name] = {"archive": archive, "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
    receipt = {"schema": "bean.github.invoke.v1", "synthetic_only": True,
               "generation": 2, "databases": databases}
    receipt["receipt_sha256"] = hashlib.sha256(canonical(receipt)).hexdigest()
    (root / "manifest.json").write_text(json.dumps(receipt))
    if missing:
        (root / reasoning).unlink()
    if rogue:
        (root / "unrelated.txt").write_text("not-for-publication")

def execute(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(WORKFLOW.parents[2]))
    return subprocess.run([sys.executable, "-c", snippet()], cwd=tmp_path,
                          env=env, capture_output=True, text=True)

def test_workflow_publication_stages_exact_allowlist(tmp_path):
    setup(tmp_path, rogue=True)
    result = execute(tmp_path)
    assert result.returncode == 0, result.stderr
    staged = set(git(tmp_path, "diff", "--cached", "--name-only").splitlines())
    assert staged == {"research/github_brain/" + name for name in (
        "manifest.json", "bean_memory.sqlite3.g000002.gz",
        "bean_reasoning.sqlite3.g000002.gz")}

def test_workflow_publication_rejects_missing_archive(tmp_path):
    setup(tmp_path, missing=True)
    result = execute(tmp_path)
    assert result.returncode != 0
    assert not git(tmp_path, "diff", "--cached", "--name-only").strip()

def test_workflow_publication_rejects_dirty_index(tmp_path):
    """Run the actual workflow preflight, not a hand-written imitation."""
    setup(tmp_path)
    (tmp_path / "unrelated.txt").write_text("pre-staged")
    git(tmp_path, "add", "unrelated.txt")
    workflow = WORKFLOW.read_text()
    section = workflow.split("      - name: Save synthetic BEAN brain checkpoint to GitHub main", 1)[1]
    section = section.split("      - name: Preserve verifiable public receipt", 1)[0]
    # Extract the real Bash preflight preceding the Python staging heredoc.
    script = section.split("          python - <<'PY'", 1)[0]
    lines = [line[10:] for line in script.splitlines() if line.startswith("          ")]
    assert "if ! git diff --cached --quiet; then" in lines
    assert "exit 1" in lines
    result = subprocess.run(["bash", "-euo", "pipefail", "-c", "\n".join(lines)],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode != 0
    assert "index was already staged" in result.stderr
    assert git(tmp_path, "diff", "--cached", "--name-only").strip() == "unrelated.txt"


def test_workflow_publication_rejects_archive_path_escape(tmp_path):
    """A forged manifest must not make git stage paths outside the brain directory."""
    setup(tmp_path)
    manifest = tmp_path / "research/github_brain/manifest.json"
    receipt = json.loads(manifest.read_text())
    receipt["databases"]["core"]["archive"] = "../../README.md"
    manifest.write_text(json.dumps(receipt))
    result = execute(tmp_path)
    assert result.returncode != 0
    assert "unexpected checkpoint archive" in result.stderr
    assert not git(tmp_path, "diff", "--cached", "--name-only").strip()


def test_workflow_publication_rejects_non_synthetic_manifest(tmp_path):
    """Public staging must refuse an explicitly non-synthetic checkpoint."""
    setup(tmp_path)
    manifest = tmp_path / "research/github_brain/manifest.json"
    receipt = json.loads(manifest.read_text())
    receipt["synthetic_only"] = False
    manifest.write_text(json.dumps(receipt))
    result = execute(tmp_path)
    assert result.returncode != 0
    assert not git(tmp_path, "diff", "--cached", "--name-only").strip()


def test_workflow_publication_rejects_symlink_archive(tmp_path):
    """A referenced archive must be a real file, never a Git symlink pointer."""
    setup(tmp_path)
    root = tmp_path / "research/github_brain"
    archive = root / "bean_memory.sqlite3.g000002.gz"
    archive.unlink()
    archive.symlink_to(tmp_path / "README.md")
    result = execute(tmp_path)
    assert result.returncode != 0
    assert "symlink checkpoint archive forbidden" in result.stderr
    assert not git(tmp_path, "diff", "--cached", "--name-only").strip()


def test_workflow_publication_rejects_corrupt_archive(tmp_path):
    setup(tmp_path)
    archive = tmp_path / "research/github_brain/bean_memory.sqlite3.g000002.gz"
    archive.write_bytes(b"not a gzip SQLite archive")
    result = execute(tmp_path)
    assert result.returncode != 0
    assert not git(tmp_path, "diff", "--cached", "--name-only").strip()


def test_workflow_publication_rejects_forged_receipt(tmp_path):
    setup(tmp_path)
    manifest = tmp_path / "research/github_brain/manifest.json"
    receipt = json.loads(manifest.read_text())
    receipt["events"] = 999999
    manifest.write_text(json.dumps(receipt))
    result = execute(tmp_path)
    assert result.returncode != 0
    assert not git(tmp_path, "diff", "--cached", "--name-only").strip()

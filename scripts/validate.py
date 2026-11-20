"""Checks the registry index.

Usage:
  python scripts/validate.py                  check every entry's format
  python scripts/validate.py --base origin/main
      also compare with the base branch: published versions may not be
      removed or changed (except `yanked`), the git URL of a package may
      not change, and every new version's commit must exist in its
      repository with a matching name and version in elomar.toml.

Needs Python 3.11+ (tomllib) and git. Exits 1 if anything is wrong.
"""

import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ROOT / "packages"
NAME = re.compile(r"^[a-z_][a-z0-9_]*$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
# Semantic versioning 2.0.0 (without build metadata).
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$"
)

errors = []


def fail(where, message):
    errors.append(f"{where}: {message}")


def check_entry(path, data):
    name = path.stem
    if not NAME.match(name) or name in ("app", "std"):
        fail(path.name, "file name must be a package name: lowercase letters, digits and `_`, not `app` or `std`")
    allowed = {"description", "git", "versions"}
    for key in data:
        if key not in allowed:
            fail(path.name, f"unknown key `{key}`")
    if not isinstance(data.get("description", ""), str):
        fail(path.name, "`description` must be text")
    git = data.get("git")
    if not isinstance(git, str) or not git.startswith("https://"):
        fail(path.name, "`git` must be an https:// repository URL")
    versions = data.get("versions", [])
    if not isinstance(versions, list) or not versions:
        fail(path.name, "needs at least one [[versions]] entry")
        return
    seen = set()
    for v in versions:
        where = f"{path.name} {v.get('version', '?')}"
        for key in v:
            if key not in ("version", "commit", "yanked"):
                fail(where, f"unknown key `{key}`")
        version = v.get("version")
        if not isinstance(version, str) or not SEMVER.match(version):
            fail(where, "`version` must look like 1.2.3")
        elif version in seen:
            fail(where, "version listed twice")
        seen.add(version)
        if not isinstance(v.get("commit"), str) or not COMMIT.match(v["commit"]):
            fail(where, "`commit` must be a full 40-character lowercase commit hash")
        if not isinstance(v.get("yanked", False), bool):
            fail(where, "`yanked` must be true or false")


def load(path):
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        fail(path.name, f"not valid TOML: {e}")
        return None


def base_entry(base, name):
    out = subprocess.run(
        ["git", "show", f"{base}:packages/{name}.toml"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    if out.returncode != 0:
        return None
    return tomllib.loads(out.stdout)


def check_commit(name, git, version, commit):
    """Fetches the commit and compares its elomar.toml."""
    where = f"{name} {version}"
    with tempfile.TemporaryDirectory() as tmp:
        def run(*args):
            return subprocess.run(["git", *args], cwd=tmp, capture_output=True,
                                  text=True, encoding="utf-8")
        run("init", "--quiet")
        fetched = run("fetch", "--quiet", "--depth", "1", git, commit)
        if fetched.returncode != 0:
            fail(where, f"cannot fetch commit {commit} from {git}: {fetched.stderr.strip()}")
            return
        shown = run("show", "FETCH_HEAD:elomar.toml")
        if shown.returncode != 0:
            fail(where, "the commit has no elomar.toml at the repository root")
            return
        try:
            package = tomllib.loads(shown.stdout).get("package", {})
        except tomllib.TOMLDecodeError as e:
            fail(where, f"elomar.toml of the commit is not valid TOML: {e}")
            return
        if package.get("name") != name:
            fail(where, f"elomar.toml says name = {package.get('name')!r}, expected {name!r}")
        if package.get("version") != version:
            fail(where, f"elomar.toml says version = {package.get('version')!r}, expected {version!r}")


def compare(base, path, data):
    name = path.stem
    old = base_entry(base, name)
    old_versions = {v["version"]: v for v in (old or {}).get("versions", [])}
    if old and old.get("git") != data.get("git"):
        fail(path.name, "the `git` URL of a published package cannot change")
    new_versions = {v.get("version"): v for v in data.get("versions", [])}
    for version, v in old_versions.items():
        if version not in new_versions:
            fail(path.name, f"published version {version} cannot be removed (set `yanked = true` instead)")
        elif new_versions[version].get("commit") != v.get("commit"):
            fail(path.name, f"the commit of published version {version} cannot change")
    for version, v in new_versions.items():
        if version not in old_versions and isinstance(v.get("commit"), str) and isinstance(data.get("git"), str):
            check_commit(name, data["git"], version, v["commit"])


def removed_files(base):
    out = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=D", base, "--", "packages"],
        cwd=ROOT, capture_output=True, text=True,
    )
    return [line for line in out.stdout.splitlines() if line.endswith(".toml")]


def main():
    base = None
    if len(sys.argv) == 3 and sys.argv[1] == "--base":
        base = sys.argv[2]
    elif len(sys.argv) != 1:
        sys.exit(__doc__)
    files = sorted(PACKAGES.glob("*.toml")) if PACKAGES.is_dir() else []
    for path in files:
        data = load(path)
        if data is None:
            continue
        check_entry(path, data)
        if base:
            compare(base, path, data)
    if base:
        for gone in removed_files(base):
            fail(gone, "a published package cannot be removed")
    if errors:
        print("Registry check failed:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print(f"ok: {len(files)} package(s)")


if __name__ == "__main__":
    main()

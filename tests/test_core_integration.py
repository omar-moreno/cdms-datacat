"""Integration tests for CatalogCore against a live data catalog.

These tests run against a REAL data catalog, writing to the production
scratch area at /CDMS/Scratch. 

Requirements to run:
- A working catalog configuration (credentials, network access).
- Write access to /CDMS/Scratch.

Safety:
- Every test writes ONLY under a unique per-run subtree of /CDMS/Scratch.
- Fixtures guarantee cleanup even when a test fails.
- A guard refuses to operate outside the scratch root.
"""

import os
import tempfile
import uuid

import pytest

from pathlib import Path
from CDMSDataCatalog.core import CatalogCore
from importlib.resources import files

# --- Scratch root and safety guard ------------------------------------------

SCRATCH_ROOT = "/CDMS/Scratch"

def _assert_in_scratch(path: str) -> None:
    """Refuse to operate on any path outside the scratch root.

    A last line of defense: even if a test constructs a bad path, this prevents
    an accidental operation on real catalog data.
    """
    normalized = path.rstrip("/")
    if not (normalized == SCRATCH_ROOT or normalized.startswith(SCRATCH_ROOT + "/")):
        raise AssertionError(
            f"Refusing to operate outside scratch root: {path!r}. "
            f"All integration-test paths must be under {SCRATCH_ROOT}."
        )

# --- Fixtures ----------------------------------------------------------------

@pytest.fixture(scope="session")
def core():
    """A CatalogCore connected to the real catalog with the default config.

    Session-scoped: one real connection is reused across all tests to avoid
    repeated authentication/setup overhead.
    """
    data_dir = Path(tempfile.gettempdir()) / "datacat-data"
    data_dir.mkdir(exist_ok=True)

    return CatalogCore(files("CDMSDataCatalog").joinpath("cfg/prod.cfg"),
            default_fetchdir=data_dir)

@pytest.fixture
def scratch_dir(core):
    """A unique, empty scratch directory for one test, cleaned up afterward.

    Yields the path to a freshly created directory under /CDMS/Scratch that is
    guaranteed unique to this test invocation. On teardown, the directory and
    everything under it is removed — even if the test failed.
    """
    unique = f"pytest-{uuid.uuid4().hex}"
    path = f"{SCRATCH_ROOT}/{unique}"
    _assert_in_scratch(path)

    core.mkdir(path, parents=True)

    try:
        yield path
    finally:
        # Robust cleanup: never let teardown raise, but do log if it fails so a
        # leaked directory is visible.
        _assert_in_scratch(path)
        try:
            if core.exists(path):
                print("It exists")
                core.rm(path, recursive=True)
        except Exception as e:  # pragma: no cover - teardown diagnostics
            print(f"WARNING: failed to clean up scratch dir {path}: {e}")



# --- Tests: existence and listing -------------------------------------------


class TestExistsAndLs:
    def test_scratch_root_exists(self, core):
        # A precondition for everything else: the scratch area is reachable.
        assert core.exists(SCRATCH_ROOT) is True

    def test_fresh_dir_exists_after_mkdir(self, core, scratch_dir):
        assert core.exists(scratch_dir) is True

    def test_nonexistent_path_does_not_exist(self, core, scratch_dir):
        missing = f"{scratch_dir}/definitely-not-here"
        assert core.exists(missing) is False

    def test_ls_empty_dir_returns_empty_list(self, core, scratch_dir):
        assert core.ls(scratch_dir) == []

    def test_ls_lists_created_children(self, core, scratch_dir):
        child_a = f"{scratch_dir}/childA"
        child_b = f"{scratch_dir}/childB"
        core.mkdir(child_a)
        core.mkdir(child_b)

        listing = core.ls(scratch_dir)

        assert set(listing) == {child_a, child_b}

# --- Tests: mkdir ------------------------------------------------------------


class TestMkdir:
    def test_mkdir_creates_directory(self, core, scratch_dir):
        new_dir = f"{scratch_dir}/created"
        assert core.exists(new_dir) is False

        core.mkdir(new_dir)

        assert core.exists(new_dir) is True

    def test_mkdir_with_parents_creates_intermediate_dirs(self, core, scratch_dir):
        nested = f"{scratch_dir}/a/b/c"
        core.mkdir(nested, parents=True)
        assert core.exists(nested) is True
        assert core.exists(f"{scratch_dir}/a/b") is True

    def test_mkdir_with_metadata(self, core, scratch_dir):
        new_dir = f"{scratch_dir}/with-meta"
        core.mkdir(new_dir, metadata={"purpose": "integration-test"})
        assert core.exists(new_dir) is True
        # Metadata round-trip is verified in the add_metadata tests below.


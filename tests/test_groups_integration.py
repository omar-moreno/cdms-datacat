"""Integration tests for Groups against a live data catalog.

These tests run against the production data catalog, writing to the
scratch area at /CDMS/Scratch. They verify end-to-end group behavior that the
mocked unit tests cannot: real open/closed state transitions, metadata
persistence, and dataset<->group dependency linking.

Requirements to run:
- A working catalog configuration (credentials, network access).
- Write access to /CDMS/Scratch.

Safety:
- Every test writes ONLY under a unique per-run subtree of /CDMS/Scratch.
- Fixtures guarantee cleanup even when a test fails.
- A guard refuses to operate outside the scratch root.
"""

import tempfile
import uuid
from importlib.resources import files
from pathlib import Path

import pytest

from CDMSDataCatalog import facilities, paths
from CDMSDataCatalog.core import CatalogCore
from CDMSDataCatalog.datasets import Datasets
from CDMSDataCatalog.dependents import Dependents
from CDMSDataCatalog.groups import Groups

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

    return CatalogCore(
        files("CDMSDataCatalog").joinpath("cfg/prod.cfg"), default_fetchdir=data_dir
    )


@pytest.fixture(scope="session")
def datasets(core):
    """A real Datasets component, wired exactly as the facade wires it."""
    return Datasets(core, paths, facilities)


@pytest.fixture(scope="session")
def dependents(core):
    """A real Dependents component."""
    return Dependents(core)


@pytest.fixture(scope="session")
def groups(core, dependents, datasets):
    # Groups builds its own Dependents/Datasets internally from core.
    return Groups(core, dependents, datasets)


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
                core.rm(path, recursive=True)
        except Exception as e:  # pragma: no cover - teardown diagnostics
            print(f"WARNING: failed to clean up scratch dir {path}: {e}")


@pytest.fixture
def scratch_dataset(core, scratch_dir, datasets):
    """Register a real dataset under the scratch dir and yield its catalog path.

    Builds a minimal CDMSDataset via the base constructor, forces its
    relativePath into the scratch tree, and registers it through Datasets.add.
    If registration is unavailable in this environment (backend rejects the
    dummy resource, etc.), the test is skipped rather than failed.
    """
    from CDMSDataCatalog.CDMSDataset import CDMSDataset

    ds_name = f"testfile-{uuid.uuid4().hex}.txt"
    ds_catalog_path = f"{scratch_dir}/{ds_name}"
    _assert_in_scratch(ds_catalog_path)

    # Build a minimal dataset via the base constructor.
    cds = CDMSDataset(
        name=ds_name,
        filePath=f"/sdf/data/scdms/data/CDMS/Scratch/{ds_name}",
        dataType="Scratch",  # arbitrary non-DatacatQuery value
        site="SLAC",  # VERIFY: a site the backend accepts for scratch
        fileFormat="txt",  # must be a key in fileFormats
    )

    # The relative path is already derived in the constructor but is set here
    # to avoid writing to other areas.
    cds.relativePath = scratch_dir

    try:
        datasets.add(cds, catch_errors=False)
    except Exception as e:
        pytest.skip(f"Dataset registration unavailable in this environment: {e}")

    yield ds_catalog_path
    # Cleanup handled by scratch_dir teardown (recursive rm of the whole tree).


# --- Tests: create / get ------------------------------------------------------------


class TestCreateAndGet:
    def test_create_group(self, groups, core, scratch_dir):
        group_path = f"{scratch_dir}/grp"
        assert core.exists(group_path) is False
        groups.create(group_path)
        assert core.exists(group_path) is True

    def test_created_group_is_open_by_default(self, groups, scratch_dir):
        group_path = f"{scratch_dir}/grp-open"
        groups.create(group_path)
        assert groups.group_is_open(groups.get(group_path)) is True

    def test_create_with_extra_metadata(self, groups, scratch_dir):
        group_path = f"{scratch_dir}/grp-meta"
        groups.create(group_path, metadata={"purpose": "integration-test"})
        group = groups.get(group_path)
        assert group.metadata.get("purpose") == "integration-test"
        assert group.metadata.get("State") == "Open"

    def test_create_existing_raises(self, groups, scratch_dir):
        group_path = f"{scratch_dir}/grp-dup"
        groups.create(group_path)
        with pytest.raises(FileExistsError):
            groups.create(group_path)


# --- Tests: open / close ------------------------------------------------------------


class TestStateTransitions:
    def test_close_group(self, groups, scratch_dir):
        group_path = f"{scratch_dir}/grp-close"
        groups.create(group_path)
        assert groups.group_is_open(groups.get(group_path)) is True
        groups.close(group_path)
        assert groups.group_is_open(groups.get(group_path)) is False

    def test_open_group(self, groups, scratch_dir):
        group_path = f"{scratch_dir}/grp-reopen"
        groups.create(group_path)
        groups.close(group_path)
        assert groups.group_is_open(groups.get(group_path)) is False
        groups.open(group_path)
        assert groups.group_is_open(groups.get(group_path)) is True

    def test_close_preserves_other_metadata(self, groups, scratch_dir):
        """Does closing a group drop its other metadata?

        End-to-end verification of the add_metadata(replace=True) behavior that
        mocks could not answer. If this fails, close() is wiping keys.
        """
        group_path = f"{scratch_dir}/grp-preserve"
        groups.create(group_path, metadata={"purpose": "keepme"})
        groups.close(group_path)
        group = groups.get(group_path)
        assert group.metadata.get("State") == "Closed"
        assert group.metadata.get("purpose") == "keepme"  # the key test


# --- Tests: retrieve_files on empty group (no dataset creation needed) --------------


class TestRetrieveEmpty:
    def test_retrieve_files_empty_group(self, groups, scratch_dir):
        group_path = f"{scratch_dir}/grp-empty"
        groups.create(group_path)
        assert groups.retrieve_files(group_path) == []


# --- Tests: add_files validation (no real datasets needed) --------------------------


class TestAddFilesValidation:
    def test_add_to_closed_group_raises(self, groups, scratch_dir):
        group_path = f"{scratch_dir}/grp-closed"
        groups.create(group_path)
        groups.close(group_path)
        dataset_path = "/CDMS/Scratch/test_file.txt"
        with pytest.raises(Exception, match="Closed"):
            groups.add_files(group_path, [dataset_path])

    def test_unrecognized_path_format_raises(self, groups, scratch_dir):
        group_path = f"{scratch_dir}/grp-badpath"
        groups.create(group_path)
        with pytest.raises(Exception, match="Unrecognized"):
            groups.add_files(group_path, ["no-cdms-segment.txt"])


# --- Tests: add/remove files --------------------------------------------------------


class TestAddRemoveFiles:
    def test_add_file_to_open_group(self, groups, scratch_dir, scratch_dataset):
        group_path = f"{scratch_dir}/grp-addfiles"
        groups.create(group_path)

        groups.add_files(group_path, [scratch_dataset])

        members = groups.retrieve_files(group_path)

        assert len(members) >= 1

    def test_remove_file_from_group(self, groups, scratch_dir, scratch_dataset):
        group_path = f"{scratch_dir}/grp-removefiles"
        groups.create(group_path)
        groups.add_files(group_path, [scratch_dataset])
        assert len(groups.retrieve_files(group_path)) >= 1

        groups.remove_files(group_path, [scratch_dataset])

        assert len(groups.retrieve_files(group_path)) == 0

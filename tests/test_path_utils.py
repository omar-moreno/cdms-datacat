"""Unit tests for the path_utils module."""

from CDMSDataCatalog.path_utils import normalize_path


class TestNormalizePath:
    """Test suite for the normalize_path function.

    This class contains unit tests to verify the correct behavior of the
    `normalize_path` function from the `CDMSDataCatalog.path_utils` module.
    The function ensures that all CDMS data catalog paths start with '/CDMS/'
    and have no trailing slashes.
    """

    def test_empty_string_returns_default(self):
        """Test that empty string input returns '/CDMS' as default.

        This verifies the baseline behavior when no path is provided.
        """
        assert normalize_path("") == "/CDMS"

    def test_none_returns_default(self):
        """Test that None input returns '/CDMS' as default.

        This ensures the function handles None gracefully without raising
        exceptions.
        """
        assert normalize_path(None) == "/CDMS"

    def test_already_starts_with_cdms(self):
        """Test that paths already starting with '/CDMS' remain unchanged.

        This verifies that the function does not duplicate the '/CDMS' prefix
        when it is already present. Trailing slashes should still be removed.
        """
        assert normalize_path("/CDMS/Existing") == "/CDMS/Existing"
        assert normalize_path("/CDMS/Existing/") == "/CDMS/Existing"

    def test_adds_cdms_prefix_when_missing(self):
        """Test that paths without '/CDMS' prefix have it prepended.

        This covers two cases:
        1. Absolute paths starting with '/' but not '/CDMS'
        2. Relative paths without any leading '/'

        """
        assert normalize_path("/CUTE/Raw/Run1") == "/CDMS/CUTE/Raw/Run1"
        assert normalize_path("Raw/Run1") == "/CDMS/Raw/Run1"

    def test_removes_trailing_slash(self):
        """Test that trailing slashes are stripped from the output.

        This ensures consistent path formatting regardless of input
        trailing slash count.

        """
        assert normalize_path("/CDMS/Test/") == "/CDMS/Test"
        assert normalize_path("/CDMS/Test//") == "/CDMS/Test"

    def test_handles_double_leading_slashes(self):
        """Test that double or triple leading slashes are normalized.

        This verifies the function handles malformed input with multiple
        leading slashes without introducing duplicate prefixes.

        """
        assert normalize_path("//CUTE/Raw") == "/CDMS/CUTE/Raw"
        assert normalize_path("///Test/Data") == "/CDMS/Test/Data"

import substrate.execution.bridge  # noqa: F401 — ensure namespace pkg resolves before collection


def pytest_ignore_collect(collection_path, config):
    """Skip standalone script-style test files that use sys.exit() instead of pytest."""
    if collection_path.suffix == ".py" and collection_path.name.startswith("test_"):
        content = collection_path.read_text()
        has_test_functions = "def test_" in content
        has_sys_exit = "sys.exit(" in content
        if has_sys_exit and not has_test_functions:
            return True
    return None

"""Phase 6H — Config system and structured logging tests."""

import sys
import os

sys.path.insert(0, "/opt/OS")
os.environ.setdefault("UMH_API_KEY", "test-key-phase6h")
os.environ["UMH_TASK_BACKEND"] = "memory"

import json
import logging
import tempfile
import unittest
from unittest.mock import MagicMock, patch


class TestConfig(unittest.TestCase):
    """Config values have defaults, env overrides work, types correct."""

    def test_defaults_exist(self):
        from umh.core.config import (
            API_HOST,
            API_PORT,
            DB_PATH,
            LOG_DIR,
            LOG_LEVEL,
            MAX_STEPS,
            RETRY_BACKOFF,
            RETRY_MAX_ATTEMPTS,
            TASK_BACKEND,
            WORKER_AUTO_START,
            WORKER_POLL_INTERVAL,
        )

        self.assertEqual(API_PORT, 8000)
        self.assertEqual(API_HOST, "127.0.0.1")
        self.assertTrue(DB_PATH.endswith("tasks.sqlite"))
        self.assertEqual(WORKER_POLL_INTERVAL, 2.0)
        self.assertIs(WORKER_AUTO_START, True)
        self.assertEqual(RETRY_MAX_ATTEMPTS, 2)
        self.assertEqual(RETRY_BACKOFF, 5.0)
        self.assertEqual(LOG_LEVEL, "INFO")
        self.assertEqual(MAX_STEPS, 10)
        # TASK_BACKEND overridden by test env setup
        self.assertEqual(TASK_BACKEND, "memory")

    def test_env_override(self):
        from umh.core import config as cfg

        # Set an env var and confirm _int reads it
        os.environ["_TEST_OVERRIDE_INT"] = "7777"
        self.assertEqual(cfg._int("_TEST_OVERRIDE_INT", 9999), 7777)
        os.environ.pop("_TEST_OVERRIDE_INT", None)
        # Missing var returns default
        self.assertEqual(cfg._int("UMH_NONEXISTENT_INT", 42), 42)

    def test_types(self):
        from umh.core.config import (
            API_HOST,
            API_PORT,
            LOG_DIR,
            RETRY_BACKOFF,
            WORKER_AUTO_START,
            WORKER_POLL_INTERVAL,
        )

        self.assertIsInstance(API_PORT, int)
        self.assertIsInstance(API_HOST, str)
        self.assertIsInstance(WORKER_POLL_INTERVAL, float)
        self.assertIsInstance(WORKER_AUTO_START, bool)
        self.assertIsInstance(RETRY_BACKOFF, float)
        self.assertIsInstance(LOG_DIR, str)

    def test_bool_parsing(self):
        from umh.core.config import _bool

        self.assertTrue(_bool("_TEST_BOOL_T", True))
        self.assertFalse(_bool("_TEST_BOOL_F", False))
        os.environ["_TEST_BOOL_YES"] = "yes"
        self.assertTrue(_bool("_TEST_BOOL_YES", False))
        os.environ["_TEST_BOOL_ONE"] = "1"
        self.assertTrue(_bool("_TEST_BOOL_ONE", False))
        os.environ["_TEST_BOOL_NO"] = "no"
        self.assertFalse(_bool("_TEST_BOOL_NO", True))
        # Cleanup
        for k in ("_TEST_BOOL_YES", "_TEST_BOOL_ONE", "_TEST_BOOL_NO"):
            os.environ.pop(k, None)


class TestLogging(unittest.TestCase):
    """Structured logging setup, formatters, and handlers."""

    def test_setup_creates_log_dir(self):
        from umh.core.logging_config import setup_logging

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, "nested", "logs")
            setup_logging(log_dir=log_dir, level="DEBUG")
            self.assertTrue(os.path.isdir(log_dir))

    def test_handlers_attached(self):
        from umh.core.logging_config import setup_logging

        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(log_dir=tmpdir, level="INFO")
            root = logging.getLogger()
            # At least 3 handlers: console, api file, error file
            self.assertGreaterEqual(len(root.handlers), 3)

    def test_structured_formatter_produces_json(self):
        from umh.core.logging_config import StructuredFormatter

        fmt = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )
        output = fmt.format(record)
        parsed = json.loads(output)
        self.assertEqual(parsed["level"], "INFO")
        self.assertEqual(parsed["message"], "hello world")
        self.assertIn("timestamp", parsed)

    def test_structured_formatter_includes_task_id(self):
        from umh.core.logging_config import StructuredFormatter

        fmt = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="step done",
            args=(),
            exc_info=None,
        )
        record.task_id = "task_abc123"
        output = fmt.format(record)
        parsed = json.loads(output)
        self.assertEqual(parsed["task_id"], "task_abc123")

    def test_console_formatter_readable(self):
        from umh.core.logging_config import ConsoleFormatter

        fmt = ConsoleFormatter()
        record = logging.LogRecord(
            name="umh.core",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="something happened",
            args=(),
            exc_info=None,
        )
        output = fmt.format(record)
        self.assertIn("WARNI", output)
        self.assertIn("umh.core", output)
        self.assertIn("something happened", output)

    def test_error_log_captures_warnings(self):
        from umh.core.logging_config import setup_logging

        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(log_dir=tmpdir, level="DEBUG")
            logger = logging.getLogger("test.error.capture")
            logger.warning("test warning message")
            # Flush handlers
            for h in logging.getLogger().handlers:
                h.flush()
            error_log = os.path.join(tmpdir, "umh_errors.log")
            self.assertTrue(os.path.exists(error_log))
            with open(error_log) as f:
                content = f.read()
            self.assertIn("test warning message", content)


class TestSilentExceptionFixed(unittest.TestCase):
    """_save_task logs errors instead of silently swallowing them."""

    def test_save_task_logs_error_on_store_failure(self):
        from umh.orchestrator.task import Task, TaskStep, _save_task

        task = Task(
            steps=[TaskStep(operation="test_op")],
            issued_by="test",
        )

        mock_store = MagicMock()
        mock_store.save.side_effect = RuntimeError("disk full")

        mock_module = MagicMock()
        mock_module.get_task_store = MagicMock(return_value=mock_store)

        with patch.dict(
            "sys.modules",
            {"umh.orchestrator.task_store": mock_module},
        ):
            with self.assertLogs("umh.orchestrator.task", level="ERROR") as cm:
                _save_task(task)

        self.assertTrue(
            any("Failed to persist task" in msg for msg in cm.output),
            f"Expected error log about persistence failure, got: {cm.output}",
        )


if __name__ == "__main__":
    unittest.main()

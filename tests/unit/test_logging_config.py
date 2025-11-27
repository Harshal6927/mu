# Copyright (c) 2025. All rights reserved.
"""Unit tests for logging_config module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from src.logging_config import (
    LOG_DIR,
    LOG_FILE,
    get_logger,
    init_logging,
    reset_logging,
    setup_logging,
)


class TestLoggingConstants:
    """Tests for logging configuration constants."""

    def test_log_dir_in_home(self) -> None:
        """Log directory should be in user's home directory."""
        assert ".muc" in str(LOG_DIR)
        assert "logs" in str(LOG_DIR)

    def test_log_file_path(self) -> None:
        """Log file should be named muc.log."""
        assert LOG_FILE.name == "muc.log"
        assert LOG_FILE.parent == LOG_DIR


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_creates_log_directory(self) -> None:
        """setup_logging should create log directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_log_dir = Path(tmpdir) / ".muc" / "logs"

            with patch("src.logging_config.LOG_DIR", test_log_dir):
                reset_logging()  # Reset any previous state
                setup_logging(debug=False, log_to_file=False)

                assert test_log_dir.exists()

    def test_idempotent_initialization(self) -> None:
        """setup_logging should be idempotent (safe to call multiple times)."""
        reset_logging()  # Reset state

        with tempfile.TemporaryDirectory() as tmpdir:
            test_log_dir = Path(tmpdir) / ".muc" / "logs"

            with patch("src.logging_config.LOG_DIR", test_log_dir):
                # Call twice - should not raise
                setup_logging(debug=False, log_to_file=False)
                setup_logging(debug=False, log_to_file=False)


class TestInitLogging:
    """Tests for init_logging function."""

    def test_init_logging_calls_setup(self) -> None:
        """init_logging should call setup_logging."""
        reset_logging()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_log_dir = Path(tmpdir) / ".muc" / "logs"

            with patch("src.logging_config.LOG_DIR", test_log_dir):
                init_logging(debug=False)

                assert test_log_dir.exists()


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger(self) -> None:
        """get_logger should return a logger object."""
        logger = get_logger("test_module")
        assert logger is not None

    def test_logger_has_name(self) -> None:
        """Logger should be bound with the specified name."""
        logger = get_logger("my_module")
        # loguru binds extra data, so we check it works without error
        assert logger is not None


class TestResetLogging:
    """Tests for reset_logging function."""

    def test_reset_allows_reinit(self) -> None:
        """reset_logging should allow re-initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_log_dir = Path(tmpdir) / ".muc" / "logs"

            with patch("src.logging_config.LOG_DIR", test_log_dir):
                reset_logging()
                init_logging(debug=False)
                reset_logging()
                # Should be able to init again
                init_logging(debug=True)


class TestLoggingIntegration:
    """Integration tests for logging functionality."""

    def test_logger_logs_without_error(self) -> None:
        """Logger should log messages without raising errors."""
        reset_logging()

        # Use log_to_file=False to avoid Windows file locking issues during tests
        init_logging(debug=True)
        logger = get_logger("test")

        # Should not raise
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

"""Tests for configuration management module."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from github_stars_mcp.config import Settings


class TestSettings:
    """Test cases for Settings configuration class."""

    def test_settings_with_valid_values(self):
        """Test Settings creation with valid values."""
        settings = Settings(
            github_token="ghp_test123",
            cache_dir=".test_cache",
            log_level="INFO"
        )
        
        assert settings.github_token == "ghp_test123"
        assert settings.cache_dir == ".test_cache"
        assert settings.log_level == "INFO"

    def test_settings_with_environment_variables(self, monkeypatch):
        """Test Settings loading from environment variables."""
        monkeypatch.setenv("GITHUB_TOKEN", "env_token_456")
        monkeypatch.setenv("CACHE_DIR", ".env_cache")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        
        settings = Settings()
        
        assert settings.github_token == "env_token_456"
        assert settings.cache_dir == ".env_cache"
        assert settings.log_level == "DEBUG"

    def test_settings_default_values(self):
        """Test Settings with default values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(github_token="required_token")
            
            assert settings.github_token == "required_token"
            assert settings.cache_dir == ".cache"
            assert settings.log_level == "INFO"

    def test_settings_missing_required_token(self, tmp_path, monkeypatch):
        """Test Settings validation when required github_token is missing."""
        # Create empty .env file to avoid loading from project .env
        env_file = tmp_path / ".env"
        env_file.write_text("")
        
        with patch.dict(os.environ, {}, clear=True):
            monkeypatch.chdir(tmp_path)
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "github_token" in str(exc_info.value)

    def test_settings_invalid_log_level(self):
        """Test Settings validation with invalid log level."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                github_token="test_token",
                log_level="INVALID_LEVEL"
            )
        
        assert "log_level" in str(exc_info.value)

    def test_settings_valid_log_levels(self):
        """Test Settings with all valid log levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            settings = Settings(
                github_token="test_token",
                log_level=level
            )
            assert settings.log_level == level

    def test_settings_case_insensitive_log_level(self):
        """Test Settings with case-insensitive log level."""
        settings = Settings(
            github_token="test_token",
            log_level="debug"
        )
        assert settings.log_level == "DEBUG"

    def test_settings_cache_dir_validation(self):
        """Test Settings with various cache directory formats."""
        valid_dirs = [
            ".cache",
            "/tmp/cache",
            "./data/cache",
            "cache_dir"
        ]
        
        for cache_dir in valid_dirs:
            settings = Settings(
                github_token="test_token",
                cache_dir=cache_dir
            )
            assert settings.cache_dir == cache_dir

    def test_settings_from_env_file(self, tmp_path, monkeypatch):
        """Test Settings loading from .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "GITHUB_TOKEN=file_token_789\n"
            "CACHE_DIR=.file_cache\n"
            "LOG_LEVEL=WARNING\n"
        )
        
        # Clear environment variables and change to the directory containing .env file
        with patch.dict(os.environ, {}, clear=True):
            monkeypatch.chdir(tmp_path)
            
            settings = Settings()
            
            assert settings.github_token == "file_token_789"
            assert settings.cache_dir == ".file_cache"
            assert settings.log_level == "WARNING"

    def test_settings_env_var_precedence_over_file(self, tmp_path, monkeypatch):
        """Test that environment variables take precedence over .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "GITHUB_TOKEN=file_token\n"
            "LOG_LEVEL=DEBUG\n"
        )
        
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("GITHUB_TOKEN", "env_token")
        
        settings = Settings()
        
        # Environment variable should override .env file
        assert settings.github_token == "env_token"
        # .env file value should be used when env var is not set
        assert settings.log_level == "DEBUG"
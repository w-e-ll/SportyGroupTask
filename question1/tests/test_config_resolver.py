from __future__ import annotations

import logging
from pathlib import Path

import pytest

from question1.config_resolver_main import run
from question1.lib.exceptions import InvalidConfigError
from question1.lib.models import ChangeType, SourceStatus
from question1.lib.utils import (
    build_diff,
    deep_merge,
    detect_conflicts,
    flatten,
    is_sensitive_key,
    load_yaml_file,
    mask_sensitive,
    parse_env,
    serialize_conflicts,
    serialize_diff,
    set_nested_value,
)


logger = logging.getLogger("config_resolver.tests")

CONFIG_DIR = Path("question1/configs")


def test_load_yaml_file_success():
    """Verify valid YAML config file loads successfully."""
    logger.info("Testing successful YAML file loading")

    result = load_yaml_file(CONFIG_DIR / "base.yml")

    assert result.status == SourceStatus.LOADED
    assert result.data["service"]["port"] == 8080


def test_missing_yaml_file_returns_empty_config():
    """Verify missing YAML file returns unavailable source result."""
    logger.info("Testing missing YAML file handling")

    result = load_yaml_file(CONFIG_DIR / "missing.yml")

    assert result.status == SourceStatus.UNAVAILABLE
    assert result.data == {}
    assert result.error is not None


def test_broken_yaml_returns_unavailable_source():
    """Verify invalid YAML syntax returns unavailable source result."""
    logger.info("Testing broken YAML file handling")

    result = load_yaml_file(CONFIG_DIR / "broken.yml")

    assert result.status == SourceStatus.UNAVAILABLE
    assert result.data == {}
    assert result.error is not None


def test_unsupported_file_extension_returns_unavailable_source(tmp_path: Path):
    """Verify unsupported config file suffix is reported as unavailable."""
    logger.info("Testing unsupported config file extension")

    json_file = tmp_path / "config.json"
    json_file.write_text("{}", encoding="utf-8")

    result = load_yaml_file(json_file)

    assert result.status == SourceStatus.UNAVAILABLE
    assert "Unsupported config format" in result.error


def test_deep_merge_nested_override():
    """Verify deep merge preserves existing nested values and applies overrides."""
    logger.info("Testing nested deep merge override")

    base = {"service": {"host": "localhost", "port": 8080}, "debug": False}
    override = {"service": {"port": 9090}}

    assert deep_merge(base, override) == {
        "service": {"host": "localhost", "port": 9090},
        "debug": False,
    }


def test_deep_merge_rejects_non_dict_base():
    """Verify deep merge rejects non-dictionary base values."""
    logger.info("Testing deep merge non-dict base validation")

    with pytest.raises(InvalidConfigError):
        deep_merge([], {})  # type: ignore[arg-type]


def test_deep_merge_rejects_non_dict_override():
    """Verify deep merge rejects non-dictionary override values."""
    logger.info("Testing deep merge non-dict override validation")

    with pytest.raises(InvalidConfigError):
        deep_merge({}, [])  # type: ignore[arg-type]


def test_flatten_nested_dictionary():
    """Verify nested dictionary is flattened into dotted-path keys."""
    logger.info("Testing nested dictionary flattening")

    data = {"service": {"host": "localhost", "port": 8080}}

    assert flatten(data) == {
        "service.host": "localhost",
        "service.port": 8080,
    }


def test_flatten_rejects_non_dictionary():
    """Verify flatten rejects non-dictionary input."""
    logger.info("Testing flatten non-dict validation")

    with pytest.raises(InvalidConfigError):
        flatten([])  # type: ignore[arg-type]


def test_detect_conflicts():
    """Verify conflict detection finds same path with different values."""
    logger.info("Testing conflict detection")

    staging = {"service": {"port": 8080}}
    production = {"service": {"port": 9090}}

    conflicts = detect_conflicts(staging, production)

    assert len(conflicts) == 1
    assert conflicts[0].path == "service.port"


def test_detect_conflicts_ignores_different_paths():
    """Verify different paths are not classified as direct conflicts."""
    logger.info("Testing conflict detection ignores unrelated paths")

    staging = {"feature_flags": {"new_ui": True}}
    production = {"service": {"port": 9090}}

    conflicts = detect_conflicts(staging, production)

    assert conflicts == []


def test_build_diff_detects_changed_values():
    """Verify diff detects changed values."""
    logger.info("Testing changed diff detection")

    diff = build_diff(
        current={"service": {"port": 8080}},
        desired={"service": {"port": 9090}},
    )

    assert len(diff) == 1
    assert diff[0].path == "service.port"
    assert diff[0].change_type == ChangeType.CHANGED


def test_build_diff_detects_added_values():
    """Verify diff detects added values."""
    logger.info("Testing added diff detection")

    diff = build_diff(
        current={"service": {"port": 8080}},
        desired={"service": {"port": 8080, "replicas": 3}},
    )

    assert len(diff) == 1
    assert diff[0].path == "service.replicas"
    assert diff[0].change_type == ChangeType.ADDED
    assert diff[0].old_value is None
    assert diff[0].new_value == 3


def test_build_diff_detects_removed_values():
    """Verify diff detects removed values."""
    logger.info("Testing removed diff detection")

    diff = build_diff(
        current={"service": {"port": 8080, "replicas": 3}},
        desired={"service": {"port": 8080}},
    )

    assert len(diff) == 1
    assert diff[0].path == "service.replicas"
    assert diff[0].change_type == ChangeType.REMOVED
    assert diff[0].old_value == 3
    assert diff[0].new_value is None


def test_is_sensitive_key_detects_sensitive_paths():
    """Verify sensitive path detection covers common secret names."""
    logger.info("Testing sensitive key detection")

    assert is_sensitive_key("database.password") is True
    assert is_sensitive_key("api.api_key") is True
    assert is_sensitive_key("security.private_key") is True
    assert is_sensitive_key("service.port") is False


def test_mask_sensitive_values():
    """Verify recursive sensitive value masking."""
    logger.info("Testing sensitive value masking")

    data = {
        "database": {"password": "super-secret", "host": "localhost"},
        "api_key": "secret-api-key",
    }

    masked = mask_sensitive(data)

    assert masked["database"]["password"] == "<masked>"
    assert masked["database"]["host"] == "localhost"
    assert masked["api_key"] == "<masked>"


def test_sensitive_values_are_masked_in_conflicts():
    """Verify serialized conflicts do not expose secrets."""
    logger.info("Testing conflict serialization masking")

    conflicts = detect_conflicts(
        staging={"database": {"password": "staging-secret"}},
        production={"database": {"password": "production-secret"}},
    )

    serialized = serialize_conflicts(conflicts)

    assert serialized[0]["path"] == "database.password"
    assert serialized[0]["staging_value"] == "<masked>"
    assert serialized[0]["production_value"] == "<masked>"


def test_sensitive_values_are_masked_in_diff():
    """Verify serialized diff does not expose secrets."""
    logger.info("Testing diff serialization masking")

    diff = build_diff(
        current={"api": {"api_key": "old-key"}},
        desired={"api": {"api_key": "new-key"}},
    )

    serialized = serialize_diff(diff)

    assert serialized[0]["path"] == "api.api_key"
    assert serialized[0]["old_value"] == "<masked>"
    assert serialized[0]["new_value"] == "<masked>"


def test_parse_env_supports_nested_values(monkeypatch):
    """Verify env parsing supports nested override paths and scalar conversion."""
    logger.info("Testing environment override parsing")

    monkeypatch.setenv("STAGING_SERVICE__PORT", "9443")
    monkeypatch.setenv("STAGING_FEATURE_FLAGS__ENABLE_NEW_DASHBOARD", "true")
    monkeypatch.setenv("STAGING_CACHE__RATE", "0.5")
    monkeypatch.setenv("STAGING_OPTION", "null")

    result = parse_env("STAGING_")

    assert result.status == SourceStatus.LOADED
    assert result.data["service"]["port"] == 9443
    assert result.data["feature_flags"]["enable_new_dashboard"] is True
    assert result.data["cache"]["rate"] == 0.5
    assert result.data["option"] is None


def test_parse_env_empty_prefix_returns_unavailable():
    """Verify empty env prefix is handled as source failure."""
    logger.info("Testing empty environment prefix handling")

    result = parse_env("")

    assert result.status == SourceStatus.UNAVAILABLE
    assert result.data == {}
    assert result.error is not None


def test_set_nested_value_rejects_empty_path():
    """Verify nested setter rejects empty paths."""
    logger.info("Testing set_nested_value empty path validation")

    with pytest.raises(InvalidConfigError):
        set_nested_value({}, [], "value")


def test_set_nested_value_rejects_empty_segment():
    """Verify nested setter rejects empty path segments."""
    logger.info("Testing set_nested_value empty segment validation")

    with pytest.raises(InvalidConfigError):
        set_nested_value({}, ["service", "", "port"], 8080)


def test_set_nested_value_rejects_nested_override_under_scalar():
    """Verify nested setter rejects nesting under scalar value."""
    logger.info("Testing set_nested_value scalar collision validation")

    data = {"service": "not-a-dict"}

    with pytest.raises(InvalidConfigError):
        set_nested_value(data, ["service", "port"], 8080)


def test_run_applies_environment_override(monkeypatch, tmp_path: Path):
    """Verify full resolver applies environment variable overrides."""
    logger.info("Testing full resolver with environment override")

    monkeypatch.setenv("STAGING_SERVICE__PORT", "9443")

    result = run(
        staging_file=CONFIG_DIR / "base.yml",
        production_file=CONFIG_DIR / "production.yml",
        staging_env_prefix="STAGING_",
        production_env_prefix="PRODUCTION_",
        dry_run=True,
        log_dir=tmp_path / "logs",
        stdout=False,
    )

    assert result["staging_effective_config"]["service"]["port"] == 9443


def test_run_returns_summary_and_source_failures(tmp_path: Path):
    """Verify full resolver response includes summary and source failures."""
    logger.info("Testing full resolver response structure")

    result = run(
        staging_file=CONFIG_DIR / "base.yml",
        production_file=CONFIG_DIR / "production.yml",
        staging_env_prefix="STAGING_",
        production_env_prefix="PRODUCTION_",
        dry_run=True,
        log_dir=tmp_path / "logs",
        stdout=False,
    )

    assert result["dry_run"] is True
    assert "dry_run_note" in result
    assert "summary" in result
    assert "conflicts" in result
    assert "source_failures" in result
    assert "diff_production_to_staging" in result


def test_run_surfaces_broken_source_failure(tmp_path: Path):
    """Verify full resolver surfaces broken YAML as structured source failure."""
    logger.info("Testing full resolver broken source reporting")

    result = run(
        staging_file=CONFIG_DIR / "broken.yml",
        production_file=CONFIG_DIR / "production.yml",
        staging_env_prefix="STAGING_",
        production_env_prefix="PRODUCTION_",
        dry_run=True,
        log_dir=tmp_path / "logs",
        stdout=False,
    )

    assert result["summary"]["source_failure_count"] >= 1
    assert result["source_failures"]


def test_run_writes_split_log_files(tmp_path: Path):
    """Verify resolver creates split info and error log files."""
    logger.info("Testing resolver split log file creation")

    log_dir = tmp_path / "logs"

    run(
        staging_file=CONFIG_DIR / "broken.yml",
        production_file=CONFIG_DIR / "production.yml",
        staging_env_prefix="STAGING_",
        production_env_prefix="PRODUCTION_",
        dry_run=True,
        log_dir=log_dir,
        stdout=False,
    )

    assert list(log_dir.glob("config_resolver-info-*.log"))
    assert list(log_dir.glob("config_resolver-error-*.log"))

"""Test cases for the project module."""

import json
import logging
from datetime import datetime

from dbt_core_interface import DbtProject


def test_import_succeeds() -> None:
    """A simple test to ensure that the project module can be imported.

    This implicitly guarantees both that none of the surface area of dbt-core
    imports have changed and that our import side-effects are succeeding.
    It exits with a status code of zero.
    """
    from dbt_core_interface import project

    _ = project


def test_logging_not_configured_at_import() -> None:
    """Verify logging is NOT configured at import time.

    This is critical for issue #136 - importing dbt-core-interface
    should not cause side effects like setting DEBUG log level or
    adding RichHandler to dbt's logger.
    """
    from dbt_core_interface import project

    _ = project

    logger = logging.getLogger("dbt_core_interface.project")

    assert logger.level == 0 or logger.level == logging.NOTSET, (
        f"Logger should NOT be configured at import, but level is {logger.level}"
    )
    assert len(logger.handlers) == 0, (
        f"Logger should have NO handlers at import, but has {len(logger.handlers)}"
    )


def test_setup_logging_works() -> None:
    """Verify DbtProject.setup_logging() correctly configures logging."""
    from dbt_core_interface import DbtProject

    DbtProject.setup_logging(level=logging.DEBUG)

    logger = logging.getLogger("dbt_core_interface.project")

    assert logger.level == logging.DEBUG, (
        f"Logger level should be DEBUG after setup_logging, but is {logger.level}"
    )
    assert len(logger.handlers) > 0, "Logger should have handlers after setup_logging"
    assert any(h.__class__.__name__ == "RichHandler" for h in logger.handlers), (
        "Logger should have RichHandler after setup_logging"
    )


def test_setup_logging_idempotent() -> None:
    """Verify DbtProject.setup_logging() can be called multiple times safely."""
    from dbt_core_interface import DbtProject

    DbtProject.setup_logging(level=logging.DEBUG)
    handler_count_after_first_call = len(logging.getLogger("dbt_core_interface.project").handlers)

    DbtProject.setup_logging(level=logging.INFO)

    logger = logging.getLogger("dbt_core_interface.project")

    handler_count_after_second_call = len(logger.handlers)

    assert handler_count_after_second_call == handler_count_after_first_call, (
        "setup_logging should be idempotent - should not add duplicate handlers"
    )


def test_write_manifest_serializes_datetime(tmp_path) -> None:
    """Verify write_manifest writes a manifest holding a datetime as valid JSON."""
    project = DbtProject(
        project_dir="tests/sqlfluff_templater/fixtures/dbt/dbt_project",
        profiles_dir="tests/sqlfluff_templater/fixtures/dbt/profiles_yml",
        target="dev",
    )
    node = next(n for n in project.manifest.nodes.values() if n.resource_type == "model")
    node.config.meta["written_at"] = datetime(2025, 6, 26)
    try:
        project.write_manifest(tmp_path)
    finally:
        del node.config.meta["written_at"]

    manifest = json.loads((tmp_path / "manifest.json").read_text())
    written_at = manifest["nodes"][node.unique_id]["config"]["meta"]["written_at"]

    assert written_at == "2025-06-26T00:00:00"

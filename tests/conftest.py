from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from src.config import PROJECT_ROOT


@pytest.fixture
def workspace(request: pytest.FixtureRequest) -> Path:
    base = PROJECT_ROOT / "sample_files" / "generated_pytest" / request.node.name
    path = base / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def tmp_path(request: pytest.FixtureRequest) -> Path:
    """Sandbox-safe tmp_path equivalent kept inside the project test-artifact area."""
    base = PROJECT_ROOT / "sample_files" / "generated_pytest" / request.node.name
    path = base / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path

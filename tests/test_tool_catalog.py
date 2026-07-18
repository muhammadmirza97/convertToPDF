from __future__ import annotations

from src.config import ACTIONS
from src.ui.tool_catalog import CATEGORIES, MEGA_MENU_GROUPS, TOOLS


def test_catalog_has_exact_categories_and_complete_actions():
    assert CATEGORIES == [
        "All",
        "Organize PDF",
        "Optimize PDF",
        "Convert PDF",
        "Edit PDF",
        "PDF Security",
        "PDF Intelligence",
    ]
    assert len(TOOLS) == 31
    assert all(tool.action in ACTIONS for tool in TOOLS)


def test_catalog_contains_no_account_or_cloud_tools():
    labels = " ".join(tool.name for tool in TOOLS).lower()
    assert "login" not in labels
    assert "sign up" not in labels
    assert "cloud" not in labels


def test_mega_menu_groups_every_tool_once():
    grouped_names = [name for _heading, names in MEGA_MENU_GROUPS for name in names]
    assert len(grouped_names) == len(set(grouped_names))
    assert set(grouped_names) == {tool.name for tool in TOOLS}

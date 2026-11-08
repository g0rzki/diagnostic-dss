import pytest

from app import create_app
from app.config import TestConfig
from app.engine.rules import RuleFileError


def test_rule_base_is_loaded_when_application_starts(app):
    base = app.extensions["rule_base"]

    assert len(base.rules) == 45
    assert set(base.sources) == {"esscd1", "ptge"}


def test_application_does_not_start_with_invalid_rule_files(tmp_path):
    (tmp_path / "sources.yaml").write_text("esscd1: {name: ESsCD}\n", encoding="utf-8")

    class BrokenRulesConfig(TestConfig):
        RULES_DIR = tmp_path

    with pytest.raises(RuleFileError):
        create_app(BrokenRulesConfig)

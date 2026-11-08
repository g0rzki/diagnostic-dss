from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from app.engine.rules import AllOf, AnyOf, Comparison, Level, RuleFileError, load_rules

SAMPLE = Path(__file__).parent / "data" / "rules"


def copy_sample(tmp_path, change=None):
    files = {
        path.name: yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in SAMPLE.glob("*.yaml")
    }
    if change:
        change(files)
    for name, content in files.items():
        text = yaml.safe_dump(content, allow_unicode=True, sort_keys=False)
        (tmp_path / name).write_text(text, encoding="utf-8")
    return tmp_path


def first_rule(files):
    return files["g1.yaml"]["rules"][0]


def problems(directory):
    with pytest.raises(RuleFileError) as error:
        load_rules(directory)
    return error.value.problems


def test_sample_rules_are_loaded_in_file_order():
    base = load_rules(SAMPLE)

    assert [rule.id for rule in base.rules] == ["G1-01", "G2-04", "G2-07", "G4-04", "G4-11"]
    assert set(base.sources) == {"esscd1", "ptge"}
    assert base.rules[0].level is Level.RECOMMENDATION


def test_condition_is_parsed_into_tree_of_typed_comparisons():
    rules = {rule.id: rule for rule in load_rules(SAMPLE).rules}

    g4_04 = rules["G4-04"].condition
    assert isinstance(g4_04, AllOf)
    assert isinstance(g4_04.conditions[3], AnyOf)
    assert g4_04.conditions[3].conditions[1] == Comparison("P13", "in", ("0", "1"))
    assert rules["G2-07"].condition.conditions[1] == Comparison("P1", "≥", Decimal(45))
    assert rules["G1-01"].condition.conditions[0] == Comparison("P3", "=", None)


def test_source_and_ptge_metadata_are_loaded():
    rule = load_rules(SAMPLE).rules[0]

    assert (rule.source.ref, rule.source.page, rule.source.kind) == ("esscd1", 1865, "zalecenie")
    assert rule.source.grade.agreement == 95
    assert rule.ptge.status == "zgodność"
    assert rule.ptge.pages == (5,)
    assert rule.ptge.grade.agreement is None


def replace_comparison(index, comparison):
    def change(files):
        first_rule(files)["condition"]["all"][index] = comparison

    return change


def set_key(key, value):
    def change(files):
        first_rule(files)[key] = value

    return change


@pytest.mark.parametrize(
    "change, expected",
    [
        (lambda f: first_rule(f).pop("name"), "brak pól ['name']"),
        (set_key("quotes", ["cytat"]), "nieznane pola ['quotes']"),
        (set_key("level", "zalecenie"), "level"),
        (set_key("group", "G2"), "group"),
        (set_key("basis", "esscd"), "basis"),
        (replace_comparison(0, ["P18", "=", None]), "nieznane pole 'P18'"),
        (replace_comparison(1, ["P2", "=", "zwykłe"]), "spoza listy"),
        (replace_comparison(1, ["P2", "!=", "normalne"]), "nieznany operator"),
        (replace_comparison(1, ["P2", "<", 1]), "tylko dla pól liczbowych"),
        (replace_comparison(2, ["D3", "=", None]), "null niedozwolone"),
        (replace_comparison(1, ["P2", "in", []]), "niepustej listy"),
        (replace_comparison(1, ["P2", "normalne"]), "[pole, operator, wartość]"),
        (set_key("uses", ["P3", "P7", "P15"]), "czytanych wprost przez warunek ['P2']"),
        (set_key("uses", ["P2", "P3", "P7", "P9", "P15"]), "których warunek nie czyta ['P9']"),
        (set_key("uses", ["P2", "P3", "P15"]), "żaden parametr wartości D3"),
        (lambda f: first_rule(f)["source"].update(ref="bsg"), "source.ref"),
        (lambda f: first_rule(f)["source"]["grade"].update(strength="mocne"), "strength"),
        (lambda f: first_rule(f)["ptge"].update(status="brak odniesienia"), "ptge.pages"),
        (lambda f: first_rule(f)["source"].update(quotes=["cytat"]), "source: nieznane pola"),
        (lambda f: first_rule(f)["ptge"].update(ref="ptge"), "ptge: nieznane pola"),
        (lambda f: first_rule(f)["source"].update(page=True), "source.page"),
        (lambda f: first_rule(f)["source"].update(location=""), "source.location"),
        (lambda f: first_rule(f)["source"].update(kind="rycina"), "source.kind"),
        (set_key("source", "esscd1"), "source: wymagany słownik"),
        (set_key("ptge", "zgodność"), "ptge: wymagany słownik"),
        (lambda f: first_rule(f)["ptge"].update(pages=[True]), "ptge.pages"),
        (lambda f: first_rule(f)["source"]["grade"].update(agreement=True), "agreement"),
        (lambda f: first_rule(f)["source"]["grade"].update(agreement=101), "agreement"),
        (lambda f: first_rule(f)["source"]["grade"].update(gr="silne"), "dozwolone pola"),
        (set_key("name", " "), "name: wymagany niepusty tekst"),
        (set_key("condition_text", ""), "condition_text: wymagany niepusty tekst"),
        (set_key("uses", []), "wymagana niepusta lista"),
        (set_key("uses", ["P2", "P2", "P3", "P7", "P15"]), "powtórzone parametry"),
        (replace_comparison(3, ["P17", "=", "tak"]), "wymagane true / false"),
        (replace_comparison(3, ["P1", "=", "trzydzieści"]), "wymagana liczba"),
        (replace_comparison(3, ["P14", "=", 4]), "tylko z null"),
        (replace_comparison(3, [15, "=", "ujemny"]), "musi być napisem"),
        (replace_comparison(3, ["P1", "<", None]), "wymaga liczby"),
        (replace_comparison(3, {"all": []}), "niepustej listy warunków"),
        (replace_comparison(3, {"not": [["P15", "=", "ujemny"]]}), "nieprawidłowy warunek"),
    ],
)
def test_invalid_rule_is_rejected(tmp_path, change, expected):
    found = problems(copy_sample(tmp_path, change))

    assert len(found) == 1
    assert found[0].startswith("g1.yaml: G1-01: ")
    assert expected in found[0]


def test_unquoted_number_is_not_a_marsh_grade(tmp_path):
    def change(files):
        files["g4.yaml"]["rules"][0]["condition"]["all"][3]["any"][1] = ["P13", "in", [0, 1]]

    assert "spoza listy" in problems(copy_sample(tmp_path, change))[0]


def test_duplicate_rule_id_is_rejected(tmp_path):
    def change(files):
        files["g2.yaml"]["rules"][1]["id"] = "G2-04"

    assert problems(copy_sample(tmp_path, change)) == ["g2.yaml: G2-04: powtórzone id"]


def test_all_problems_are_reported_together(tmp_path):
    def change(files):
        first_rule(files)["level"] = "zalecenie"
        files["g2.yaml"]["rules"][0]["uses"] = ["P99"]

    assert len(problems(copy_sample(tmp_path, change))) == 2


def test_yaml_syntax_error_is_reported(tmp_path):
    directory = copy_sample(tmp_path)
    (directory / "g1.yaml").write_text("rules: [\n", encoding="utf-8")

    assert problems(directory)[0].startswith("g1.yaml: błąd składni YAML")


def test_unquoted_equals_sign_is_a_yaml_error(tmp_path):
    directory = copy_sample(tmp_path)
    text = (SAMPLE / "g1.yaml").read_text(encoding="utf-8").replace("'='", "=")
    (directory / "g1.yaml").write_text(text, encoding="utf-8")

    assert problems(directory)[0].startswith("g1.yaml: błąd składni YAML")


def test_directory_without_rule_files_is_rejected(tmp_path):
    (tmp_path / "sources.yaml").write_text((SAMPLE / "sources.yaml").read_text(encoding="utf-8"))

    assert "brak plików reguł" in problems(tmp_path)[0]


def test_rule_that_is_not_a_mapping_is_rejected(tmp_path):
    def change(files):
        files["g1.yaml"]["rules"][0] = "G1-01"

    assert problems(copy_sample(tmp_path, change)) == ["g1.yaml: #1: reguła musi być słownikiem"]


def test_rules_without_id_in_two_files_are_not_reported_as_duplicates(tmp_path):
    def change(files):
        del first_rule(files)["id"]
        del files["g2.yaml"]["rules"][0]["id"]

    found = problems(copy_sample(tmp_path, change))

    assert found == ["g1.yaml: #1: brak pól ['id']", "g2.yaml: #1: brak pól ['id']"]


def test_group_file_without_rules_list_is_rejected(tmp_path):
    def change(files):
        files["g4.yaml"] = {"reguly": []}

    assert "wyłącznie listę 'rules'" in problems(copy_sample(tmp_path, change))[0]


@pytest.mark.parametrize(
    "sources, expected",
    [
        ([], "wymagany słownik źródeł"),
        ({"esscd1": {"name": "ESsCD"}}, "wymagane pola name i citation"),
        ({"esscd1": {"name": "ESsCD", "citation": ""}}, "niepustym tekstem"),
    ],
)
def test_invalid_sources_file_is_rejected(tmp_path, sources, expected):
    def change(files):
        files["sources.yaml"] = sources

    found = problems(copy_sample(tmp_path, change))

    assert len(found) == 1
    assert found[0].startswith("sources.yaml: ")
    assert expected in found[0]


def test_missing_sources_file_is_rejected(tmp_path):
    directory = copy_sample(tmp_path)
    (directory / "sources.yaml").unlink()

    assert problems(directory)[0].startswith("sources.yaml: ")


def test_rule_id_must_start_with_group_of_its_file(tmp_path):
    found = problems(copy_sample(tmp_path, set_key("id", "G2-01")))

    assert found == ["g1.yaml: G2-01: id: musi zaczynać się od G1-"]

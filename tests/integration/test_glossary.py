import re

from app.engine.derived import DERIVED
from app.engine.parameters import PARAMETERS


def test_glossary_lists_every_code(client, app):
    response = client.get("/slownik")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    codes = [*PARAMETERS, *DERIVED, *(rule.id for rule in app.extensions["rule_base"].rules)]
    for code in codes:
        assert f'id="{code}"' in page


def test_glossary_names_sources_and_levels(client):
    page = client.get("/slownik").get_data(as_text=True)

    assert "ESsCD 2025 cz. 1" in page
    assert "PTG-E 2026" in page
    assert 'href="https://doi.org/10.1002/ueg2.70119"' in page
    assert "<dd>ESsCD 2025 cz. 1, s. 1865</dd>" in page
    assert "<dd>zgodność, s. 5</dd>" in page
    assert "sygnalizuje czynnik, który może zafałszować wynik" in page


def test_navigation_links_to_glossary(client):
    page = client.get("/").get_data(as_text=True)

    assert 'href="/slownik"' in page


def test_glossary_links_codes_in_conditions_and_definitions(client):
    page = client.get("/slownik").get_data(as_text=True)

    assert re.search(r'ścieżka bez biopsji dostępna \(<a href="#D4"[^>]*>D4</a>\)', page)
    assert re.search(r'<a href="#P3"[^>]*>P3</a> ≥ 10 × <a href="#P4"[^>]*>P4</a>', page)


def test_glossary_marks_rule_levels_and_groups(client):
    page = client.get("/slownik").get_data(as_text=True)

    assert re.search(r'id="G1-02" class="[^"]*border-l-amber-500', page)
    assert re.search(r'id="G1-01" class="[^"]*border-l-brand', page)
    assert re.search(r'id="G1-04" class="[^"]*border-l-slate-400', page)
    for group in ("G1", "G2", "G3", "G4"):
        assert f'href="#grupa-{group}"' in page
        assert f'id="grupa-{group}"' in page

import pytest

from app.scenarios import BY_SLUG, SCENARIOS


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[scenario.slug for scenario in SCENARIOS])
def test_result_explains_every_fired_rule(client, scenario):
    page = client.post("/konsultacja", data=scenario.values).get_data(as_text=True)

    assert page.count("<summary") == page.count('id="tip-G') >= len(scenario.expected)
    for code in scenario.expected:
        assert f"Reguła {code} w słowniku oznaczeń" in page


def test_explanation_shows_condition_values_and_source(client):
    page = client.post("/konsultacja", data=BY_SLUG["bez-biopsji"].values).get_data(as_text=True)

    assert "Wartości w warunku" in page
    assert 'ścieżka bez biopsji dostępna: <span class="font-medium">tak</span>' in page
    assert 'wiek: <span class="font-medium">30 lat</span>' in page
    assert "ESsCD 2025 cz. 1: Q.IV.1.2 (zalecenie) i kluczowe uwagi, s. 1870" in page
    assert "siła zalecenia: warunkowe, zgoda 95%" in page
    assert 'href="/slownik#D4"' in page


def test_explanation_shows_ptge_direction(client):
    page = client.post("/konsultacja", data=BY_SLUG["biopsja-marsh-2"].values).get_data(
        as_text=True
    )

    assert "różnica, s. 8; kierunek reguły według PTG-E" in page
    assert "Uzasadnienie (bez przypisanej oceny GRADE)" in page

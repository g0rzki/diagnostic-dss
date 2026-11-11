import re

from app.scenarios import BY_SLUG, SCENARIOS


def test_form_offers_every_scenario(client):
    page = client.get("/konsultacja").get_data(as_text=True)

    assert "Przykładowe scenariusze" in page
    for scenario in SCENARIOS:
        assert f'href="/konsultacja?przyklad={scenario.slug}"' in page
    assert "Ścieżka w systemie" not in page


def test_scenario_fills_the_form_and_describes_its_path(client):
    scenario = BY_SLUG["bez-biopsji"]
    page = client.get(f"/konsultacja?przyklad={scenario.slug}").get_data(as_text=True)

    assert 'aria-current="true"' in page
    assert "Ścieżka w systemie" in page
    assert scenario.path[0] in page
    assert "Druga próbka dodatnia – rozpoznanie bez biopsji" in page
    assert 'id="P3" name="P3" value="150"' in page
    assert re.search(r'name="P12" value="tak"[^>]*checked', page)


def test_unknown_scenario_gives_404(client):
    assert client.get("/konsultacja?przyklad=brak").status_code == 404


def test_result_of_unchanged_scenario_shows_its_path(client):
    scenario = BY_SLUG["niedobor-iga"]
    page = client.post("/konsultacja", data=scenario.values).get_data(as_text=True)

    assert "Ścieżka w systemie" in page
    assert scenario.path[-1] in page
    assert "Popraw dane</strong> na dole strony" in page
    for code in scenario.expected:
        assert f'id="tip-{code}"' in page
        assert f'id="tip-scenario-{code}"' in page


def test_result_of_changed_scenario_data_shows_no_path(client):
    scenario = BY_SLUG["niedobor-iga"]
    data = {**scenario.values, "P9": "dodatni"}
    page = client.post("/konsultacja", data=data).get_data(as_text=True)

    assert "G4-01" in page
    assert "Ścieżka w systemie" not in page


def test_form_explains_codes_next_to_fields(client):
    page = client.get("/konsultacja").get_data(as_text=True)

    assert "Kody przy polach" in page
    assert 'id="tip-legend-P3"' in page
    assert page.count('id="tip-P3"') == 1

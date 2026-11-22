import re
import shutil

import pytest
from sqlalchemy import select

from app import create_app
from app.config import TestConfig
from app.forms import INTERVIEW_DEFAULTS
from app.models import Consultation
from app.scenarios import BY_SLUG

SEROLOGY = {"P3": "150", "P4": "10", "P7": "1,5", "P8": "0,7"}


def post(client, label="P-001", **changes):
    data = {**INTERVIEW_DEFAULTS, "P1": "30", **SEROLOGY, **changes, "oznaczenie": label}
    return client.post("/konsultacja", data=data)


def hidden_fields(page):
    return dict(re.findall(r'type="hidden" name="([^"]+)" value="([^"]*)"', page))


def test_saving_redirects_to_saved_consultation_and_repeat_points_to_the_same_one(client, database):
    first = post(client, label="p-001")
    again = post(client)
    second = post(client, P12="tak")

    assert first.status_code == 303
    assert first.headers["Location"] == "/historia/P-001/1?zapis=nowy"
    assert again.headers["Location"] == "/historia/P-001/1?zapis=bez-zmian"
    assert second.headers["Location"] == "/historia/P-001/2?zapis=kolejna"
    assert len(database.session.scalars(select(Consultation)).all()) == 2


def test_saved_consultation_shows_data_result_explanation_and_consistency(client, database):
    page = client.get(post(client).headers["Location"]).get_data(as_text=True)

    assert "Konsultacja 1 przypadku P-001" in page
    assert "Utworzono przypadek P-001 i zapisano pierwszą konsultację." in page
    assert "Wynik zgodny z bieżącą bazą reguł." in page
    assert 'IgA całkowite: <span class="font-medium">1,5 g/L</span>' in page
    assert 'id="tip-G2-01"' in page
    assert "Uzasadnienie" in page and "Warunek reguły" in page
    assert 'href="/historia/P-001"' in page


def test_saved_consultation_without_save_message_when_opened_directly(client, database):
    post(client)

    page = client.get("/historia/P-001/1").get_data(as_text=True)

    assert "Utworzono przypadek" not in page
    assert "Konsultacja 1 przypadku P-001" in page


def test_edit_from_saved_consultation_keeps_label_and_decimal_comma(client, database):
    page = client.get(post(client).headers["Location"]).get_data(as_text=True)

    hidden = hidden_fields(page)

    assert hidden["oznaczenie"] == "P-001"
    assert (hidden["P7"], hidden["P8"]) == ("1,5", "0,7")


@pytest.mark.parametrize("url", ["/historia/P-001/0", "/historia/P-001/2", "/historia/X-1/1"])
def test_missing_saved_consultation_gives_404(client, database, url):
    post(client)

    assert client.get(url).status_code == 404


def test_timeline_links_every_consultation_to_its_details(client, database):
    post(client)
    post(client, P12="tak")

    page = client.get("/historia/P-001").get_data(as_text=True)

    assert 'href="/historia/P-001/1"' in page
    assert 'href="/historia/P-001/2"' in page


def test_scenario_description_is_shown_on_saved_consultation(client, database):
    data = {**BY_SLUG["bez-biopsji"].values, "oznaczenie": "P-001"}
    location = client.post("/konsultacja", data=data).headers["Location"]

    assert 'id="tip-scenario-G2-03"' in client.get(location).get_data(as_text=True)


@pytest.mark.parametrize("label", ["przykład-1", "PRZYKLAD-7", " Przykład  9"])
def test_reserved_demo_label_is_rejected_at_its_field(client, database, label):
    response = post(client, label=label)

    assert response.status_code == 422
    assert "zarezerwowane dla przypadków pokazowych" in response.get_data(as_text=True)
    assert database.session.scalars(select(Consultation)).all() == []


def changed_rules_app(tmp_path, old, new):
    rules = tmp_path / "rules"
    shutil.copytree(TestConfig.RULES_DIR, rules)
    g2 = rules / "g2.yaml"
    g2.write_text(g2.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    class ChangedRules(TestConfig):
        RULES_DIR = rules

    return create_app(ChangedRules)


def test_saved_consultation_reports_different_result_after_rule_change(client, database, tmp_path):
    post(client)
    changed = changed_rules_app(tmp_path, "[P12, '=', nie omówiono]", "[P12, '=', tak]")

    page = changed.test_client().get("/historia/P-001/1").get_data(as_text=True)

    assert "Ponowna ocena zapisanych danych bieżącymi regułami daje inny wynik." in page
    assert "Nie zadziałałyby już" in page
    assert "pochodzą z bieżącej wersji bazy reguł" in page
    assert 'id="tip-G2-01"' in page


def test_saved_consultation_reports_same_result_after_change_without_effect(
    client, database, tmp_path
):
    post(client)
    changed = changed_rules_app(tmp_path, "rules:\n", "rules:\n# uwaga\n")

    page = changed.test_client().get("/historia/P-001/1").get_data(as_text=True)

    assert "Baza reguł zmieniła się od zapisu" in page
    assert "daje ten sam wynik" in page

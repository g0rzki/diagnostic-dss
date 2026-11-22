import re
from collections import Counter
from datetime import UTC, datetime
from html.parser import HTMLParser

import pytest
from sqlalchemy import select

from app.engine.validation import validate
from app.forms import INTERVIEW_DEFAULTS
from app.history import form_display, form_values
from app.models import Case, Consultation

SEROLOGY = {"P3": "150", "P4": "10", "P7": "1,5", "P8": "0,7"}


class FormReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.data = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form" and attrs.get("action") == "/konsultacja":
            self.inside = True
        elif tag == "input" and self.inside:
            if attrs.get("type") == "text" or "checked" in attrs:
                self.data[attrs["name"]] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.inside = False


def browser_form(page):
    reader = FormReader()
    reader.feed(page)
    return reader.data


def submit(client, label="", **changes):
    data = {**INTERVIEW_DEFAULTS, "P1": "30", **changes}
    if label is not None:
        data["oznaczenie"] = label
    return client.post("/konsultacja", data=data)


def consultations(database):
    return database.session.scalars(select(Consultation).order_by(Consultation.id)).all()


def test_consultation_with_label_is_saved_with_rule_base_version(client, database, app):
    page = submit(client, label=" p-001 ", **SEROLOGY).get_data(as_text=True)

    (saved,) = consultations(database)
    assert saved.case.label == "P-001"
    assert saved.parameters["P3"] == "150"
    assert saved.parameters["P7"] == "1.5"
    assert saved.fired_rules == ["G2-01"]
    assert saved.derived["D4"] is True
    assert saved.rules_version == app.extensions["rule_base"].version
    assert "Utworzono przypadek P-001 i zapisano pierwszą konsultację." in page
    assert 'href="/historia/P-001"' in page


@pytest.mark.parametrize("label", ["", "   ", None])
def test_consultation_without_label_is_not_saved(client, database, label):
    page = submit(client, label=label).get_data(as_text=True)

    assert consultations(database) == []
    assert "Wynik nie został zapisany w historii" in page


def test_invalid_form_saves_nothing_and_keeps_label(client, database):
    response = submit(client, label="P-001", P1="")

    assert response.status_code == 422
    assert consultations(database) == []
    assert 'value="P-001"' in response.get_data(as_text=True)


def test_invalid_label_is_shown_at_its_field_and_nothing_is_saved(client, database):
    response = submit(client, label="P/001")
    page = response.get_data(as_text=True)

    assert response.status_code == 422
    assert consultations(database) == []
    assert "oznaczenie przypadku: do 30 znaków" in page
    assert 'id="oznaczenie" name="oznaczenie" value="P/001"' in page


def test_edit_keeps_label_and_next_assessment_adds_consultation(client, database):
    first = submit(client, label="p-001").get_data(as_text=True)
    hidden = dict(re.findall(r'type="hidden" name="([^"]+)" value="([^"]*)"', first))
    assert hidden["oznaczenie"] == "P-001"

    form = browser_form(client.post("/konsultacja/popraw", data=hidden).get_data(as_text=True))
    page = client.post("/konsultacja", data={**form, **SEROLOGY}).get_data(as_text=True)

    assert [item.fired_rules for item in consultations(database)] == [["G1-01"], ["G2-01"]]
    assert "Zapisano jako konsultację 2 przypadku P-001." in page


def test_identical_assessment_does_not_add_consultation(client, database):
    submit(client, label="P-001", **SEROLOGY)

    page = submit(client, label="P-001", **SEROLOGY).get_data(as_text=True)

    assert len(consultations(database)) == 1
    assert "takie same jak w ostatniej konsultacji przypadku P-001" in page


def test_labels_differing_only_in_case_and_spaces_belong_to_one_case(client, database):
    submit(client, label="p-001")
    submit(client, label="  P-001", **SEROLOGY)

    assert database.session.scalars(select(Case.label)).all() == ["P-001"]
    assert len(consultations(database)) == 2


def test_label_does_not_hide_scenario_description(client, database):
    form = browser_form(client.get("/konsultacja?przyklad=bez-biopsji").get_data(as_text=True))

    page = client.post("/konsultacja", data={**form, "oznaczenie": "P-001"}).get_data(as_text=True)

    assert 'id="tip-scenario-G2-03"' in page


def test_history_lists_cases_with_newest_consultation_first(client, database):
    submit(client, label="P-001")
    submit(client, label="P-002", **SEROLOGY)
    submit(client, label="P-001", **SEROLOGY, P12="tak")

    page = client.get("/historia").get_data(as_text=True)

    assert page.index("P-001") < page.index("P-002")
    assert "2 konsultacje, ostatnia" in page
    assert "1 konsultacja, ostatnia" in page
    assert 'id="tip-1-G2-02"' in page
    assert 'id="tip-2-G2-01"' in page


def test_empty_history_points_to_consultation_form(client, database):
    page = client.get("/historia").get_data(as_text=True)

    assert "Brak zapisanych przypadków." in page


def test_case_page_shows_timeline_of_changes(client, database):
    submit(client, label="P-001")
    submit(client, label="P-001", **SEROLOGY)
    submit(client, label="P-001", **SEROLOGY, P12="tak")

    page = client.get("/historia/p-001").get_data(as_text=True)

    assert "Przypadek P-001" in page
    assert "3 konsultacje, od" in page
    assert page.count("<article") == 3
    assert "Wpisane dane" in page
    assert page.count("Zmienione dane") == 2
    change = r"anty-TG2 IgA, wynik 1:\s*<span[^>]*>brak wyniku</span> →\s*<span[^>]*>150<"
    assert re.search(change, page)
    assert re.search(r"Doszły</dt>\s*<dd[^>]*>\s*<a[^>]*>G2-01</a>", page)
    assert re.search(r"Zniknęły</dt>\s*<dd[^>]*>\s*<a[^>]*>G1-01</a>", page)
    duplicates = [i for i, n in Counter(re.findall(r'id="([^"]+)"', page)).items() if n > 1]
    assert duplicates == []


def test_case_page_marks_change_of_rule_base_version(client, database):
    submit(client, label="P-001", **SEROLOGY)
    database.session.scalars(select(Consultation)).one().rules_version = "0" * 64
    database.session.commit()
    submit(client, label="P-001", **SEROLOGY)

    page = client.get("/historia/P-001").get_data(as_text=True)

    assert "Zmieniła się wersja bazy reguł: 00000000 →" in page


def test_label_with_space_works_in_case_address(client, database):
    page = submit(client, label="kontrola 3").get_data(as_text=True)

    assert 'href="/historia/KONTROLA%203"' in page
    assert "Przypadek KONTROLA 3" in client.get("/historia/KONTROLA%203").get_data(as_text=True)


def test_unknown_case_gives_404(client, database):
    assert client.get("/historia/P-404").status_code == 404
    assert client.get("/konsultacja?przypadek=P-404").status_code == 404


def test_continue_opens_form_with_last_data_and_resubmitting_it_adds_nothing(client, database):
    submit(client, label="P-001")
    submit(client, label="P-001", **SEROLOGY, P13="3", P14_dalsza="4", P14_opuszka="1")
    last = consultations(database)[-1]

    form = browser_form(client.get("/konsultacja?przypadek=P-001").get_data(as_text=True))
    page = client.post("/konsultacja", data=form).get_data(as_text=True)

    expected = {**form_display(last.parameters), "oznaczenie": "P-001"}
    assert (form["P7"], form["P8"]) == ("1,5", "0,7")
    assert {name: value for name, value in form.items() if value} == {
        name: value for name, value in expected.items() if value
    }
    assert len(consultations(database)) == 2
    assert "takie same jak w ostatniej konsultacji" in page


def test_case_dates_are_shown_in_polish_time(client, database):
    values = validate({**INTERVIEW_DEFAULTS, "P1": "30"}).values
    summer = Consultation(
        created_at=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
        parameters=form_values(values),
        derived={},
        fired_rules=[],
        rules_version="0" * 64,
    )
    database.session.add(Case(label="P-001", consultations=[summer]))
    database.session.commit()

    assert "01.07.2026, 10:00" in client.get("/historia/P-001").get_data(as_text=True)


@pytest.mark.parametrize("url", ["/", "/konsultacja", "/slownik", "/historia"])
def test_every_page_links_to_history(client, database, url):
    assert 'href="/historia"' in client.get(url).get_data(as_text=True)

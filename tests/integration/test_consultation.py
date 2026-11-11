from app.engine.parameters import PARAMETERS
from app.forms import INTERVIEW_DEFAULTS


def submit(client, **changes):
    return client.post("/konsultacja", data={**INTERVIEW_DEFAULTS, "P1": "30", **changes})


def test_form_shows_every_parameter_with_its_code(client):
    page = client.get("/konsultacja").get_data(as_text=True)

    assert "Dorosły pacjent z podejrzeniem celiakii lub z grupy ryzyka" in page
    for param in PARAMETERS.values():
        assert f'href="/slownik#{param.id}"' in page
        assert f'id="tip-{param.id}"' in page


def test_form_marks_conditional_fields_for_the_browser(client):
    page = client.get("/konsultacja").get_data(as_text=True)

    assert 'data-show-param="P2"' in page
    assert 'data-show-param="P13"' in page


def test_interview_only_consultation_recommends_first_line_serology(client):
    response = submit(client)

    assert response.status_code == 200
    assert "G1-01" in response.get_data(as_text=True)


def test_invalid_form_is_shown_again_with_errors_and_entered_values(client):
    response = submit(client, P1="", P3="abc")
    page = response.get_data(as_text=True)

    assert response.status_code == 422
    assert "wiek: wartość wymagana" in page
    assert 'value="abc"' in page


def test_form_banner_lists_only_errors_without_their_own_field(client):
    page = submit(client, P1="", P18="tak").get_data(as_text=True)
    banner = page.split("Formularz zawiera błędy")[1].split("</div>")[0]

    assert "nieznane pole: P18" in banner
    assert "wiek: wartość wymagana" not in banner
    assert "wiek: wartość wymagana" in page


def test_restricted_diet_requires_gluten_challenge_answer(client):
    response = submit(client, P2="ograniczone")

    assert response.status_code == 422
    assert "prowokacja glutenem zakończona (wg zaleconego schematu): wartość wymagana" in (
        response.get_data(as_text=True)
    )


def test_number_in_exponent_notation_is_rejected_without_server_error(client):
    response = submit(client, P3="1", P4="1e999999")

    assert response.status_code == 422
    assert "GGN laboratorium dla wyniku 1: wymagana liczba" in response.get_data(as_text=True)


def test_inconsistent_results_are_shown_as_warning(client):
    response = submit(client, P3="20", P4="10", P7="0,05", P8="0,7")

    assert response.status_code == 200
    assert "wyniki niespójne" in response.get_data(as_text=True)


def test_high_titre_under_45_offers_no_biopsy_path(client):
    page = submit(client, P3="150", P4="10", P7="1,5", P8="0,7").get_data(as_text=True)

    assert "G2-01" in page
    assert "Rekomendacje" in page


def test_result_links_each_rule_to_the_glossary(client):
    page = submit(client).get_data(as_text=True)

    assert 'href="/slownik#G1-01"' in page
    assert "Reguła z grupy G1 (serologia wstępna), poziom: rekomendacja." in page


def test_result_keeps_entered_data_for_correction(client):
    page = submit(client, P3="150", P4="10").get_data(as_text=True)

    assert '<input type="hidden" name="P3" value="150">' in page
    assert "Popraw dane" in page


def test_correction_shows_form_with_entered_data(client):
    response = client.post(
        "/konsultacja/popraw", data={**INTERVIEW_DEFAULTS, "P1": "30", "P3": "150"}
    )
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'value="150"' in page
    assert "Formularz zawiera błędy" not in page

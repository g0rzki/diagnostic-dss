# System wspomagania decyzji diagnostycznych oparty na regułach eksperckich i danych pacjentów

> Praca inżynierska, Piotr Gorzkiewicz  
> Uniwersytet Rzeszowski, Wydział Nauk Ścisłych i Technicznych  
> Kierunek: Informatyka  
> Promotor: dr inż. Przemysław Pardel

---

## O projekcie

Celem pracy jest zaprojektowanie i implementacja prototypu **systemu wspomagania decyzji (DSS)**, który integruje wiedzę ekspercką z danymi pacjentów w celu wsparcia procesu diagnostycznego.

Współczesna medycyna generuje ogromne ilości danych klinicznych, a lekarze muszą na bieżąco łączyć je z wytycznymi i doświadczeniem eksperckim, często w warunkach presji czasowej i złożoności przypadków. System ma to ułatwić poprzez automatyczne generowanie czytelnych i interpretowalnych rekomendacji diagnostycznych.

System łączy dwa podejścia:

- **reguły eksperckie** oparte na wytycznych klinicznych, jawne i możliwe do prześledzenia,
- **model uczenia maszynowego**, który uzupełnia reguły tam, gdzie wytyczne nie dają jednoznacznej odpowiedzi.

Prototyp nie zastępuje decyzji lekarza i nie jest przeznaczony do użytku klinicznego.

---

## Dziedzina: diagnostyka celiakii u dorosłych

Pierwsza wersja systemu dotyczy diagnostyki celiakii u dorosłego pacjenta (≥ 18 lat) z podejrzeniem choroby lub z grupy ryzyka, przed ustaleniem rozpoznania. Lekarz wpisuje dane, które są już znane (wywiad, serologia, histopatologia, HLA). Niepełne dane są normalnym stanem diagnostyki: system wskazuje kolejny krok na podstawie dostępnych wyników.

Baza wiedzy:

| Element | Liczba |
|---|---|
| dane wejściowe (P1–P17) | 17 |
| wartości wyliczane (D1–D9) | 11 (D1 i D2 także dla drugiej próbki) |
| reguły | 45 w czterech grupach: G1 serologia wstępna (7), G2 ścieżka bez biopsji (10), G3 biopsja i histologia (17), G4 sytuacje szczególne (11) |
| poziomy komunikatów | rekomendacja (29), ostrzeżenie (4), informacja (12) |

Źródła wiedzy:

- **ESsCD 2025 cz. 1**: Al-Toma i wsp. European Society for the Study of Coeliac Disease 2025 Updated Guidelines on the Diagnosis and Management of Coeliac Disease in Adults. Part 1: Diagnostic Approach. United European Gastroenterology Journal 2025;13(10):1855–1886. doi:10.1002/ueg2.70119
- **PTG-E 2026**: Gawron-Kiszka i wsp. Wytyczne postępowania w celiakii – rekomendacje Sekcji Jelitowej Polskiego Towarzystwa Gastroenterologii. Gastroenterology Review 2026;21(3). doi:10.5114/pg.2026.164973

Warunki reguł i oceny GRADE pochodzą z ESsCD. Gdy wytyczne się różnią, kierunek reguły wyznacza PTG-E, a stanowisko ESsCD jest podane we wniosku reguły.

---

## Zakres funkcjonalny

- Formularz do wprowadzania danych pacjenta
- Moduł reguł eksperckich przetwarzający dane wejściowe
- Generowanie rekomendacji diagnostycznych wraz z wyjaśnieniem, które reguły zadziałały i z jakiego źródła pochodzą
- Możliwość dodawania i modyfikowania reguł bez ingerencji w kod
- Komponent uczenia maszynowego jako uzupełnienie podejścia regułowego (regresja logistyczna, drzewa decyzyjne)
- Prezentacja wyników w przejrzystej formie webowej

Stan realizacji jest opisany w sekcji [Status projektu](#status-projektu).

---

## Korzystanie z aplikacji

| Adres | Strona |
|---|---|
| http://localhost:8000 | strona startowa |
| http://localhost:8000/konsultacja | formularz konsultacji |
| http://localhost:8000/slownik | słownik oznaczeń: dane wejściowe, wartości wyliczane, reguły ze stronami źródeł |

Po wypełnieniu formularza i kliknięciu **Oceń** strona wyniku pokazuje komunikaty reguł podzielone na rekomendacje, ostrzeżenia i informacje. **Popraw dane** wraca do formularza z wpisanymi wartościami, więc jedną ścieżkę diagnostyczną można przejść etapami. Najechanie na kod (P1, G2-01 itd.) pokazuje opis, a kliknięcie otwiera słownik na tym kodzie.

Przykładowe dane (pola nie wymienione zostają z wartościami domyślnymi):

| Dane | Oczekiwany wynik |
|---|---|
| wiek 30 | G1-01: zleć badania pierwszego rzutu |
| wiek 30, anty-TG2 IgA 150, GGN 10, IgA całkowite 1,5, dolna granica normy 0,7 | G2-01: ścieżka bez biopsji możliwa, omów z pacjentem |
| jak wyżej, wiek 45 | G2-07: ścieżka bez biopsji nie ma zastosowania, oraz G3-03: protokół pobrania wycinków |
| wiek 30, spożycie glutenu ograniczone, prowokacja zakończona: nie | G4-04: HLA przed prowokacją, ostrzeżenie G1-02, informacja G4-07 |

---

## Architektura systemu

System zbudowany jest w podejściu warstwowym:

- **Warstwa prezentacji**: interfejs webowy (szablony Jinja2, Tailwind CSS)
- **Warstwa logiki biznesowej**: aplikacja Flask, silnik reguł eksperckich, integracja modeli ML
- **Warstwa danych**: PostgreSQL (dane pacjentów, reguły eksperckie)

Przepływ konsultacji: formularz → walidacja danych → wartości wyliczane → ocena reguł → strona wyniku.

Środowisko uruchomieniowe składa się z trzech kontenerów Docker:

| Kontener | Rola |
|---|---|
| `db` | baza danych PostgreSQL 16 |
| `backend` | aplikacja Flask uruchamiana przez serwer gunicorn |
| `frontend` | budowanie arkusza stylów Tailwind CSS na podstawie szablonów |

---

## Stos technologiczny

| Obszar | Technologia |
|---|---|
| Backend | Python 3.12, Flask, gunicorn |
| Baza danych | PostgreSQL 16, SQLAlchemy, psycopg |
| Reguły | YAML (PyYAML) |
| Frontend | HTML (Jinja2), Tailwind CSS |
| ML / analiza danych | Scikit-learn, Pandas, NumPy |
| Testy i jakość kodu | pytest, ruff |
| Środowisko | Docker, Docker Compose |

---

## Struktura repozytorium

```
app/
  engine/            logika domenowa, niezależna od Flaska
    parameters.py    rejestr danych wejściowych P1–P17 (typy, zakresy, pola warunkowe)
    validation.py    walidacja i normalizacja danych z formularza
    derived.py       wartości wyliczane D1–D9
    rules.py         wczytywanie i sprawdzanie plików reguł
    engine.py        ocena reguł dla danych pacjenta
  rules/             baza reguł: g1.yaml…g4.yaml, sources.yaml
  forms.py           układ formularza, wartości domyślne, podpowiedzi
  glossary.py        treść słownika oznaczeń i podpowiedzi przy kodach
  routes.py          trasy (adresy URL)
  templates/         szablony HTML
  static/css/        style (input.css: źródło, output.css: budowany automatycznie)
  static/js/         pokazywanie pól warunkowych w formularzu
tests/
  unit/              testy bez aplikacji i bazy danych
    data/            przypadki testowe reguł i próbki plików reguł
  integration/       testy aplikacji Flask
docker/              pliki Dockerfile i skrypty inicjalizacyjne kontenerów
compose.yaml         definicja środowiska uruchomieniowego
.env.example         przykładowa konfiguracja lokalna
```

---

## Uruchomienie

### Wymagania

- Docker z Docker Compose (Docker Desktop na Windows i macOS, Docker Engine na Linux; na macOS alternatywnie Colima)
- Git

### Start aplikacji

```bash
git clone https://github.com/g0rzki/diagnostic-dss.git
cd diagnostic-dss
docker compose up -d
```

Aplikacja jest dostępna pod adresem http://localhost:8000.

Pierwsze uruchomienie trwa dłużej, bo Docker pobiera obrazy i buduje kontenery (obraz `frontend` pobiera program Tailwind CSS).

### Sprawdzenie działania

```bash
docker compose ps
curl http://localhost:8000/health
```

Endpoint `/health` zwraca `{"status": "ok", "database": "ok"}`, gdy aplikacja działa i ma połączenie z bazą danych.

### Zatrzymanie

```bash
docker compose stop
```

Dane bazy są przechowywane w wolumenie Docker i nie są tracone przy zatrzymaniu. Polecenie `docker compose down -v` usuwa kontenery razem z bazą danych.

---

## Konfiguracja

Projekt działa bez dodatkowej konfiguracji. Aby zmienić ustawienia domyślne (np. port bazy danych zajęty przez inną aplikację), należy skopiować plik przykładowy i zmienić wartości:

```bash
cp .env.example .env
```

Opis zmiennych znajduje się w pliku `.env.example`.

---

## Baza reguł

Reguły są zapisane w plikach `app/rules/g1.yaml`…`g4.yaml`, po jednym na grupę. Każda reguła zawiera:

- identyfikator, nazwę, grupę i poziom (rekomendacja, ostrzeżenie, informacja),
- warunek zapisany na danych wejściowych i wartościach wyliczanych, w dwóch postaciach: tekstowej (`condition_text`, wyświetlanej lekarzowi) i maszynowej (`condition`),
- listę danych wejściowych czytanych przez warunek (`uses`),
- wniosek dla lekarza,
- źródło w ESsCD (miejsce, strona, rodzaj fragmentu, ocena GRADE) i zgodność z PTG-E.

Przykład warunku maszynowego:

```yaml
condition:
  all:
    - [D4, '=', true]
    - [P12, '=', nie omówiono]
```

Pliki reguł są wczytywane i sprawdzane przy starcie aplikacji: nieznane pola, wartości spoza listy, niezgodność `uses` z warunkiem i inne błędy zatrzymują start z listą wszystkich problemów. Po zmianie plików reguł trzeba zrestartować backend:

```bash
docker compose restart backend
```

Każda reguła ma przypadki testowe w `tests/unit/data/catalog_cases.yaml` (dane, przy których reguła się uruchamia, i dane, przy których milczy).

---

## Praca deweloperska

### Środowisko lokalne

Do uruchamiania testów i narzędzi potrzebny jest Python 3.12:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### Testy

Testy jednostkowe nie wymagają Dockera:

```bash
pytest tests/unit
```

Testy integracyjne korzystają z osobnej bazy `dss_test`, więc wymagają działającego kontenera bazy danych:

```bash
docker compose up -d db
pytest
```

Testy jednej reguły:

```bash
pytest tests/unit/test_rule_base.py -k "G2-03"
```

### Jakość kodu

```bash
ruff check .
ruff format .
```

### Logi i debugowanie

```bash
docker compose logs -f backend
```

Zmiany w kodzie Pythona i w szablonach są widoczne bez restartu (gunicorn z `--reload`, tryb debug Flaska). Dwa wyjątki:

- **pliki reguł** są wczytywane przy starcie, więc po ich zmianie potrzebny jest `docker compose restart backend`;
- **arkusz stylów** jest budowany przez kontener `frontend`. Na macOS (Colima) kontener może nie zauważyć zmian w szablonach. Gdy po zmianie szablonu brakuje stylów albo podpowiedzi przy kodach nie działają, należy wykonać `docker compose restart frontend` i odświeżyć stronę z pominięciem pamięci podręcznej (Cmd+Shift+R).

Do debugowania z interaktywnym debuggerem Flaska aplikację można uruchomić lokalnie, równolegle z kontenerami:

```bash
flask run --port 8001
```

---

## Status projektu

Projekt jest w trakcie realizacji (praca inżynierska 2026/2027).

- [x] Szkielet aplikacji: Flask, PostgreSQL, Docker, testy, layout
- [x] Baza wiedzy: 45 reguł diagnostyki celiakii u dorosłych, zweryfikowanych z wytycznymi ESsCD 2025 i PTG-E 2026
- [x] Silnik reguł eksperckich, walidacja danych i formularz konsultacji
- [x] Strona wyniku i słownik oznaczeń
- [ ] Pełne uzasadnienie reguły przy wyniku (warunek, źródło, ocena GRADE, wpisane i wyliczone dane)
- [ ] Przechowywanie reguł i historii konsultacji w bazie danych
- [ ] Komponent uczenia maszynowego i łączenie wyników
- [ ] Panel zarządzania regułami
- [ ] Ewaluacja systemu

---

## Autor

**Piotr Gorzkiewicz**

Uniwersytet Rzeszowski
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

Poza zakresem są diagnostyka u dzieci, leczenie i monitorowanie chorych z ustalonym rozpoznaniem.

---

## Baza wiedzy

Baza wiedzy składa się z danych wejściowych (kody P), wartości wyliczanych przez system (kody D) i reguł (kody G). Warunek każdej reguły jest zapisany na danych wejściowych i wartościach wyliczanych.

### Dane wejściowe

| Kod | Dana | Wartości | Wymagana |
|---|---|---|---|
| P1 | wiek | liczba całkowita 18–120 [lata] | tak |
| P2 | spożycie glutenu w okresie badań | normalne / ograniczone | tak |
| P3 | anty-TG2 IgA, wynik 1 | liczba > 0 | nie |
| P4 | GGN laboratorium dla wyniku 1 | liczba > 0 | gdy podano P3 |
| P5 | anty-TG2 IgA, wynik 2 (druga próbka) | liczba > 0 | nie |
| P6 | GGN laboratorium dla wyniku 2 | liczba > 0 | gdy podano P5 |
| P7 | IgA całkowite | liczba ≥ 0 [g/L] | nie |
| P8 | dolna granica normy IgA całkowitego | liczba > 0,07 [g/L] | gdy podano P7 |
| P9 | testy IgG (anty-TG2 IgG / anty-DGP IgG) | dodatni / ujemny / nie wykonano | tak |
| P10 | objawy złego wchłaniania sugerujące celiakię | tak / nie | tak |
| P11 | objawy alarmowe | tak / nie | tak |
| P12 | zgoda pacjenta na ścieżkę bez biopsji | nie omówiono / tak / nie | tak |
| P13 | stopień Marsha | nie wykonano / 0 / 1 / 2 / 3 | tak |
| P14 | liczba wycinków (część dalsza dwunastnicy, opuszka) | dwie liczby całkowite ≥ 0 | gdy P13 ≠ nie wykonano |
| P15 | HLA-DQ2/DQ8 | dodatni / ujemny / nie badano | tak |
| P16 | prowokacja glutenem zakończona (wg zaleconego schematu) | tak / nie | gdy P2 = ograniczone |
| P17 | krewny 1. stopnia z celiakią | tak / nie | tak |

GGN to górna granica normy podana przez laboratorium. Krotność GGN liczy system, lekarz wpisuje wynik i granicę z wydruku.

### Wartości wyliczane

| Kod | Wartość | Definicja |
|---|---|---|
| D1, D1_2 | anty-TG2 IgA (wynik 1, wynik 2) | dodatni, gdy wynik > GGN; ujemny, gdy wynik ≤ GGN |
| D2, D2_2 | wysokie miano anty-TG2 IgA (wynik 1, wynik 2) | wynik ≥ 10 × GGN |
| D3 | IgA całkowite | niedobór całkowity (< 0,07 g/L), niedobór częściowy (poniżej dolnej granicy normy) albo norma |
| D4 | ścieżka bez biopsji dostępna | wysokie miano, wiek < 45 lat, brak objawów alarmowych, dieta z glutenem, histologia niewykonana, brak całkowitego niedoboru IgA, HLA nie ujemne |
| D5 | status serologii swoistej | dodatnia, ujemna albo nieustalona (z anty-TG2 IgA, IgA całkowitego i testów IgG) |
| D6 | niskie miano anty-TG2 IgA | GGN < wynik < 10 × GGN, bez całkowitego niedoboru IgA |
| D7 | wystarczająca liczba wycinków | co najmniej 4 z części dalszej i co najmniej 1 z opuszki |
| D8 | spożycie glutenu wystarczające do oceny | dieta z glutenem albo zakończona prowokacja glutenem |
| D9 | ścieżka bez biopsji w toku | ścieżka dostępna, pacjent nie odmówił, druga próbka nie jest ujemna |

Pełne definicje są w słowniku oznaczeń w aplikacji (`/slownik`) i w `app/engine/derived.py`.

### Reguły

| Grupa | Zakres | Rekomendacje | Ostrzeżenia | Informacje | Razem |
|---|---|---|---|---|---|
| G1 serologia wstępna | badania pierwszego rzutu, badanie krewnych, ograniczony gluten, niedobór IgA przed testami IgG, ujemny wynik przed biopsją | 3 | 1 | 3 | 7 |
| G2 ścieżka bez biopsji | anty-TG2 IgA ≥ 10 × GGN przed histologią: warunki wstępne, zgoda pacjenta, druga próbka, sytuacje bez zastosowania | 7 | 0 | 3 | 10 |
| G3 biopsja i histologia | wskazanie do biopsji, protokół wycinków, stopień Marsha w zestawieniu z serologią, czynniki zaniżające obraz histologiczny | 11 | 3 | 3 | 17 |
| G4 sytuacje szczególne | niedobór IgA po testach IgG, dieta ograniczona (HLA, prowokacja), stan po prowokacji, wykluczenie przez ujemne HLA | 8 | 0 | 3 | 11 |
| **Razem** | | **29** | **4** | **12** | **45** |

Poziomy komunikatów:

- **rekomendacja** wskazuje kolejny krok diagnostyczny albo wniosek diagnostyczny;
- **ostrzeżenie** sygnalizuje czynnik, który może zafałszować wynik;
- **informacja** pokazuje niejednoznaczność lub rozbieżność źródeł albo opcję do rozważenia; decyzja należy do lekarza.

Każda reguła ma źródło w ESsCD (miejsce w wytycznych ze stroną, rodzaj fragmentu i ocenę GRADE, jeśli jest przypisana; 24 reguły mają ocenę GRADE) oraz status zgodności z PTG-E: zgodność (30 reguł), różnica (13), brak odniesienia (2). Przy 9 z 13 reguł z różnicą kierunek reguły wyznacza PTG-E. Pozostałe 4 to trzy reguły informacyjne, które pokazują rozbieżność (G1-04, G2-09, G4-07), i G4-02, gdzie stanowisko PTG-E wynika tylko z ryciny, więc kierunek pochodzi z ESsCD.

### Weryfikacja bazy wiedzy

- Każda reguła opiera się na dosłownych cytatach z wytycznych. Wszystkie 288 cytatów sprawdzono automatycznie w tekście plików PDF na wskazanej stronie. Katalog wiedzy z cytatami jest przechowywany poza repozytorium; w repozytorium są reguły w postaci wykonywalnej.
- Silnik reguł uruchomiono na 2 628 288 stanach, czyli na wszystkich kombinacjach kategorii wyników i wartości progowych: żadna para reguł nie daje przeciwstawnych wniosków, a stan bez żadnej reguły występuje tylko przy danych fizjologicznie niespójnych (dodatnie anty-TG2 IgA przy IgA całkowitym < 0,07 g/L), które sygnalizuje walidacja formularza.
- Dla każdej reguły są przypadki testowe, w których reguła się uruchamia i w których milczy (192 przypadki w `tests/unit/data/catalog_cases.yaml`), sprawdzane przy każdym uruchomieniu testów.

### Źródła wiedzy

| Źródło | Opis bibliograficzny | Rola w systemie |
|---|---|---|
| ESsCD 2025 cz. 1 | Al-Toma A. i wsp. European Society for the Study of Coeliac Disease 2025 Updated Guidelines on the Diagnosis and Management of Coeliac Disease in Adults. Part 1: Diagnostic Approach. *United European Gastroenterology Journal* 2025;13(10):1855–1886. [doi:10.1002/ueg2.70119](https://doi.org/10.1002/ueg2.70119) | warunki reguł i oceny GRADE; strony według paginacji czasopisma |
| PTG-E 2026 | Gawron-Kiszka M. i wsp. Wytyczne postępowania w celiakii – rekomendacje Sekcji Jelitowej Polskiego Towarzystwa Gastroenterologii. *Gastroenterology Review* 2026;21(3). [doi:10.5114/pg.2026.164973](https://doi.org/10.5114/pg.2026.164973) | zgodność z zaleceniami krajowymi, kierunek części reguł przy rozbieżności źródeł, polska terminologia; strony według numeracji artykułu |

Kierunek reguły pochodzi z ESsCD. Wyjątkiem są reguły oznaczone w słowniku „kierunek reguły według PTG-E”: przy rozbieżności źródeł przyjęto w nich stanowisko PTG-E.

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

Po uruchomieniu (sekcja [Uruchomienie](#uruchomienie)) aplikacja działa lokalnie pod adresem http://localhost:8000.

| Ścieżka | Strona |
|---|---|
| `/` | strona startowa |
| `/konsultacja` | formularz konsultacji |
| `/slownik` | słownik oznaczeń: dane wejściowe, wartości wyliczane, reguły ze stronami źródeł |

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

## Pliki reguł

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
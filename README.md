# System wspomagania decyzji diagnostycznych oparty na regułach eksperckich i danych pacjentów

> Praca inżynierska - Piotr Gorzkiewicz  
> Uniwersytet Rzeszowski, Wydział Nauk Ścisłych i Technicznych  
> Kierunek: Informatyka  
> Promotor: dr inż. Przemysław Pardel

---

## O projekcie

Celem pracy jest zaprojektowanie i implementacja prototypu **systemu wspomagania decyzji (DSS)**, który integruje wiedzę ekspercką z danymi pacjentów w celu wsparcia procesu diagnostycznego.

Współczesna medycyna generuje ogromne ilości danych klinicznych, a lekarze muszą na bieżąco łączyć je z wytycznymi i doświadczeniem eksperckim, często w warunkach presji czasowej i złożoności przypadków. System ma to ułatwić poprzez automatyczne generowanie czytelnych i interpretowalnych rekomendacji diagnostycznych.

System łączy dwa podejścia:

- **reguły eksperckie** oparte na wytycznych klinicznych - jawne, możliwe do prześledzenia i uzasadnienia,
- **model uczenia maszynowego** - uzupełnia reguły tam, gdzie wytyczne nie dają jednoznacznej odpowiedzi.

---

## Zakres funkcjonalny

- Formularz do wprowadzania danych pacjenta
- Moduł reguł eksperckich przetwarzający dane wejściowe
- Generowanie rekomendacji diagnostycznych i oceny poziomu ryzyka wraz z wyjaśnieniem, które reguły zadziałały
- Możliwość dodawania i modyfikowania reguł bez ingerencji w kod
- Komponent uczenia maszynowego jako uzupełnienie podejścia regułowego (regresja logistyczna, drzewa decyzyjne)
- Prezentacja wyników w przejrzystej formie webowej

---

## Architektura systemu

System zbudowany jest w podejściu warstwowym:

- **Warstwa prezentacji** - interfejs webowy (szablony HTML, Tailwind CSS)
- **Warstwa logiki biznesowej** - aplikacja Flask, silnik reguł eksperckich, integracja modeli ML
- **Warstwa danych** - PostgreSQL (dane pacjentów, reguły eksperckie)

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
| Frontend | HTML (Jinja2), Tailwind CSS |
| ML / analiza danych | Scikit-learn, Pandas, NumPy |
| Testy i jakość kodu | pytest, ruff |
| Środowisko | Docker, Docker Compose |

---

## Struktura repozytorium

```
app/                 kod aplikacji
  templates/         szablony HTML
  static/css/        style (input.css - źródło, output.css - budowany automatycznie)
  config.py          konfiguracja aplikacji
  routes.py          trasy (adresy URL)
tests/               testy automatyczne
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

Pierwsze uruchomienie trwa dłużej - Docker pobiera obrazy i buduje kontenery.

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

## Praca deweloperska

### Środowisko lokalne

Do uruchamiania testów i narzędzi potrzebny jest Python 3.12:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### Testy

Testy wymagają działającego kontenera bazy danych (korzystają z osobnej bazy `dss_test`):

```bash
docker compose up -d db
pytest
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

Zmiany w kodzie i szablonach są widoczne bez restartu kontenerów. Do debugowania z interaktywnym debuggerem Flaska aplikację można uruchomić lokalnie, równolegle z kontenerami:

```bash
flask run --port 8001
```

---

## Status projektu

Projekt jest w trakcie realizacji (praca inżynierska 2026/2027).

- [x] Szkielet aplikacji: Flask, PostgreSQL, Docker, testy, layout
- [ ] Silnik reguł eksperckich i formularz danych pacjenta
- [ ] Przechowywanie reguł i historii konsultacji w bazie danych
- [ ] Komponent uczenia maszynowego i łączenie wyników
- [ ] Panel zarządzania regułami
- [ ] Ewaluacja systemu

---

## Autor

**Piotr Gorzkiewicz**

Uniwersytet Rzeszowski

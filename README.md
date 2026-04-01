# System wspomagania decyzji diagnostycznych oparty na regułach eksperckich i danych pacjentów

> Praca inżynierska — Piotr Gorzkiewicz  
> Uniwersytet Rzeszowski, Wydział Nauk Ścisłych i Technicznych  
> Kierunek: Informatyka  
> Promotor: Dr inż. Przemysław Pardel

---

## O projekcie

Celem pracy jest zaprojektowanie i implementacja prototypu **systemu wspomagania decyzji (DSS)**, który integruje wiedzę ekspercką z danymi pacjentów w celu wsparcia procesu diagnostycznego.

Współczesna medycyna generuje ogromne ilości danych klinicznych, a lekarze muszą na bieżąco łączyć je z wytycznymi i doświadczeniem eksperckim — często w warunkach presji czasowej i złożoności przypadków. System ma to ułatwić poprzez automatyczne generowanie czytelnych i interpretowalnych rekomendacji diagnostycznych.

---

## Zakres funkcjonalny

- Formularz do wprowadzania danych pacjenta
- Moduł reguł eksperckich przetwarzający dane wejściowe (silnik reguł if-else / konfigurowalny)
- Generowanie rekomendacji diagnostycznych i oceny poziomu ryzyka
- Możliwość łatwego dodawania i modyfikowania reguł bez ingerencji w kod
- Komponent uczenia maszynowego jako uzupełnienie podejścia regułowego (regresja logistyczna, drzewa decyzyjne)
- Prezentacja wyników w przejrzystej formie webowej

---

## Architektura systemu

System zbudowany jest w podejściu warstwowym:

- **Warstwa prezentacji** — interfejs webowy (HTML + Tailwind CSS)
- **Warstwa logiki biznesowej** — backend Flask (Python), silnik reguł eksperckich, integracja modeli ML
- **Warstwa danych** — PostgreSQL (dane pacjentów, reguły eksperckie)

---

## Stos technologiczny

| Warstwa | Technologia |
|---|---|
| Backend | Python, Flask |
| Baza danych | PostgreSQL |
| Frontend | HTML, Tailwind CSS |
| ML / Analiza danych | Scikit-learn, Pandas, NumPy |

---

## Status projektu

Projekt jest w trakcie realizacji (praca inżynierska 2026/2027).

---

## Autor

**Piotr Gorzkiewicz**

Uniwersytet Rzeszowski

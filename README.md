# Analiza partii szachowych Lichess — Projekt 1 (Big Data)

Aplikacja pobiera partie szachowe z serwisu Lichess (listopad–grudzień 2016),
sprawdza i czyści dane, importuje je do lokalnej bazy MongoDB, wykonuje analizy
statystyczne w modelu MapReduce, zapisuje wyniki w MongoDB i rysuje wykresy.

## Źródło danych

- Zbiór: [Lichess/standard-chess-games](https://huggingface.co/datasets/Lichess/standard-chess-games) (Hugging Face, format Apache Parquet)
- Oryginalne źródło: [database.lichess.org](https://database.lichess.org)
- Licencja: CC0 (domena publiczna)
- Zakres: 2016-11 i 2016-12, 28 plików Parquet

| Etap | Rozmiar | Liczba partii |
|---|---|---|
| Parquet (pobrane) | 6,3 GB | 17 454 921 |
| TSV (po czyszczeniu, rozpakowane) | 12 GB | 17 357 441 |
| MongoDB, kolekcja `games` (bez zapisu ruchów) | 5,4 GB danych / 1,8 GB na dysku | 17 357 441 |

Dane nie są dołączone do repozytorium. Pobiera je skrypt `download.py`.

## Wymagania

- Python 3.12
- Docker z Docker Compose
- ok. 30 GB wolnego miejsca na dysku

## Uruchomienie

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
docker compose up -d          # uruchamia MongoDB

python pull_data.py            # pobranie danych (python download.py test → tylko 1 plik)
python prepare.py             # sprawdzanie i czyszczenie danych, Parquet → TSV
python import_games.py        # import do MongoDB (python import_games.py force → ponowny import)
python run_analyses.py        # analizy MapReduce, wyniki do MongoDB
python charts.py              # wykresy do katalogu charts/
```

Każdy krok można uruchomić ponownie. Pliki już przetworzone są pomijane,
a ponowny import nie tworzy duplikatów (identyfikator partii jest kluczem `_id`,
zapis odbywa się przez upsert).

## Czyszczenie danych

Odrzucane są partie, które:
- mają wynik inny niż `1-0`, `0-1`, `1/2-1/2` (np. `*` — partia nierozstrzygnięta),
- zostały porzucone (`Termination = Abandoned`),
- nie mają rankingu jednego z graczy,
- były rozgrywane przez konto komputerowe (`BOT`),
- nie zawierają zapisu ruchów.

Statystyki czyszczenia (łącznie i dla każdego pliku) zapisywane są w `data/tsv/cleaning_stats.json`.

## Analizy

Każda analiza to para skryptów mapper i reducer w katalogu `map_reducer/`,
zgodnych z Hadoop Streaming (czytają `stdin`, piszą `klucz<TAB>wartość` na `stdout`).
Lokalnie uruchamiane są jako potok:

```bash
cat data/tsv/*.tsv | python map_reducer/elo_results_mapper.py | LC_ALL=C sort | python map_reducer/count_results_reducer.py
```

| Analiza | Mapper | Reducer | Pytanie |
|---|---|---|---|
| `elo_results` | `elo_results_mapper.py` | `count_results_reducer.py` | jak wynik partii zależy od średniego rankingu graczy? |
| `opening_results` | `opening_results_mapper.py` | `count_results_reducer.py` | które rodziny debiutów są najpopularniejsze i jak w nich wypadają białe? |
| `speed_length` | `speed_length_mapper.py` | `stats_reducer.py` | jak długie są partie w poszczególnych tempach gry? |

Wyniki trafiają do kolekcji `results` (jeden dokument na analizę), a wykresy (`charts.py`) są rysowane na ich podstawie.

## Struktura projektu

| Plik / katalog | Rola |
|---|---|
| `config.py` | wspólne ustawienia (adres bazy, katalogi, zakres miesięcy) |
| `download.py` | pobiera pliki Parquet z Hugging Face |
| `prepare.py` | czyści dane i zapisuje je jako TSV (jedna partia = jedna linia, bez nagłówka) |
| `import_games.py` | importuje partie do kolekcji `games`, dziennik importu w kolekcji `imports` |
| `map_reducer/` | mappery i reducery |
| `run_analyses.py` | uruchamia potoki `mapper \| sort \| reducer`, zapisuje wyniki do kolekcji `results` |
| `charts.py` | rysuje wykresy na podstawie kolekcji `results` |
| `docker-compose.yml` | kontener MongoDB |

## Kolekcje w MongoDB (baza `lichess`)

| Kolekcja | Zawartość |
|---|---|
| `games` | partie (bez zapisu ruchów), `_id` = identyfikator partii z Lichess |
| `imports` | dziennik importu: jeden dokument na plik TSV (liczba wierszy, czas importu) |
| `results` | wyniki analiz: jeden dokument na analizę (wiersze wyniku, czas wykonania) |

## Usunięcie wszystkiego po zakończeniu

```bash
docker compose down -v
rm -rf data charts
```
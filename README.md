# Analiza partii szachowych Lichess — Projekt 1 (Big Data)

Aplikacja pobiera partie szachowe z serwisu Lichess (listopad–grudzień 2016),
sprawdza i czyści dane, importuje je do lokalnej bazy MongoDB, pobiera metadane źródła metodą web scrapingu,
zapisuje główny zbiór w HDFS, wykonuje analizy statystyczne w modelu MapReduce (lokalnie i w Hadoop Streaming),
zapisuje wyniki w dwóch bazach MongoDB (lokalnej i Atlas, połączenia szyfrowane TLS z uwierzytelnieniem) i rysuje wykresy.

## Źródło danych

- Zbiór: [Lichess/standard-chess-games](https://huggingface.co/datasets/Lichess/standard-chess-games) (Hugging Face, format Apache Parquet)
- Oryginalne źródło: [database.lichess.org](https://database.lichess.org)
- Licencja: CC0 (domena publiczna)
- Zakres: 2016-11 i 2016-12, 28 plików Parquet

| Etap | Rozmiar | Liczba partii |
|---|---|---|
| Parquet (pobrane) | 6,3 GB | 17 454 921 |
| TSV (po czyszczeniu, rozpakowane) | 12 GB | 17 357 441 |
| HDFS, `/lichess/games` (28 plików, 112 bloków) | 11,5 GiB | 17 357 441 |
| MongoDB, kolekcja `games` (bez zapisu ruchów) | 5,4 GB danych / 1,8 GB na dysku | 17 357 441 |

Dane nie są dołączone do repozytorium. Pobiera je skrypt `pull_data.py`.

## Wymagania

- Python 3.12
- Docker z Docker Compose
- ok. 45 GB wolnego miejsca na dysku (dane surowe, TSV, MongoDB, HDFS)
- ok. 8 GB RAM (kontenery Hadoop + MongoDB)

## Uruchomienie

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

./tls/generate_certs.sh       # certyfikaty TLS dla lokalnej MongoDB
cp .env.example .env          # uzupełnij loginy i hasła
docker compose build          # obraz NodeManagera z Pythonem 3
docker compose up -d          # MongoDB + Hadoop (NameNode, DataNode, ResourceManager, NodeManager)
# jednorazowo: utworzenie użytkownika lokalnej bazy (patrz sekcja „Bezpieczeństwo”)

python check_databases.py     # test połączenia z bazami (lokalna i Atlas)
python check_security.py      # pokazuje, że połączenia bez TLS / bez hasła są odrzucane

python pull_data.py           # pobranie danych (python pull_data.py test → tylko 1 plik)
python prepare.py             # sprawdzanie i czyszczenie danych, Parquet → TSV
python import_games.py        # import do MongoDB (python import_games.py force → ponowny import)
python scrape.py              # web scraping database.lichess.org → kolekcja sources
python hdfs_upload.py         # TSV → HDFS (/lichess/games), metadane plików → kolekcja hdfs_files
python run_analyses.py hadoop # analizy w Hadoop Streaming, wyniki do MongoDB
python run_analyses.py        # te same analizy lokalnie (mapper | sort | reducer) — do porównania
python charts.py              # wykresy do katalogu charts/ (python charts.py atlas → wyniki z Atlasa)
```

Każdy krok można uruchomić ponownie. Pliki już przetworzone są pomijane,
a ponowny import nie tworzy duplikatów (identyfikator partii jest kluczem `_id`,
zapis odbywa się przez upsert).

## Bazy danych

Projekt korzysta z dwóch baz MongoDB (baza `lichess` w obu):
- **lokalna** — kontener Docker (`docker-compose.yml`), adres w `MONGO_URI_LOCAL`,
- **MongoDB Atlas** — darmowy klaster M0 w chmurze, adres w `MONGO_URI_ATLAS`.

Partie (ok. 5,4 GB) przechowywane są tylko lokalnie, ponieważ darmowy klaster Atlas
ma limit 512 MB. Do Atlasa trafiają metadane, dane ze scrapingu i wyniki analiz.

## Bezpieczeństwo

- **Atlas**: połączenie `mongodb+srv://` jest zawsze szyfrowane TLS, wymaga użytkownika i hasła,
  a dostęp jest ograniczony do zadeklarowanych adresów IP (*Network Access*).
- **Lokalna baza**: `mongod` działa z `--tlsMode requireTLS` i `--auth`. Certyfikat serwera
  podpisany jest lokalnym CA (`tls/generate_certs.sh`), klient weryfikuje go plikiem `tls/ca.pem`.
  Aplikacja łączy się jako użytkownik `lichess_app` z rolą `readWrite` tylko w bazie `lichess`.

Utworzenie użytkownika (jednorazowo, na bazie uruchomionej chwilowo bez `--auth`):

```bash
docker exec -it bigdata-mongo mongosh --tls --tlsCAFile /etc/mongo-tls/ca.pem --host localhost admin \
  --eval 'db.createUser({user: "lichess_app", pwd: passwordPrompt(), roles: [{role: "readWrite", db: "lichess"}]})'
```

Klucze i certyfikaty (`tls/`) oraz plik `.env` nie są dołączone do repozytorium.

## Hadoop

Klaster Hadoop 3.4.1 działa w czterech kontenerach (NameNode, DataNode, ResourceManager, NodeManager),
replikacja HDFS = 1. Obraz NodeManagera (`docker/nodemanager/Dockerfile`) zawiera dodatkowo Pythona 3,
potrzebnego do uruchamiania mapperów i reducerów. Konfiguracja: `hadoop.env`.

- `hdfs_upload.py` kopiuje pliki TSV do HDFS (pomija pliki już istniejące) i zapisuje ich listę w kolekcji `hdfs_files`.
- `run_analyses.py hadoop` uruchamia te same skrypty z `map_reducer/` przez `mapred streaming`
  i porównuje wynik z poprzednim przebiegiem lokalnym (wyniki są identyczne).

Panele: HDFS — http://localhost:9870, YARN — http://localhost:8088.

Dane HDFS przechowywane są w kontenerach (bez trwałego wolumenu): `docker compose down`
je usuwa, a ponowne załadowanie wykonuje `hdfs_upload.py`.

## Web scraping

`scrape.py` pobiera stronę [database.lichess.org](https://database.lichess.org)
i odczytuje tabele wszystkich wariantów gry (miesiąc, rozmiar pliku, liczba partii, link).
Dane trafiają do kolekcji `sources` w obu bazach (`_id` = `wariant_miesiąc`, zapis przez upsert).
Liczba partii podana na stronie służy do walidacji pobranego zbioru:
dla 2016-11 i 2016-12 jest równa liczbie wierszy odczytanych z plików Parquet.

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

Wyniki trafiają do kolekcji `results` (jeden dokument na analizę), a czasy przebiegów (lokalnie / Hadoop)
do kolekcji `runs`. Wykresy (`charts.py`) są rysowane na podstawie kolekcji `results`.

## Struktura projektu

| Plik / katalog | Rola |
|---|---|
| `config.py` | wspólne ustawienia (adresy baz, katalogi, zakres miesięcy) |
| `databases.py` | połączenia z bazą lokalną i Atlas |
| `check_databases.py` | test połączenia z bazami i ich rozmiar |
| `check_security.py` | próby połączeń bez TLS / bez hasła / ze złym hasłem |
| `tls/generate_certs.sh` | generuje lokalne CA i certyfikat serwera MongoDB |
| `pull_data.py` | pobiera pliki Parquet z Hugging Face |
| `prepare.py` | czyści dane i zapisuje je jako TSV (jedna partia = jedna linia, bez nagłówka) |
| `import_games.py` | importuje partie do kolekcji `games`, dziennik importu w kolekcji `imports` |
| `scrape.py` | web scraping database.lichess.org do kolekcji `sources`, walidacja zbioru |
| `hadoop.py` | wykonywanie poleceń Hadoopa w kontenerze NameNode |
| `hdfs_upload.py` | ładowanie TSV do HDFS, metadane do kolekcji `hdfs_files` |
| `map_reducer/` | mappery i reducery |
| `run_analyses.py` | uruchamia analizy lokalnie lub w Hadoop Streaming, zapisuje wyniki do `results` i `runs` |
| `charts.py` | rysuje wykresy na podstawie kolekcji `results` |
| `docker-compose.yml` | kontenery MongoDB i Hadoop |
| `hadoop.env` | konfiguracja Hadoopa |
| `docker/nodemanager/Dockerfile` | obraz NodeManagera z Pythonem 3 |

## Kolekcje w MongoDB (baza `lichess`)

| Kolekcja | Zawartość | Lokalna | Atlas |
|---|---|---|---|
| `games` | partie (bez zapisu ruchów), `_id` = identyfikator partii z Lichess | ✅ | ❌ |
| `imports` | dziennik importu: jeden dokument na plik TSV (liczba wierszy, czas importu) | ✅ | ✅ |
| `sources` | dane ze scrapingu: jeden dokument na wariant i miesiąc | ✅ | ✅ |
| `results` | wyniki analiz: jeden dokument na analizę (wiersze wyniku, silnik, czas wykonania) | ✅ | ✅ |
| `runs` | czasy przebiegów: jeden dokument na parę analiza–silnik (`local` / `hadoop`) | ✅ | ✅ |
| `hdfs_files` | metadane plików w HDFS (nazwa, rozmiar) | ✅ | ✅ |

## Usunięcie wszystkiego po zakończeniu

```bash
docker compose down -v
rm -rf data charts tls/*.pem tls/*.key tls/*.crt tls/*.srl
```
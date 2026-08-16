# Herkunft der Fixtures

Aufgezeichnet am **2026-08-15** mit `PYTHONPATH=src python scripts/record_fixtures.py`.

Eine Antwort je **Abfrage**, nicht je Endpunkt: dieser Server spricht mit einem
Suchendpunkt, aber in einem halben Dutzend Abfrageformen — Volltext,
Signatur-Lookup, Gesetzesreferenz, Taxonomie-Aggregation, Datums-Sortierung,
Jahres-Statistik. Eine Datei wuerde die Portfolio-Regel erfuellen und fast
nichts belegen.

Der **Schluessel** unten ist, woran der Test eine Anfrage wiedererkennt: die
URL plus eine Kurzfassung des Elasticsearch-Rumpfes. Ohne den Rumpf waeren alle
Suchen ununterscheidbar — sie gehen an dieselbe Adresse.

Die Antworten stammen aus dem Client von `api_client.new_client()` (gleicher
User-Agent, gleiches Timeout, gleiche Host-Pruefung wie im Betrieb),
abgegriffen ueber einen httpx-Response-Hook. Ausgeloest hat sie jeweils das
Werkzeug selbst — so belegt die Aufzeichnung auch, dass das Werkzeug genau
diese Anfrage schickt.

## Personendaten

Gerichtsentscheide werden von den Gerichten anonymisiert publiziert;
entscheidsuche.ch spiegelt diese Publikationen. Aufgezeichnet sind
Trefferlisten und ein Entscheid — also genau das, was die Gerichte selbst
veroeffentlichen.

## Auswahl

Neu gesetzt ist die Einrueckung; gekuerzt ist allein die **Zahl** der Treffer
in `hits.hits`. Kein Feld eines behaltenen Treffers ist angetastet, und
`hits.total` steht wie geliefert — die Quelle meint damit die Treffer im ganzen
Index, nicht die der Seite. Aggregationen bleiben ungekuerzt: der Server
summiert und filtert *in* ihnen.

Die Fehlerpfade — Timeout, 5xx, leere Trefferliste, der Offline-Fallback —
bleiben handgeschrieben. Sie lassen sich nicht auf Zuruf aufzeichnen und sind
als Erfindung in Ordnung. `scd_sample.csv` ist der Dump-Auszug fuer den
Fallback und keine Aufzeichnung.

## `courts_1.json`

- **Werkzeuge:** `list_courts`
- **Schluessel:** `https://entscheidsuche.ch/docs/Facetten_alle.json`
- **Auswahl:** ungekuerzt — der Server rechnet *in* dieser Antwort, ein Schnitt erfaende ein anderes Ergebnis
- **Groesse:** 115867 Bytes
- **SHA-256:** `06687b3e051086aaaa69ba7269b6a6c719487189bd587ced59eea2ad573a07fb`

## `decision_1.json`

- **Werkzeuge:** `get_court_decision`
- **Schluessel:** `https://entscheidsuche.ch/_searchV2.php#e65565a2c6d1`
- **Rumpf:** `{"query":{"term":{"_id":"NW_OG_001_42526_2026-08-05"}},"size":1}`
- **Auswahl:** ungekuerzt
- **Groesse:** 106026 Bytes
- **SHA-256:** `3df5bc90753ab67585ae3de5f6f6ad8e38b7acaef5f2996cc5297e4b0a4464be`

## `recent_1.json`

- **Werkzeuge:** `get_recent_decisions`
- **Schluessel:** `https://entscheidsuche.ch/_searchV2.php#a64ba064dd82`
- **Rumpf:** `{"size":5,"from":0,"track_total_hits":true,"sort":[{"date":{"order":"desc"}}],"query":{"match_all":{}}}`
- **Auswahl:** die ersten 3 von 5 Treffern, aus 121952 Bytes Rohantwort
- **Groesse:** 53178 Bytes
- **SHA-256:** `1d8654cc1ea2c99dc59e33cd374be43be0e1c398349e5628e3d9e0c6338f4ae8`

## `search_1.json`

- **Werkzeuge:** `search_court_decisions`
- **Schluessel:** `https://entscheidsuche.ch/_searchV2.php#45b4129be534`
- **Rumpf:** `{"size":5,"from":0,"track_total_hits":true,"sort":[{"date":{"order":"desc"}}],"query":{"bool":{"must":[{"query_string":{"query":"Datenschutz","fields":["title.*^5","abstract.*^3","meta.*^10","attachment.content","reference^3"],"default_operator":"AND","type":"cross_fields"}}],"filter":[{"range":{"date":{"gte":"2025-01-01","lte":"2025-06-30"}}}]}}}`
- **Auswahl:** die ersten 3 von 5 Treffern, aus 342709 Bytes Rohantwort
- **Groesse:** 136772 Bytes
- **SHA-256:** `bf497cd6c765ffb7a0285281f2d1adf14dc55cf8dcfbef415e6d647d70879449`

## `search_bger_1.json`

- **Werkzeuge:** `search_bger_decisions`
- **Schluessel:** `https://entscheidsuche.ch/_searchV2.php#7652eec8b69c`
- **Rumpf:** `{"size":5,"from":0,"track_total_hits":true,"sort":[{"date":{"order":"desc"}}],"query":{"bool":{"must":[{"query_string":{"query":"Persönlichkeitsschutz","fields":["title.*^5","abstract.*^3","meta.*^10","attachment.content","reference^3"],"default_operator":"AND","type":"cross_fields"}}],"filter":[{"bool":{"should":[{"prefix":{"hierarchy":"CH_BGer"}},{"prefix":{"hierarchy":"CH_BGE"}}],"minimum_should_match":1}},{"range":{"date":{"gte":"2025-01-01","lte":"2025-06-30"}}}]}}}`
- **Auswahl:** die ersten 3 von 5 Treffern, aus 112035 Bytes Rohantwort
- **Groesse:** 40809 Bytes
- **SHA-256:** `4bb771afad08b732af73e22f1f4d045aa90c28e49e86019dd909a5039497117c`

## `search_canton_1.json`

- **Werkzeuge:** `search_court_decisions`
- **Schluessel:** `https://entscheidsuche.ch/_searchV2.php#2b7725da8bae`
- **Rumpf:** `{"size":5,"from":0,"track_total_hits":true,"sort":[{"date":{"order":"desc"}}],"query":{"bool":{"must":[{"query_string":{"query":"Datenschutz","fields":["title.*^5","abstract.*^3","meta.*^10","attachment.content","reference^3"],"default_operator":"AND","type":"cross_fields"}}],"filter":[{"term":{"hierarchy":"ZH"}},{"range":{"date":{"gte":"2025-01-01","lte":"2025-06-30"}}}]}}}`
- **Auswahl:** die ersten 3 von 5 Treffern, aus 308535 Bytes Rohantwort
- **Groesse:** 253311 Bytes
- **SHA-256:** `98934dadde179100cf2b7295965130f31931837664853606fa46219c4705ef63`

## `search_law_1.json`

- **Werkzeuge:** `search_by_law_reference`
- **Schluessel:** `https://entscheidsuche.ch/_searchV2.php#6e5b2e91f8aa`
- **Rumpf:** `{"size":5,"from":0,"track_total_hits":true,"sort":[{"_score":{"order":"desc"}},{"date":{"order":"desc"}}],"query":{"bool":{"should":[{"query_string":{"query":"\"Art. 28 ZGB\"","fields":["title.*^5","abstract.*^3","meta.*^10","attachment.content","reference^3"],"default_operator":"AND","boost":10}},{"query_string":{"query":"28 ZGB","fields":["title.*^5","abstract.*^3","meta.*^10","attachment.content","reference^3"],"default_operator":"AND","type":"cross_fields","boost":3}},{"query_string":{"query`
- **Auswahl:** die ersten 3 von 5 Treffern, aus 288063 Bytes Rohantwort
- **Groesse:** 134988 Bytes
- **SHA-256:** `617f75880f0b054a32be51190585bdec8bb3d7f157fba3b9f79dd65ad2c85311`

## `statistics_1.json`

- **Werkzeuge:** `get_decision_statistics`
- **Schluessel:** `https://entscheidsuche.ch/_searchV2.php#d13b85db4e1a`
- **Rumpf:** `{"size":0,"aggs":{"by_canton":{"terms":{"field":"hierarchy.keyword","size":50}},"by_year":{"date_histogram":{"field":"date","calendar_interval":"year","order":{"_key":"desc"},"min_doc_count":1}}},"query":{"bool":{"filter":[{"range":{"date":{"gte":"2025-01-01","lte":"2025-12-31"}}}]}}}`
- **Auswahl:** ungekuerzt — der Server rechnet *in* dieser Antwort, ein Schnitt erfaende ein anderes Ergebnis
- **Groesse:** 584 Bytes
- **SHA-256:** `83329d2c20b6515353c2adb3e36e835e96a00b9e90ccdfc9c0450d6aa6b50eb9`

---

# `junit/` — aufgezeichnete pytest-Reports

Aufgezeichnet am **2026-08-16** mit **pytest 9.1.1**, dieselbe Version, die
`pip install -e ".[dev]"` liefert und die die CI fährt.

Diese Dateien belegen nicht eine Antwort von entscheidsuche.ch, sondern das
Ausgabeformat von pytest selbst — der Erzeuger, dessen Vertrag
`scripts/classify_live_run.py` liest. Sie stehen deshalb in einem eigenen
Ordner und ausserhalb des Schlüsselverzeichnisses; geprüft wird ihr Nachweis
in `tests/test_classify_live_run.py`.

**Warum überhaupt:** Die übrigen Tests der Einordnung schreiben ihr XML von
Hand. Handgeschriebene Fixtures kodieren die Annahme des Autors und können
sie nicht widerlegen — hiesse ein Zähler `error` statt `errors`, oder fehlte
die `<testsuites>`-Hülle, blieben alle grün und die Produktion läge falsch.
Aufgezeichnet ist deshalb je eine Form, die die Einordnung unterscheidet.

**Erzeugt** mit je einer Wegwerf-Testdatei und
`pytest <datei> --junitxml=<ziel>`; `null_tests.xml` zusätzlich mit
`-m "not live"` auf einen ausschliesslich mit `live` markierten Test, weil
genau so ein leerer Lauf entsteht.

Beobachtet und damit belegt: die Hülle `<testsuites name="pytest tests">`, die
Zähler `tests` / `failures` / `errors` / `skipped` als Attribute am
`<testsuite>`, und dass ein Setup-Fehler in `errors` landet, nicht in
`failures`.

## `junit/gruen.xml`

- **Lauf:** zwei bestandene Tests
- **Zähler:** tests=2, failures=0, errors=0, skipped=0 → `clear`
- **SHA-256:** `6a3006ef5a9206cf7085a781f2a26b97b9a0e105964046010f2c6425918e4f91`

## `junit/fehlschlag.xml`

- **Lauf:** ein bestandener, ein gefallener Test (`assert 1 == 2`)
- **Zähler:** tests=2, failures=1, errors=0, skipped=0 → `finding`
- **SHA-256:** `ce2c38408bef13426210f060151c4ff8861337b34260ae40060f05a3e85fde31`

## `junit/fehler.xml`

- **Lauf:** ein Test, dessen Fixture beim Setup wirft
- **Zähler:** tests=1, failures=0, errors=1, skipped=0 → `finding`
- **SHA-256:** `7001963b8479f5bbb03187e284518e974c6f19c8e624a194ace85a8ca2c95fe6`

## `junit/alle_uebersprungen.xml`

- **Lauf:** zwei Tests, beide per `skipif` übersprungen — die Form, die
  pytest bei einem fehlenden Secret erzeugt und mit Exit 0 quittiert
- **Zähler:** tests=2, failures=0, errors=0, skipped=2 → `unknown`
- **SHA-256:** `a307421002f5ce58da7aad92407c39f200371a885f41465d5a8ab1dd7782e798`

## `junit/null_tests.xml`

- **Lauf:** nichts eingesammelt (Marken-Filter greift auf alles)
- **Zähler:** tests=0 → `unknown`
- **SHA-256:** `834a748a49f5f0be090deb421081c7f8b83fddaa04f4ffd67525ff4f0e4adf4f`

# ADR 0002 — Offline-Fallback: Architektur und Quelle

**Status:** akzeptiert · **Datum:** 2026-07-19 · **Bezug:** Phase 3

## Kontext

entscheidsuche.ch ist die einzige Quelle des Servers, öffentlich, ohne Auth und
**ohne SLA**. Bot-Block, HTTP 5xx/429 oder ein Timeout machen den Server damit
vollständig unbenutzbar — nicht wegen eines Fehlers im Code, sondern weil die
Gegenseite gerade nicht mag. Gesucht war ein Notnagel für die Verfügbarkeit,
kein zweiter Suchindex.

Eine Live-Probe am 19.07.2026 hat die Kandidaten geprüft.

## Entscheidung

**Architektur C (Metadaten-only Offline-Fallback), geliefert per Lazy-Download
(Mechanik von Option A).**

1. **Immer Live-first.** entscheidsuche.ch bleibt im Erfolgsfall die einzige
   Quelle; das Live-Verhalten ist unverändert. Der Fallback greift nur bei einem
   Verfügbarkeitsfehler (Bot-Block, HTTP 5xx/429, Timeout, Connect-Error) oder
   wenn per `SWISS_COURTS_FORCE_DUMP=1` erzwungen.
2. **Quelle: der SCD-Dump** (Zenodo `10.5281/zenodo.14867950`, Version 2024-3,
   **CC BY 4.0**), der ~120-MB-CSV — nur Metadaten/Regesten, **kein Volltext**.
3. **Der Volltext-Parquet (375 MB) wurde verworfen** samt schwerer
   `pyarrow`-Abhängigkeit: Ein partieller Notnagel rechtfertigt den Footprint
   nicht, und Volltext würde eine Äquivalenz vorgaukeln, die es nicht gibt —
   der Dump deckt nur das Bundesgericht ab.
4. **Ein zweiter Kandidat wurde verworfen:** Zenodo `5529712`
   («SwissJudgmentPrediction») ist CC BY-**NC-SA** 4.0 — unvereinbar mit diesem
   MIT-Projekt.
5. **Kein zusätzliches Such-Tool.** Der Fallback ist ein Verhalten der
   bestehenden Tools; neu kam allein `get_fallback_status` dazu, für
   Transparenz.

## Konsequenzen

- Der CSV wird lokal gecacht (`platformdirs`) und via SQLite durchsucht; die
  Update-Erkennung nutzt die Zenodo-Versions-API (`conceptrecid` 7793043).
- Jede Antwort deklariert `source` (`live`/`dump`); Dump-Antworten ergänzen ein
  `coverage_note`. Die CC-BY-Attribution wird **im Tool-Output** mitgeliefert,
  nicht nur in der README.
- Eine kantonale oder Nicht-BGer-Anfrage im Dump-Modus liefert eine explizite
  «nicht abgedeckt»-Antwort — nie ein stilles leeres Resultat. Das ist die
  eigentliche Zusicherung: Der Server reduziert die Abdeckung nie
  stillschweigend.
- `get_court_decision` ist im Dump-Modus best-effort: SCD-Aktenzeichen
  (`docref`, z.B. `1C_517/2016`) unterscheiden sich von
  entscheidsuche-Signaturen, daher werden manche Lookups ehrlich als nicht
  auflösbar gemeldet.
- Ist weder Live noch Dump verfügbar, liefern die Tools einen klaren,
  handlungsleitenden Fehler (kein Crash, kein Stacktrace).
- Die Abdeckungsgrenzen des Dumps stehen in beiden READMEs unter «Known
  Limitations» / «Bekannte Einschränkungen» — dort, wo sie jemanden betreffen.

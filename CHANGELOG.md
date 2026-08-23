# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Behoben

- **Browser-Clients scheiterten am Preflight.** Spec `2026-07-28` routet eine
  Streamable-HTTP-Anfrage über `Mcp-Method`, `Mcp-Name` und
  `Mcp-Protocol-Version`; die CORS-Freigabeliste nannte keinen davon, dafür mit
  `Mcp-Session-Id` den Session-Header, der für sich genommen keine Anfrage
  routet. Ein Browser darf einen nicht safelisteten Header nicht senden, wenn
  der Server ihn nicht nennt: die Anfrage starb vor dem ersten MCP-Byte,
  während stdio und Python weiterliefen. Deshalb war nichts rot.

### Hinzugefügt

- **`build_http_app(settings)`**, herausgezogen aus `_run_http`, damit die
  CORS-Schicht prüfbar ist. Auth-Konfiguration, `transport_security` und
  `stateless_http` wandern unverändert mit; `_run_http` behält die
  Bind-Warnungen und ruft die neue Funktion auf.

- **Frischehinweise auf `tools/list`, `prompts/list` und `server/discover`**
  (SEP-2549, Spec `2026-07-28`): `ttlMs` 300000, `cacheScope` `public`. Das SDK
  setzt sonst «sofort veraltet, nie geteilt». `prompts/get` bleibt ohne Hinweis:
  das wäre eine Zusicherung über den Inhalt statt über das Verzeichnis.
  `resources/list` fehlt, weil dieser Server keine Ressourcen registriert.


Noch nichts seit 0.4.0.

- **`Mcp-Session-Id` ist weiterhin freigegeben — und das steht jetzt in einem
  Test statt in einem Satz.** Der Docstring von `tests/test_cors.py` nannte den
  Header die Spur einer Mechanik, die `2026-07-28` abgeschafft habe. Das stimmt
  nicht: `mcp` 2.x bedient beide Protokoll-Aeren, die Session gehoert zur
  Handshake-Aera, und der Server gibt den Header nicht ohne Grund auch in
  `expose_headers` frei.

  Nachgemessen statt aus Spec-Text geschlossen: `MCP_SESSION_ID_HEADER` steht
  unveraendert in `mcp/server/streamable_http.py`, und ein echter `initialize`
  durch den zusammengebauten ASGI-Stack bekommt eine Session-ID im
  Antwort-Header zurueck.

  `test_der_session_header_ist_weiterhin_freigegeben` haelt beides fest. Die
  Gegenprobe zeigt, dass es die Luecke wirklich gab: nimmt man den Header aus
  der Freigabeliste, faellt genau dieser eine Test, und die sieben bestehenden
  bleiben gruen.

## [0.4.0] - 2026-08-16

Minor, nicht Patch: Der Server läuft nach der Migration nicht mehr auf
`mcp` 1.x (`>=2.0.0,<3`, harte Untergrenze), und der Shard-Wächter macht aus
einem stillen Null-Treffer eine Fehlermeldung — beides ändert Verhalten, das
ein Aufrufer sieht.

### Behoben / Fixed

- **`search_bger_decisions` hat nie einen Entscheid gefunden.** Der
  Gerichtsfilter schickte `{"prefix": {"_id": "CH_BGer"}}`. Elasticsearch lehnt
  Prefix-Abfragen auf `_id` ab — «Can only use prefix queries on keyword, text
  and wildcard fields — not on [_id] which is of type [_id]». 47 von 53 Shards
  warfen eine `query_shard_exception`, und die Antwort kam trotzdem mit
  HTTP 200 und `hits.total = 0` zurück. Das Tool meldete daraufhin «Keine
  Bundesgerichtsentscheide gefunden» samt Suchtipps: ein Totalausfall in der
  Form eines sauberen Negativbefunds. Betroffen war jeder `court_level`-Filter,
  nicht nur das BGer-Tool.

  Gefiltert wird jetzt über `hierarchy` — ein Keyword-Array, das genau diese
  Präfixe trägt (`["CH", "CH_BGer", "CH_BGer_001"]`). Gemessen am 15.08.2026
  für «Datenschutz»: vorher 0 Treffer, nachher 557.

- **Der Kantonsfilter ebenso.** Er las `hierarchy.keyword`; dieses Unterfeld
  gibt es im Index nicht. Ein `term` auf ein unbekanntes Feld beantwortet
  Elasticsearch mit HTTP 200 und null Treffern — ohne Fehler, ohne Warnung,
  ohne Shard-Ausfall. Über `hierarchy`: «Datenschutz» + ZH von 0 auf 460.

  Beide Defekte waren in `tests/test_api_client.py` festgeschrieben:
  `assert any("hierarchy.keyword" in str(f) …)` prüfte den falschen Feldnamen,
  und `assert any("prefix" in str(f) or "should" in str(f) …)` war auf der
  kaputten Bauform genauso wahr.

### Hinzugefügt / Added

- **`_raise_if_shards_failed` (`UpstreamQueryError`).** Elasticsearch
  beantwortet eine Abfrage, die auf einzelnen Shards scheitert, mit HTTP 200 und
  der Trefferzahl der *übrigen* Shards. Genau so blieb der `_id`-Fehler
  unbemerkt. Ein Modell kann «dazu gibt es keine Rechtsprechung» nicht von «die
  Abfrage wurde nicht ausgeführt» unterscheiden — der Server muss es können. Die
  Meldung nennt die Zahl der gescheiterten Shards und den Grund und wird nicht
  als interner Fehler maskiert.

- **Aufgezeichnete Fixtures** in `tests/fixtures/` — acht echte Antworten, eine
  je Abfrageform. Ein Suchendpunkt, aber Volltext, Signatur-Lookup,
  Gesetzesreferenz, Kantonsfilter, Taxonomie, Datums-Sortierung und
  Jahres-Statistik gehen alle an dieselbe URL; der Elasticsearch-Rumpf gehört
  deshalb in den Schlüssel. Herkunft, Datum, Auswahlregel und SHA-256 je Datei
  in `tests/fixtures/PROVENANCE.md`, neu aufzeichnen mit
  `scripts/record_fixtures.py`, geladen über `tests/fixture_data.py`.
  Portfolio-Konvention, gleich wie in `meteoswiss-mcp` und
  `swiss-statistics-mcp`.

  Gekürzt ist nur die Zahl der Treffer in `hits.hits`; `hits.total` bleibt
  stehen (die Quelle meint damit den ganzen Index), und die Gerichtstaxonomie
  wie die Statistik-Aggregation bleiben ganz ungekürzt — der Server filtert und
  summiert *in* ihnen.

  Personendaten: Gerichte publizieren anonymisiert, entscheidsuche.ch spiegelt
  das. Die aufgezeichnete Entscheidung trägt 146 Anonymisierungsmarker
  (`A._`, `B._`) und keinen Klarnamen;
  `test_der_entscheid_ist_anonymisiert` hält das fest.

### Geändert / Changed
- **Migration auf die `mcp` 2.x Server-API.** Pin von `>=1.28.1,<2` auf
  `>=2.0.0,<3`. Die Untergrenze ist hart: 2.0.0 hat `mcp.server.fastmcp` ohne
  Kompatibilitätsschicht entfernt, dieser Code läuft also gar nicht mehr auf
  1.x. `FastMCP` → `MCPServer` (`mcp.server.mcpserver`).

- **`stateless_http` wieder verdrahtet (SCALE-002).** In 1.x war es ein
  `MCPServer`-Konstruktor-Argument, in 2.x ein Kwarg von
  `streamable_http_app()`. Beim Umbau war es ersatzlos verschwunden: die App
  baut weiter, fällt aber still auf Sticky-Sessions zurück — horizontale
  Skalierung wäre unbemerkt weg gewesen, weil kein Test den Zwischenzustand
  mehr lesen konnte. Geprüft wird jetzt der Kwarg selbst, über beide Werte
  (der Default ist `True`, ein hartkodiertes `True` wäre sonst durchgegangen),
  und zusätzlich, dass der Bind mitreist: 2.x schaltet bei loopback-artigem
  `host` automatisch eine `127.0.0.1:*`-Allow-List scharf, ein 0.0.0.0-Bind
  hätte damit jede echte Anfrage mit HTTP 421 abgewiesen.

- **`transport_security` als App-Kwarg.** `server.settings.transport_security = …`
  wirft in 2.x `ValueError`. Ohne den Kwarg fällt die App auf die
  SDK-Loopback-Policy zurück — und genau dann hält
  `test_right_host_wrong_port_is_rejected` nicht mehr.

- **Protokoll-Drift-Guard auf die richtige Ära gerichtet (ARCH-012).** 2.x
  bedient zwei Ären über denselben Server: der Legacy-`initialize`-Handshake
  deckelt bei 2025-11-25, die moderne Envelope-Ära erreicht 2026-07-28.
  `LATEST_PROTOCOL_VERSION` ist in 2.x ein Alias auf die *moderne* Version, der
  alte Guard verglich also gegen den falschen Wert und schlug fehl — nicht
  fälschlich, denn das SDK bringt wirklich eine neuere Revision mit.
  `PROTOCOL_VERSION` bleibt bei `2025-11-25`, weil es die Handshake-Ära
  beschreibt; geprüft wird jetzt gegen `LATEST_HANDSHAKE_VERSION` **und**
  `LATEST_MODERN_VERSION`, statt eine Ära stillschweigend zu übergehen.
  Nachgemessen statt aus Konstantennamen geschlossen: ein Legacy-`initialize`
  mit `2026-07-28` bekommt `2025-11-25` zurück, ältere Clients behalten ihre
  Revision.

- **`CallToolResult`-Feldnamen.** `mcp_types` hat auf snake_case umgestellt
  (`structuredContent` → `structured_content`). Die camelCase-Namen bleiben
  Pydantic-Aliase, das alte Kwarg funktionierte also weiter und die Suite blieb
  grün — nur mypy hätte es gesehen. Auf der Leitung steht unverändert
  `structuredContent`/`isError`, nachgeprüft am serialisierten Ergebnis.

  Geprüft: 129 passed / 4 deselected gegen die 1.x-Baseline von 120 — die
  Differenz sind genau die neun neuen Tests. `ruff check src/ tests/` und ein
  Install in einem frischen venv sind grün. Der neue Protokoll-Guard ist
  mutationsgetestet: bei verschobenem Pin fallen vier Tests.

### Behoben / Fixed
- **`mcp` auf `<2` gepinnt.** `mcp` 2.0.0 hat `mcp.server.fastmcp` entfernt; die
  bisherige Angabe `mcp[cli]>=1.28.1` war nach oben offen, sodass jede frische
  Installation die 2.x zog und der Server beim Import scheiterte
  (`ModuleNotFoundError: No module named 'mcp.server.fastmcp'`, 5 Test-Module
  bereits beim Sammeln). Betrifft jeden Neuaufbau seit dem 2.0.0-Release, nicht
  nur die CI. Der Pin entspricht dem Portfolio-Standard (vgl.
  `swiss-environment-mcp`, Audit ARCH-012).

### Geändert / Changed
- **User-Agent aus den Paket-Metadaten abgeleitet.** `__version__` und der
  `USER_AGENT` in `api_client.py` waren zwei handgepflegte Literale, die
  zufällig beide auf 0.3.0 standen — erzwungen war das nicht. Beim nächsten
  Versionsbump hätte entscheidsuche.ch einen veralteten Wert gesehen; genau so
  ist es in fünf Schwester-Servern des Portfolios passiert. Die Version kommt
  jetzt aus `importlib.metadata`. Abgesichert durch `tests/test_version.py`.

### Hinzugefügt / Added

- **`CLAUDE.md`.** Portfolio-weite Konventionen plus ein kurzer repo-eigener
  Teil: Default-Branch `master` statt `main`, die ruff-Version, die Gate-Liste
  und der Live-Aufruf. 78 Zeilen; eine lange Datei wird überlesen und ist dann
  schlechter als keine.

- **`scripts/check_gate_docs.py` — fünftes Gate.** Es hält die dokumentierten
  Befehle gegen die, die die Workflows wirklich fahren: `CLAUDE.md`, beide
  READMEs und beide CONTRIBUTING gegen `ci.yml` und `live.yml`. Als Gate zählt,
  wessen Befehlszeile die Marke `# gate` trägt — in `ci.yml` ein YAML-Kommentar,
  im Skript-Block von `live.yml` ein Shell-Kommentar; beides erreicht das
  Ausgeführte nicht, nachgemessen mit PyYAML und mit `${PIPESTATUS[0]}` in der
  Zeile darunter.

  Verglichen wird nach einer kleinen, dokumentierten Normalisierung (führende
  Env-Zuweisungen, `-v`, CI-Beiwerk wie `--junitxml` und Pipes fallen weg);
  alles andere zählt, in beide Richtungen. Der Abgleich meldet also auch einen
  Befehl, den die Doku nennt und der Workflow nicht fährt. Was übersprungen
  wurde, steht in jeder Ausgabe — auch im Erfolgsfall, damit eine Auswahl nicht
  wie Vollständigkeit aussieht.

  Grenze, bewusst in Kauf genommen: Ein neues Gate, das niemand markiert, wird
  nicht eingefordert. Es erscheint aber im Übersprungen-Bericht, und wer die
  Marke von einem *bestehenden* Gate entfernt, macht den Check trotzdem rot.

- **`docs/adr/0002-offline-fallback.md`.** Der Architektur-Entscheid zum
  Offline-Fallback — verworfene Kandidaten (der 375-MB-Volltext-Parquet, das
  NC-SA-lizenzierte Zenodo-`5529712`) und die Lizenzgründe. Das ist
  Entscheidungsgeschichte, keine Bedienungsanleitung; sie stand vorher in
  beiden READMEs.

- **Aufgezeichnete pytest-Reports** in `tests/fixtures/junit/` — je eine Form,
  die `classify_live_run.py` unterscheidet: grün, Fehlschlag, Setup-Fehler,
  alle übersprungen, null Tests. Aufgezeichnet am 16.08.2026 mit pytest 9.1.1,
  Herkunft und SHA-256 in `PROVENANCE.md`.

  Die dreizehn bestehenden Tests der Einordnung schreiben ihr XML von Hand und
  belegen damit nur, dass sie zur Annahme ihres Autors passt. Hiesse ein Zähler
  `error` statt `errors`, blieben alle grün, während der geplante Lauf
  danebengreift — und diese Einordnung entscheidet, ob ein Issue aufgeht oder
  zugeht. Nachgewiesen an einer simulierten Format-Drift: Sie bringt nur den
  aufgezeichneten Test zu Fall, die handgeschriebenen bleiben grün.

### Behoben / Fixed

- **Die dokumentierte Gate-Liste war unvollständig.** Die CI lintet
  `src/ tests/ scripts/`, README, README.de und beide CONTRIBUTING nannten
  `src/ tests/`; `ruff format --check` und `check_version_sync.py` fehlten ganz.
  Wer die Doku kopierte, fuhr das Gate unvollständig und sah die Differenz erst
  rot in der CI — an Code, den er nicht angefasst hatte. Alle fünf Dateien
  nennen jetzt alle fünf Gates, und `check_gate_docs.py` hält sie dort.

- **ruff war nur in der CI gepinnt.** `ci.yml` installierte `ruff==0.16.1`, die
  `dev`-Extra sagte `ruff>=0.15.15` — eine Untergrenze. `pip install -e ".[dev]"`,
  der Befehl aus CONTRIBUTING, lieferte damit die jeweils neueste Version, und
  eine andere Version meldet Abweichungen an Code, den niemand angefasst hat.
  Der Pin steht jetzt in `pyproject.toml`, und nur dort; der separate
  `pip install`-Schritt in `ci.yml` ist entfallen, weil zwei Pins, die
  übereinstimmen müssen, die Drift-Quelle sind und nicht ihre Absicherung.

### Geändert / Changed

- **`CLAUDE.md` und beide READMEs gekürzt** — 88 → 78, 464 → 393 und 413 → 379
  Zeilen. Dasselbe Prinzip überall: die Anweisung bleibt, die Begründung zieht
  dorthin, wo man sie sucht. Der Offline-Fallback stand zweimal in derselben
  README (unter *Architecture* und unter *Known Limitations*, beide Male mit
  Gerichtsumfang, Zeitraum und «kein Volltext») und ist in den Einschränkungen
  zusammengelegt; der Verzeichnisbaum unter *Project Structure* ist weg, weil er
  mit jedem Modul veraltet und wiederholt, was GitHub ohnehin zeigt; die Notiz,
  warum die 8 Tools in `server.py` liegen, steht jetzt in beiden CONTRIBUTING,
  bei den Leuten, die sie angeht.

## [0.3.1] - 2026-08-02

### Fixed

- **`structlog` carried no upper bound, and the index already serves a major past
  the floor.** The declared range was `structlog>=25.5.0`; PyPI has been serving
  `26.1.0`. The artefact does not change — the resolver's answer to the next
  fresh install does, and that is exactly how `swiss-energy-mcp` 0.3.3 became
  uninstallable when `mcp` 2.0.0 removed the module it imported.

  Now `structlog>=25.5.0,<27`. The bound is measured rather than guessed: this package
  installs and imports against `structlog 26.1.0` today, so the cap admits what
  demonstrably works and stops only the next, unknown major.

A dependency range only reaches users through a new release, hence the
version bump. No code changed.

## [0.3.0]

### Added

- **Offline fallback via the SCD Zenodo dump.** When entscheidsuche.ch is
  unreachable (Imunify360 bot-block, HTTP 5xx/429, timeout, connect error), the
  search-style tools now fall back to the **Swiss Federal Supreme Court Dataset
  (SCD)** (Zenodo `10.5281/zenodo.14867950`, Version 2024-3, CC BY 4.0). The
  ~120 MB CSV (metadata/regesten, **no full text**) is downloaded lazily into a
  `platformdirs` cache on first need and searched locally via SQLite (`fallback`
  module, fully separate from the live client).
- **Provenance on every response.** All response models now carry
  `source: Literal["live","dump"]`; dump responses additionally carry a
  `coverage_note`. The former `source` field (data-provider name) was renamed to
  `dataset`, and `attribution` was added (CC-BY citation shipped in the tool
  output, not just the README).
- **New tool `get_fallback_status`** (`readOnlyHint`) for transparency over the
  offline cache state, dataset version, coverage, and pre-warming. Optional
  `check_updates` queries the Zenodo versions API. Tool budget: 7 → 8.
- Configuration via env: `SWISS_COURTS_FORCE_DUMP=1` (force the dump path, e.g.
  for pre-warming/tests), `SWISS_COURTS_FALLBACK_ENABLED=0` (disable the
  fallback), `SWISS_COURTS_CACHE_DIR`, `SWISS_COURTS_DUMP_RECORD`.

### Known findings (from the Phase 1 live probe, 2026-07-19)

- The offline fallback is **partial, not equivalent**: SCD covers only the
  Federal Supreme Court (BGer/BGE), 2007–2024, ~16 % of what entscheidsuche.ch
  indexes. Cantonal / BVGer / BStGer queries in dump mode return an explicit
  "not covered" answer, never a silent empty result.
- The second candidate dataset (Zenodo `5529712`, "SwissJudgmentPrediction")
  was **rejected**: its licence is CC BY-**NC-SA** 4.0 (NonCommercial +
  ShareAlike), incompatible with this MIT project.
- SCD case identifiers (`docref`, e.g. `1C_517/2016`) differ from
  entscheidsuche signatures (`CH_BGer_005_…`); `get_court_decision` in dump mode
  is therefore best-effort and honest about non-resolvable lookups.

### Fixed

- Full-text search returned no results (HTTP 200 but `total == 0`) for ordinary
  queries such as "Datenschutz". The query is now aligned with the official
  `entscheidsuche` client: a `query_string` over the explicit, boosted fields
  `title.*^5`, `abstract.*^3`, `meta.*^10`, `attachment.content`, `reference^3`
  with `default_operator: "AND"` and `type: "cross_fields"`. The real index
  uses lowercase, multi-language fields (`title`/`abstract`/`meta` keyed
  `de`/`fr`/`it`) and stores the judgment full text under `attachment.content`;
  neither relying on the `default_field` nor the earlier `simple_query_string`
  field guesses (`title.de`, `lenient: true`) matched anything. Affects
  `build_search_body` and `build_law_reference_body`.
- Switched the search endpoint from the legacy `_search.php` to `_searchV2.php`,
  the current endpoint used by the official search frontend (targets the
  `entscheidsuche.v2-*` index). Search bodies now also set
  `track_total_hits: true` for accurate hit counts.
- Detect the Imunify360 bot-protection response and raise `UpstreamBlockedError`
  instead of silently returning zero hits. entscheidsuche.ch sits behind
  Imunify360, which answers automated / datacenter IPs with `HTTP 200` and a
  body like `{"message": "Access denied by Imunify360 bot-protection ..."}`
  (no `hits`). `search_decisions` now surfaces this as a clear error
  ("blocked by bot-protection; the IP must be whitelisted") via `handle_error`,
  so a blocked client no longer sees an empty result set with no explanation.

### Tests

- The `live` `test_live_search` now **skips** (instead of failing) when the
  request is blocked by Imunify360 bot-protection — an environmental condition
  (the CI runner's IP is not whitelisted), not a regression. This was the true
  cause of the long-standing intermittent `total == 0` failures (~25–30 % of
  daily runs, independent of query form or endpoint). A genuinely empty ES
  response still fails the test.

## [0.2.3] - 2026-06-07

### Added

- Declared `mcp-name` (`io.github.malkreide/swiss-courts-mcp`) in `pyproject.toml`
  and `README.md` to establish PyPI/MCP Registry ownership.

### Fixed

- Full-text search returned no results (HTTP 200 but `total == 0`) because
  `simple_query_string` queried only the index's `default_field`, which does not
  cover the ingest-attachment full text. Searches now target the relevant fields
  explicitly (`attachment.content`, `title.*`, `abstract.*`, `reference`) with
  `lenient` enabled. Affects `build_search_body` and `build_law_reference_body`.

## [0.2.0] - 2026-05-29

> **Audit verification:** production-ready ✅ — mcp-audit skill `v1.0.0`,
> 36 pass · 0 fail · 0 partial. Run `2026-05-29T191910-Z-swiss-courts-mcp`.

### Security

- HTTP transport now supports bearer-token authentication via the SDK-native
  `TokenVerifier` (JWT, identity from validated `sub` claim; HS256 + RS256/JWKS).
  See `docs/adr/0001-http-auth.md`. (SEC-009)
- Safe default bind host `127.0.0.1`; `0.0.0.0` requires explicit opt-in and logs
  a warning otherwise. (SEC-016)
- Egress allow-list (`entscheidsuche.ch` only, HTTPS-enforced) checked before
  every outbound request; see `docs/network-egress.md`. (SEC-021/SEC-004/SEC-005)
- Error masking: internal exceptions are logged server-side only; clients receive
  friendly messages. (OBS-002)
- Added `.gitignore` (`.env*` excluded), `.env.example`, and a Gitleaks CI
  workflow. (ARCH-005)

### Added

- CORS configuration for the HTTP transport exposing `Mcp-Session-Id`. (SDK-004)
- Stateless HTTP mode for horizontal scaling without sticky sessions. (SCALE-002)
- Structured logging (structlog) on stderr. (OBS-003)
- Context injection with progress reporting in search tools. (SDK-003)
- Machine-readable `match_type` and source/license provenance in responses.
  (ARCH-003/CH-004)
- All tools now emit `structuredContent` (a consistent response envelope with
  `source`, `license`, `match_type`, `count`, `total`, `results`/provenance)
  alongside the curated Markdown, via `CallToolResult` + `structured_output=False`.
  (SDK-002)
- `rechtsrecherche` prompt as a second MCP primitive. (ARCH-008)
- Hardened `Dockerfile` (non-root UID 10001), Dependabot, nightly live-test
  workflow, and `ROADMAP.md` with the explicit read-only Phase 1 declaration.
  (SEC-007/ARCH-012/OPS-001/OPS-003)
- `docs/`: network egress, secret management, and ADR 0001.

### Changed

- Tools now raise `ToolError` for upstream failures so errors surface as
  `isError` results instead of plain text. (OBS-001)
- Single shared `httpx.AsyncClient` via a FastMCP lifespan instead of one client
  per tool call. (SDK-001)
- Pinned MCP protocol version `2025-11-25` with a drift-detection test. (ARCH-012)
- README/README.de expanded (protocol version, phase, annotations, security);
  CONTRIBUTING is now bilingual. (OPS-002)

### Notes

- MCP protocol version: **2025-11-25**. No phase transition — server remains
  Phase 1 (read-only).

## [0.1.0] - 2026-04-12

### Added

- Full-text search across all Swiss court decisions (`search_court_decisions`)
- Single decision retrieval by signature (`get_court_decision`)
- Dedicated Federal Supreme Court search with chamber filter (`search_bger_decisions`)
- Multi-stage law reference search with regex parser and boost scoring (`search_by_law_reference`)
- Court taxonomy listing from Facetten_alle.json (`list_courts`)
- Recent decisions feed with canton and court level filters (`get_recent_decisions`)
- Decision statistics with Elasticsearch aggregations (`get_decision_statistics`)
- Pydantic input validation with all 26 Swiss cantons
- Trilingual support (German, French, Italian)
- Dual transport: stdio (local) and streamable-http (cloud)
- 55 unit and live API tests
- PyPI publication via GitHub Actions trusted publishing

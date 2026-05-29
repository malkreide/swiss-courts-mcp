# Roadmap — swiss-courts-mcp

Der Server folgt der Phasenarchitektur **Read-only First → Write → Multi-Agent**
(OPS-003). Die aktuelle Phase ist im README deklariert.

## Phase 1 — Read-only (aktuell)

Alle Tools sind read-only, idempotent und nicht-destruktiv
(`readOnlyHint: true`). Keine schreibenden Operationen, keine Personendaten.

- [x] Volltext-, BGer-, Gesetzesreferenz-Suche
- [x] Einzelabruf, Gerichtsliste, Statistik, neueste Entscheide
- [x] Pydantic-Input-Validation, Egress-Allow-List, Error-Masking
- [x] Dual-Transport (stdio + streamable-http) mit Bearer-Auth im HTTP-Modus
- [ ] Strukturierter Response-Envelope auch als `structuredContent` ausliefern
- [ ] Resource-Primitiv für die Gerichts-Taxonomie

## Phase 2 — Write (geplant, noch nicht freigegeben)

Voraussetzungen für den Übergang (verbindlich):

- [ ] Vollständiger Re-Audit (mcp-audit) ohne offene `critical`/`high`-Findings
- [ ] ISDS / DSG-Verarbeitungsverzeichnis, falls Personendaten verarbeitet werden
- [ ] Human-in-the-Loop (`ctx.elicit`) für jede schreibende Operation
- [ ] Lethal-Trifecta-Neubewertung (SEC-019)

## Phase 3 — Multi-Agent (perspektivisch)

- [ ] Semantic Layer / Identity-Resolution
- [ ] GL- und Datenschutzbeauftragte:r-Sign-off

Phasenübergänge werden im `CHANGELOG.md` dokumentiert.

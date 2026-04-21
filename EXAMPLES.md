# Use Cases & Examples — swiss-courts-mcp

Real-world queries by audience. Indicate per example whether an API key is required.

### 🏫 Bildung & Schule
Lehrpersonen, Schulbehörden, Fachreferent:innen

**Rechtsprechung zum Nachteilsausgleich an Prüfungen**
«Welche Gerichtsentscheide gibt es im Kanton Zürich zum Thema Nachteilsausgleich bei Prüfungen?»
→ `search_court_decisions(query="Nachteilsausgleich Prüfung", canton="ZH")`
Warum nützlich: Erlaubt Schulleitungen und Behörden, ihre Bewilligungspraxis an der aktuellen kantonalen Rechtsprechung auszurichten.

**Entlassung von Lehrpersonen**
«Gibt es aktuelle Bundesgerichtsentscheide zur fristlosen Kündigung von Lehrpersonen?»
→ `search_bger_decisions(query="fristlose Kündigung Lehrperson", date_from="2020-01-01")`
Warum nützlich: Zeigt Schulpflegen und Rechtsdiensten auf, wie das höchste Gericht Personalfragen und arbeitsrechtliche Konflikte im Bildungsbereich beurteilt.

### 👨‍👩‍👧 Eltern & Schulgemeinde
Elternräte, interessierte Erziehungsberechtigte

**Zumutbarkeit des Schulwegs**
«Ab welcher Distanz oder bei welchen Gefahren gilt ein Schulweg rechtlich als unzumutbar?»
→ `search_court_decisions(query="Zumutbarkeit Schulweg")`
Warum nützlich: Hilft Eltern und Elternräten, objektive rechtliche Massstäbe für Diskussionen um Schulbusse, sichere Schulwege oder Gefahrenstellen zu finden.

**Sonderpädagogische Massnahmen**
«Wie entscheiden Gerichte im Kanton Bern bei Streitigkeiten um die Zuteilung von Sonderschulung?»
→ `search_court_decisions(query="Sonderschulung Zuteilung", canton="BE")`
Warum nützlich: Bietet Eltern Orientierung, wie Gerichte bei Uneinigkeit über Fördermassnahmen für Kinder mit besonderen Bedürfnissen typischerweise urteilen.

### 🗳️ Bevölkerung & öffentliches Interesse
Allgemeine Öffentlichkeit, politisch und gesellschaftlich Interessierte

**Baueinsprachen und Lärmschutz**
«Wie haben die Gerichte im Kanton Aargau kürzlich bei Baueinsprachen wegen Lärmschutz entschieden?»
→ `search_court_decisions(query="Baueinsprache Lärmschutz", canton="AG", date_from="2022-01-01")`
Warum nützlich: Ermöglicht es Anwohnenden und Bauherrschaften, die Fallstricke und Erfolgsaussichten eigener baurechtlicher Verfahren besser einzuschätzen.

**Praxis zum Strassenverkehrsgesetz**
«Gibt es aktuelle Bundesgerichtsurteile zum Entzug des Führerausweises wegen Geschwindigkeitsüberschreitung?»
→ `search_by_law_reference(law_reference="Art. 16c SVG")`
Warum nützlich: Macht die konkrete Anwendung von Strassenverkehrsregeln und die behördliche Massnahmenpraxis im Alltag transparent und nachvollziehbar.

### 🤖 KI-Interessierte & Entwickler:innen
MCP-Enthusiast:innen, Forscher:innen, Prompt Engineers, öffentliche Verwaltung

**Gesetz und Praxis kombinieren (Multi-Server)**
«Schlage den Artikel zum Auskunftsrecht im Datenschutzgesetz nach und suche dann nach aktueller Rechtsprechung dazu.»
→ `fedlex_search_laws(query="Auskunftsrecht DSG")` (via [fedlex-mcp](https://github.com/malkreide/fedlex-mcp))
→ `search_by_law_reference(law_reference="Art. 25 DSG")`
Warum nützlich: Demonstriert die Stärke von kombinierten MCP-Servern. Zuerst wird der normative Gesetzestext aus dem Bundesrecht geholt, danach die konkrete Fallpraxis dazu.

**Statistische Analyse von Gerichtsentscheiden**
«Zeige mir die Verteilung der veröffentlichten Gerichtsentscheide im Kanton Zürich für das Jahr 2023.»
→ `get_decision_statistics(canton="ZH", year=2023)`
Warum nützlich: Veranschaulicht Entwicklern und Forschenden, wie aggregierte Metadaten für Trendanalysen, Legal Tech Dashboards oder juristische Forschung genutzt werden können.

### 🔧 Technische Referenz: Tool-Auswahl nach Anwendungsfall

| Ich möchte… | Tool(s) | Auth nötig? |
|-------------|---------|-------------|
| Urteile zu einem bestimmten Thema finden | `search_court_decisions` | Nein |
| Gezielt in Bundesgerichtsentscheiden suchen | `search_bger_decisions` | Nein |
| Rechtsprechung zu einem Gesetzesartikel finden | `search_by_law_reference` | Nein |
| Die aktuellsten Entscheide aus meinem Kanton sehen | `get_recent_decisions` | Nein |
| Einen bestimmten Entscheid im Detail lesen | `get_court_decision` | Nein |
| Analysieren, wie viele Fälle ein Gericht publiziert hat | `get_decision_statistics`, `list_courts` | Nein |

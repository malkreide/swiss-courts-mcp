# Use Cases & Examples — swiss-courts-mcp

Real-world queries by audience. Alle hier gezeigten Abfragen können direkt ohne API-Key ausgeführt werden.

### 🏫 Bildung & Schule
Lehrpersonen, Schulbehörden, Fachreferent:innen

#### Fallbeispiele aus dem Schulalltag und Aufsichtspflicht
«Gibt es aktuelle Bundesgerichtsentscheide zum Thema Schulweg und Haftung der Lehrperson?»

→ `search_court_decisions(query="Schulweg Haftung Lehrperson", court_level="bundesgericht", limit=5)`
Auth: Kein API-Key erforderlich.

Warum nützlich: Erlaubt Schulleitungen und Lehrpersonen, sich unkompliziert über die aktuelle Rechtslage zur Aufsichtspflicht auf dem Schulweg zu informieren und interne Weisungen rechtssicher zu gestalten.

#### Rechte von Schülerinnen und Schülern
«Finde Entscheide zur Dispensation vom Schwimmunterricht aus religiösen Gründen.»

→ `search_court_decisions(query="Schwimmunterricht Dispensation Religion", limit=10)`
Auth: Kein API-Key erforderlich.

Warum nützlich: Hilft Schulbehörden bei der objektiven Beurteilung von heiklen Dispensationsgesuchen auf Basis bestehender kantonaler und eidgenössischer Präjudizien.

### 👨‍👩‍👧 Eltern & Schulgemeinde
Elternräte, interessierte Erziehungsberechtigte

#### Schulweg und Sicherheit
«Wie entscheiden Gerichte über die Zumutbarkeit des Schulwegs für Primarschüler im Kanton Zürich?»

→ `search_court_decisions(query="Zumutbarkeit Schulweg Primarschule", canton="ZH")`
Auth: Kein API-Key erforderlich.

Warum nützlich: Bietet Elternräten konkrete rechtliche Anhaltspunkte und Argumentationshilfen, wenn sie mit der Gemeinde über Schulbusse oder gefährliche Schulwege diskutieren.

#### Fördermassnahmen und Sonderschulung
«Welche Urteile gibt es bezüglich Kostenübernahme für Sonderschulung oder private Förderung?»

→ `search_court_decisions(query="Sonderschulung Kostenübernahme", limit=10)`
Auth: Kein API-Key erforderlich.

Warum nützlich: Unterstützt Eltern von Kindern mit besonderen Bedürfnissen dabei, ihre eigenen Rechte gegenüber der Schulgemeinde besser zu verstehen.

### 🗳️ Bevölkerung & öffentliches Interesse
Allgemeine Öffentlichkeit, politisch und gesellschaftlich Interessierte

#### Mietrecht und Kündigung
«Suche nach aktuellen Entscheiden zum Thema Eigenbedarfskündigung im Mietrecht.»

→ `search_court_decisions(query="\"Eigenbedarf\" Kündigung Mietrecht", limit=10)`
Auth: Kein API-Key erforderlich.

Warum nützlich: Ermöglicht Mieterinnen und Mietern, sich bei Erhalt einer Kündigung ein erstes Bild über die Erfolgschancen einer Anfechtung bei der Schlichtungsbehörde zu machen.

#### Datenschutz und Auskunftsrecht
«Ich möchte Urteile lesen, die den Artikel 25 des Datenschutzgesetzes (Auskunftsrecht) behandeln.»

→ `search_by_law_reference(law_reference="Art. 25 DSG", limit=10)`
Auth: Kein API-Key erforderlich.

Warum nützlich: Stärkt die Zivilgesellschaft, indem Bürgerinnen und Bürger konkret nachvollziehen können, wie ihre Datenschutzrechte in der Praxis rechtlich durchgesetzt werden.

#### Neueste Rechtsprechung im eigenen Kanton
«Zeige mir die neuesten Urteile des Kantonsgerichts Bern.»

→ `get_recent_decisions(canton="BE", limit=5)`
Auth: Kein API-Key erforderlich.

Warum nützlich: Erlaubt lokal interessierten Bürgern und Journalisten, die aktuelle juristische Entwicklung im eigenen Kanton niederschwellig zu verfolgen.

### 🤖 KI-Interessierte & Entwickler:innen
MCP-Enthusiast:innen, Forscher:innen, Prompt Engineers, öffentliche Verwaltung

#### Statistik zur Rechtsprechung extrahieren
«Wie viele Entscheide aus dem Kanton Zürich aus dem Jahr 2023 sind im System erfasst?»

→ `get_decision_statistics(canton="ZH", year=2023)`
Auth: Kein API-Key erforderlich.

Warum nützlich: Ermöglicht Datenjournalisten und Legal-Tech-Entwicklern, den Datenkorpus auf Vollständigkeit zu prüfen und quantitative Analysen zur Gerichtstätigkeit zu generieren.

#### Synergie: Gesetzestext und Rechtsprechung (Multi-Server)
«Suche das Gleichstellungsgesetz mit fedlex-mcp und finde anschliessend mit swiss-courts-mcp die neuesten Bundesgerichtsentscheide zu Lohndiskriminierung.»

→ `fedlex_search_laws(query="Gleichstellungsgesetz")` *(via [fedlex-mcp](https://github.com/malkreide/fedlex-mcp))*
→ `search_bger_decisions(query="Lohndiskriminierung Gleichstellungsgesetz", date_from="2020-01-01", limit=10)`
Auth: Kein API-Key erforderlich.

Warum nützlich: Demonstriert die Leistungsfähigkeit von Agentic Legal Research, indem formelles Recht und materielle gerichtliche Praxis über zwei spezialisierte MCP-Server nahtlos kombiniert werden.

### 🔧 Technische Referenz: Tool-Auswahl nach Anwendungsfall

| Ich möchte… | Tool(s) | Auth nötig? |
|-------------|---------|-------------|
| …nach beliebigen Begriffen in Urteilen suchen | `search_court_decisions` | Nein |
| …gezielt nur Bundesgerichtsentscheide durchsuchen | `search_bger_decisions` | Nein |
| …die Praxis zu einem bestimmten Gesetzesartikel finden | `search_by_law_reference` | Nein |
| …die neuesten publizierten Urteile in meinem Kanton sehen | `get_recent_decisions` | Nein |
| …wissen, wie viele Entscheide ein Kanton erfasst hat | `get_decision_statistics` | Nein |
| …einen spezifischen Entscheid im Volltext / als Metadaten lesen | `get_court_decision` | Nein |
| …alle erfassten Gerichte eines Kantons auflisten | `list_courts` | Nein |

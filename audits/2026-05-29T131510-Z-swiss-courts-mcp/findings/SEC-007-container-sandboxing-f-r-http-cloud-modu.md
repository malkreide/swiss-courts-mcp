## Finding: SEC-007 — Container-Sandboxing für HTTP-/Cloud-Modus

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `SEC-007` |
| **PDF-Reference** | Sec 4 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Reiner stdio/Python-Server ohne externe Prozess-/Datei-Privilegien

### Expected Behavior

Dockerfile mit non-root USER (>=10000), readOnlyRootFilesystem, cap drop ALL, seccomp RuntimeDefault — sofern HTTP/Cloud deployt wird.

### Evidence / Gaps

- Kein Dockerfile/Container-Hardening vorhanden, obwohl HTTP-/Cloud-Modus existiert (kein non-root USER, kein readOnlyRootFilesystem, keine cap drop)
- Vor einem Cloud-Deployment des HTTP-Modus muss Sandboxing nachgezogen werden

### Risk Description

Ohne Container-Hardening würde ein Cloud-Deployment des HTTP-Modus als root mit vollem Filesystem-Zugriff laufen — unnötige Angriffsfläche bei Kompromittierung.

### Remediation

Dockerfile mit non-root USER (>=10000), readOnlyRootFilesystem, cap drop ALL, seccomp RuntimeDefault — sofern HTTP/Cloud deployt wird.

### Effort Estimate

M

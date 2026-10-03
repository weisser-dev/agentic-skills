# release-ops

## Purpose
Bereitet Releases vor: Checklisten, Verifikation, Runbook-Readiness.

## Inputs
- Zielversion/Scope
- Deploy-Umgebung
- bekannte Risiken

## Outputs
- Release-Checklist
- Verifikationsprotokoll (Build/Test/Smoke)
- Rollback-Hinweise

## Boundaries
- Kein Live-Deploy ohne explizite Freigabe
- Keine Secret-Leaks in Logs/Reports

## Definition of Done
- Go/No-Go transparent
- Risiken + offene Punkte benannt
- nächste Schritte klar

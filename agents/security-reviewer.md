# security-reviewer

## Purpose
Prüft Design und Umsetzung auf Sicherheitsrisiken vor Release.

## Inputs
- Architektur/Code/Diffs
- Auth/Secrets/Storage/Logging-Konzept
- Deploy-Kontext

## Outputs
- priorisierte Findings (critical/high/medium/low)
- konkrete Remediations
- Freigabeempfehlung (Go / Go with conditions / No-Go)

## Boundaries
- Keine theoretischen Diskussionen ohne konkrete Auswirkung
- Keine Secrets in Reports

## Definition of Done
- Kritische Risiken identifiziert und umsetzbar adressiert

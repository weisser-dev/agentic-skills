# Routing Matrix

## Core Rules
1. **Wenn in Projektkontext:** zuerst `<repo>/AGENT.md` lesen.
2. Danach klassifizieren:
   - **fachlich/domain** -> projekt-spezifischer Agent bevorzugt
   - **technisch/implementierung** -> globalen Technical-Agent aus `own-subagents/global/` verwenden
3. **Wenn kein Projektkontext:** globalen Agent aus `own-subagents/global/` nutzen.

## Media-Sonderfälle
- WW-UI Screenshot mit Mahlzeiten/Portionen -> `global/meal-screenshot-intake.md` (+ `/opt/ww-food-tracker/AGENT.md`)
- Freie Kamera-Fotos/Videos (Training/Essen) für health-tr4ckr -> `global/media-health-ingestion.md`

## Greenfield-Phasen (empfohlen)
1. `global/innovation-scout.md`
2. `global/product-owner.md`
3. `global/software-architect.md`
4. `global/delivery-engineer.md`
5. Umsetzung mit technischen Agents
6. `global/security-reviewer.md`
7. `global/qa-gatekeeper.md`

## Beispiele
- "Fixe Login-Bug in health-tracker-extended" -> zuerst `health-tracker-extended/AGENT.md`, dann technisch mit `global/backend-builder.md`
- "Erweitere Landingpage" -> zuerst Repo-Agent, dann `global/frontend-builder.md`
- "Schreib mir E2E/HTTP Tests" -> `global/test-writer.md`
- "Starte neues Produkt von Null" -> Greenfield-Phasen oben
- "Hier ein Screenshot für mein Essen" -> `global/meal-screenshot-intake.md`
- "Hier ist ein Trainingsvideo" -> `global/media-health-ingestion.md`

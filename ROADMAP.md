
## `ROADMAP.md`

```markdown
# EcoRiskAI Roadmap

## Demo MVP

Goal:
Create a working prototype that can be shown during an in-person pitch.

Must have:
- Master dataset from Earth Engine
- Python ML pipeline
- Prediction CSV
- Simple dashboard
- Risk map
- Explanation panel
- Methodology page

## Version 1.1

After demo:
- Improve validation
- Add feature importance
- Add SHAP explanations
- Add year-over-year comparison
- Add downloadable report

## Version 1.2

Improve usefulness:
- Better region boundaries
- Add watersheds
- Add protected areas
- Add road distance
- Add drought severity

## Version 2

Bigger product:
- Ecosystem risk score beyond forest loss
- Multi-region support
- Better dashboard
- User-uploaded AOI
- Export PDF reports

## Future Vision

Potential future:
- Agentic conservation assistant
- Live Earth Engine refresh
- Cloud deployment
- Collaboration with conservation experts

## TNC feedback integration (Kirk Klausmeyer, Jul 2026)

Status of the action items from the check-in. See `docs/positioning.md` and
`earth_engine/README.md` for detail.

**Phase 0 — Follow-ups (non-code, owner: Yuv)**
- [ ] Host the demo and send Kirk the link — see `DEPLOY.md`
- [ ] Send Kirk the raw Earth Engine CSVs
- [ ] Accept the intro to Charlotte (forest team)
- [x] Draft follow-up email — `docs/followups/kirk_email_draft.md`

**Phase 1 — Fire scope + honest limitations (done)**
- [x] Fire-scoped target (exclude non-fire loss) — `src/dataset/labels.py`
- [x] Methodology/limitations rewritten in the dashboard
- [x] Annual cadence documented — `config.yaml` `labeling.update_cadence`

**Phase 2 — Temporal integrity + leakage fix (done)**
- [x] Removed concurrent `burned_this_month` from model features (leakage)
- [x] Date-anchored labels via Hansen `lossyear`
- [x] "Month before" lag machinery built, gated on config (needs denser data)

**Phase 3 — Sample → full landscape (in-repo done; one GEE run remaining)**
- [x] Tiled extraction script — `earth_engine/extract_full_grid.js`
- [x] Full-landscape scorer — `src/models/predict_landscape.py`
- [x] Map renders a filled per-cell risk surface, auto-uses wall-to-wall output
- [ ] Run the dense extraction on the Earth Engine account (owner: Yuv)

**Phase 4 — Prioritization signals (done as decision support)**
- [x] Time since last detected burn (overdue flag)
- [x] Controllability / natural firebreaks from neighbor burn history
- [x] Land-ownership hook (optional reference file)
- [ ] Swap proxies for dedicated fire-perimeter + ownership layers

**Phase 5 — Positioning (done)**
- [x] Positioning analysis vs. USGS Fire Danger Forecast and peers —
      `docs/positioning.md`
- [ ] Add screenshots and a one-paragraph "why EcoRiskAI" statement
- Field validation workflow
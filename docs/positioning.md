# EcoRiskAI — positioning vs. existing fire tools

Kirk's advice in the July 2026 check-in: look at the fire tools that already
exist, understand *why* people do or don't use them, and be clear about where a
prototype like EcoRiskAI fits. This doc is that starting analysis. Treat the
per-tool specifics as a research scaffold to confirm, not settled fact.

## The landscape (established tools)

| Tool | Owner | What it does | Update cadence |
|------|-------|--------------|----------------|
| **Fire Danger Forecast** (Wildland Fire Potential Index, fire spread probability, large-fire probability) | USGS | National, near-real-time fire-danger surfaces driven by current weather and fuels | Daily |
| **Wildfire Risk to Communities** | USDA Forest Service | National wildfire likelihood, intensity, and risk-to-homes layers for planning | Periodic (annual-ish) |
| **LANDFIRE** | USGS / USFS | Foundational fuels, vegetation, and disturbance layers many other tools build on | Periodic |
| **Fire Hazard Severity Zones (FHSZ)** | CAL FIRE | Regulatory hazard zoning for California | Infrequent (regulatory) |
| **Research/operational fire spread models** (e.g. WIFIRE, Technosylva-class) | Universities / vendors | Physics-based fire behavior and spread simulation | Real-time / on-demand |

*Confirm the exact product names, layers, and cadences before quoting them in a
pitch — the USGS Fire Danger Forecast interactive UI is the first one to check
(Kirk pointed to it directly and said it updates daily).*

## Why people do or don't adopt a tool

Kirk's framing — worth answering for each competitor:

- **Is it current?** Daily weather-driven danger (USGS) is operationally useful
  precisely because it is fresh; static regulatory maps age quickly.
- **Is it accessible?** A tool buried in an expert GIS workflow gets ignored; a
  clear map a non-specialist can read gets used.
- **Is it actionable?** "This forest is high risk" is less useful than "this
  parcel is high risk, overdue for burn, has natural firebreaks, and is on land
  we can actually treat."
- **Does it fit how the org works?** Most Sierra forest is US Forest Service
  land, which often prefers its own methods — so a tool has to slot into an
  existing decision, not replace it.

## Where EcoRiskAI fits (and where it does not)

**Not competing with** daily operational fire-danger forecasting (USGS) or
physics-based spread simulation. Those need real-time weather and heavy modeling
that a student MVP should not try to replicate.

**Complementary niche — conservation prioritization / triage:**

- A single, readable map that fuses vegetation, moisture, terrain, climate, and
  fire-history signals into one relative-risk score for **screening**.
- Pairs the risk score with **actionability** signals (time since last burn,
  natural firebreaks, ownership) — the "where do we act first" question, which
  the danger-forecast tools do not answer.
- **Annual** cadence aimed at planning conversations, not real-time dispatch.
- Explicitly a **decision-support / discussion starter** with experts, not an
  authoritative hazard layer.

## Honest differentiation

EcoRiskAI's edge is not better fire physics — it is **integration and
readability for prioritization**: turning many separate datasets into one triage
view a non-technical conservation team can act on, then layering the human
factors that decide real treatment. Its current weaknesses (sampled coverage,
limited time depth, single-proxy labels) are documented in the app's methodology
and on the roadmap.

## Next steps

1. Open the USGS Fire Danger Forecast interactive UI and note exactly which
   layers it exposes and how fresh they are.
2. Pull one screenshot each of USGS and Wildfire Risk to Communities for the
   Sierra Nevada and compare against an EcoRiskAI view of the same area.
3. Write a one-paragraph "why EcoRiskAI, given these exist" statement for the
   next conversation with TNC.

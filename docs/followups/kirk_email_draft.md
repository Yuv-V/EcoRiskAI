# Follow-up email to Kirk — DRAFT (review and send yourself)

> This is a draft for you to edit and send from your own email. It is not sent
> automatically. Fill in the bracketed parts (hosting link, attachments, paper).

**To:** Kirk Klausmeyer
**Subject:** EcoRiskAI — updates from your feedback + a hosted demo

---

Hi Kirk,

Thank you again for the time and the detailed feedback on EcoRiskAI — it gave me
a clear direction, and I've already worked through a lot of it.

A few things you asked for:

- **Hosted demo:** you can try it here — [PASTE HOSTED LINK]. It now starts on
  the Sierra Nevada and shows risk as a filled per-cell surface rather than
  scattered points.
- **Raw Earth Engine CSVs:** attached, so you can see the structure coming out
  of Earth Engine. [ATTACH data/raw/ml/yearly_exports/*.csv]

What I changed based on our conversation:

- **Fire focus.** The model target is now scoped to fire-associated forest loss,
  so timber-harvest loss doesn't blur the signal.
- **Leakage fix.** I removed the concurrent "burned this month" flag from the
  model inputs — it was co-occurring with every positive label, so the model was
  effectively detecting that a fire had already happened instead of learning the
  conditions beforehand. Labels are now anchored to the Hansen loss year, and I
  built the "month before the burn" and lag features so they switch on as soon as
  I have denser data.
- **Sample → full landscape.** You were right that the sparse map looks like a
  timed-out partial export. I wrote a tiled Earth Engine extraction (batched by
  tile and year) to cover every grid cell without timing out, and the dashboard
  already renders a wall-to-wall surface the moment that data lands.
- **Prioritization signals.** Each area now also shows time since the last
  detected burn, natural firebreaks from neighboring burn history, and a land-
  ownership hook — the "where do we actually act" factors you described.

I also started a short positioning write-up comparing EcoRiskAI to the USGS Fire
Danger Forecast and a few other tools — still confirming specifics, and I'd value
your take on where it genuinely adds something versus what already exists.

Two asks:

1. If the offer still stands, I'd love the intro to **Charlotte** on the forest
   team — the ownership / time-since-burn / controllability factors are exactly
   the kind of thing I'd want her read on.
2. Whenever it's convenient, the link to your **LLM document-review paper** — I'd
   like to read it.

Thanks again for the encouragement and the honest critique.

Best,
Yuv

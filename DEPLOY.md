# Deploying the EcoRiskAI dashboard

The dashboard is a Streamlit app. At runtime it only reads the predictions CSV
(`outputs/predictions/ecorisk_predictions.csv`) — it does **not** need the model
file or the raw data — so hosting is lightweight.

## Option A — Streamlit Community Cloud (recommended, free)

Kirk suggested getting it hosted so he can open it. Community Cloud is the
easiest path for a Streamlit app.

1. Push the repo to GitHub (see "What to commit" below).
2. Go to <https://share.streamlit.io>, sign in with GitHub.
3. "New app" → pick this repo/branch → main file path `app.py`.
4. Deploy. You get a public `https://<app>.streamlit.app` link to send Kirk.

`requirements.txt` and `.streamlit/config.toml` are already in the repo, so no
extra setup is needed.

## What to commit (and what to leave out)

**Needed for the hosted app:**
- `app.py`, `src/`, `config.yaml`, `.streamlit/`, `requirements.txt`
- `outputs/predictions/ecorisk_predictions.csv`

**Leave out** (add these to `.gitignore` before pushing):
- `data/raw/ml/*.exe` — stray installers checked into the data folder
- `data/raw/labels/**/*.tif` — large Hansen rasters
- `__pycache__/`, `*.pkl` if you prefer not to ship the model (not needed at runtime)

Suggested `.gitignore` additions:

```
__pycache__/
*.pyc
data/raw/ml/*.exe
data/raw/labels/**/*.tif
```

## Option B — run locally for a quick shared session

If you just need it up briefly during a call:

```bash
streamlit run app.py
```

Then share your screen, or expose the local port with a tunnel (e.g. an SSH or
ngrok-style tunnel) if the other person needs to click around themselves.

## Refreshing the data

To regenerate predictions before deploying:

```bash
python main.py
```

Commit the updated `outputs/predictions/ecorisk_predictions.csv` and redeploy.
Once the full-landscape extraction (`earth_engine/`) is run and
`ecorisk_landscape_predictions.csv` exists, the app switches to the wall-to-wall
surface automatically — commit that file too.

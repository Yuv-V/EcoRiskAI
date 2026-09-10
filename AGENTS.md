# EcoRiskAI Agent Instructions

## Project Goal
Build EcoRiskAI v1, a simple MVP conservation prioritization tool for the Sierra Nevada.

This is not a full production platform yet. The goal is to create a clean, believable demo that helps start a conversation with conservation organizations like The Nature Conservancy.

## Product Framing
EcoRiskAI helps identify which areas may need monitoring or restoration attention first.

Do not frame it as “solving deforestation.”
Frame it as a prototype decision-support tool.

## MVP Scope
Build only:
- Data merge pipeline
- Data cleaning pipeline
- Basic XGBoost model
- Prediction CSV
- Simple web dashboard
- Interactive map
- Clickable grid cells
- Risk explanation panel
- Basic analytics page
- Methodology page

Do not build:
- Agentic chat
- Login/auth
- Cloud deployment
- Complex deep learning
- CNNs, LSTMs, Transformers
- Huge enterprise architecture

## Data Input
Yearly CSV files from Google Earth Engine are placed here:

data/raw/ml/yearly_exports/

Expected files:

ecoriskai_master_2020.csv  
ecoriskai_master_2021.csv  
ecoriskai_master_2022.csv  
ecoriskai_master_2023.csv  
ecoriskai_master_2024.csv  
ecoriskai_master_2025.csv  
ecoriskai_master_2026.csv  

Expected columns:
- grid_id
- year
- month
- latitude
- longitude
- blue
- green
- red
- nir
- swir1
- swir2
- ndvi
- ndmi
- nbr
- treecover2000
- lossyear
- forest_loss_next_year
- forested_2000
- elevation
- slope
- aspect
- soil_moisture
- precipitation
- temperature_c
- burned_this_month
- night_lights
- landsat_image_count

## Pipeline
1. Merge yearly CSVs.
2. Clean invalid values.
3. Train XGBoost baseline.
4. Generate risk probabilities.
5. Save prediction CSV.
6. Show predictions on dashboard.

## Coding Rules
- Never modify raw data.
- Use config.yaml for paths.
- Keep code simple and readable.
- Use logging.
- Handle missing files gracefully.
- Prefer working MVP over complex architecture.
- Do not invent data.
- If real prediction data is missing, show a clear message instead of fake results.
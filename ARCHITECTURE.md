# EcoRiskAI MVP Architecture

## Simple Architecture

Google Earth Engine  
→ yearly CSV files  
→ local Python pipeline  
→ prediction CSV  
→ FastAPI backend  
→ React dashboard  

## Folder Structure

```text
EcoRiskAI/
├── data/
│   ├── raw/
│   │   └── ml/
│   │       └── yearly_exports/
│   ├── processed/
│   │   ├── merged/
│   │   ├── feature_tables/
│   │   └── model_ready/
│   └── exports/
│       └── dashboard_files/
│
├── outputs/
│   ├── metrics/
│   ├── predictions/
│   └── figures/
│
├── models/
│
├── src/
│   ├── dataset/
│   ├── models/
│   ├── api/
│   ├── utils/
│   └── visualization/
│
├── frontend/
│
├── AGENTS.md
├── PRODUCT_SPEC.md
├── UI_SPEC.md
├── DESIGN.md
├── ARCHITECTURE.md
├── ROADMAP.md
├── config.yaml
├── requirements.txt
└── main.py
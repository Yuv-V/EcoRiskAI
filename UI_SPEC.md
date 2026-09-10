# EcoRiskAI MVP UI Specification

## Overall UI Goal
The interface should feel like a clean conservation planning dashboard, not a flashy AI demo.

Style:
- Simple
- Professional
- Nature-focused
- Easy to understand quickly

## Pages

### 1. Dashboard Page

Main purpose:
Show where risk is concentrated.

Layout:
- Top navbar with title: EcoRiskAI
- Subtitle: Sierra Nevada Conservation Risk MVP
- Main map area
- Left sidebar with filters
- Right details panel when a grid cell is clicked

Map:
- Use Leaflet or another simple map library.
- Center on the Sierra Nevada.
- Show points or grid cells from the prediction CSV.
- Color by risk level.

Colors:
- Low risk: green
- Medium risk: yellow/orange
- High risk: red

Left Sidebar:
- Year selector
- Month selector if available
- Risk level filter
- Reset filters button

Right Details Panel:
Appears when a user clicks a point/cell.

Show:
- Grid ID
- Latitude
- Longitude
- Risk score
- Risk level
- NDVI
- NDMI
- NBR
- Soil moisture
- Precipitation
- Temperature
- Burned this month
- Suggested action

Suggested actions:
- Low: Continue standard monitoring
- Medium: Review during seasonal planning
- High: Prioritize for closer monitoring

### 2. Analytics Page

Purpose:
Give a simple overview.

Include:
- Total rows/cells
- Average risk
- Number of high-risk cells
- Number of medium-risk cells
- Number of low-risk cells
- Risk distribution chart
- Feature importance chart if available

### 3. Methodology Page

Purpose:
Explain the project to non-technical people.

Sections:
- Problem
- Data sources
- How the model works
- What the risk score means
- Current limitations
- Next steps

### 4. About Page

Purpose:
Tell the story.

Include:
- Why this project was made
- Why Sierra Nevada was chosen
- How conservation teams could use it
- Future vision

## Loading States
If data is loading, show:
“Loading EcoRiskAI data...”

If prediction file is missing, show:
“Prediction data has not been generated yet. Run the ML pipeline first.”

## Error Handling
No blank screens.

Always show a helpful message if:
- CSV missing
- model missing
- API not running
- map data unavailable
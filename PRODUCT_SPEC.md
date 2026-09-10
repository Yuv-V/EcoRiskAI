# EcoRiskAI MVP Product Specification

## One-Sentence Pitch
EcoRiskAI is a conservation prioritization tool that uses satellite, climate, fire, terrain, and forest-loss data to highlight Sierra Nevada areas that may need monitoring first.

## Target Audience
Primary:
- Conservation scientists
- GIS analysts
- Land managers
- Environmental nonprofit teams

Demo audience:
- The Nature Conservancy staff
- Environmental researchers
- Potential mentors or collaborators

## Core Problem
The Sierra Nevada is large. Conservation teams cannot manually inspect every forest area, watershed, or habitat zone. EcoRiskAI helps surface areas that may deserve attention by combining multiple environmental signals into a simple risk view.

## MVP Goal
Create a working prototype that answers:

“Which areas appear higher-risk, and why?”

## MVP Features

### 1. Interactive Map
A map of the Sierra Nevada with fixed grid points or cells colored by risk.

Risk levels:
- Low
- Medium
- High

### 2. Risk Score
Each grid cell has a risk probability or score.

Example:
- Risk Score: 82/100
- Risk Level: High

### 3. Explanation Panel
When a user clicks a grid cell, show simple reasons.

Example:
- Low NDVI
- Low soil moisture
- Recent burn signal
- High temperature
- Low precipitation

### 4. Analytics Page
Show basic summary cards:
- Total grid cells
- Average risk
- High-risk cells
- Model accuracy or F1 score if available

### 5. Methodology Page
Explain the pipeline simply:

Google Earth Engine  
→ Satellite and climate features  
→ Machine learning  
→ Risk score  
→ Map dashboard  

## Non-Goals
This MVP does not need:
- Production accuracy
- Live data updates
- User accounts
- Chatbot
- Cloud deployment
- Perfect map styling
- Advanced deep learning

## Success Criteria
The MVP is successful if:
- The dashboard opens locally.
- It shows Sierra Nevada prediction points.
- Clicking a point shows a risk score and explanation.
- The methodology is easy to understand.
- It supports a conversation with conservation experts.
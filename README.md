# MPLADS-IntelliTrack

## Problem Statement
- **Problem Statement ID:** SIH PS 26102
- **Title:** Development of an AI-powered system to detect anomalies, fraud, and inefficiencies in MPLAD Scheme implementation.

## Project Objective
MPLADS-IntelliTrack is an intelligent monitoring and risk-assessment platform designed to bring end-to-end transparency, accountability, and operational efficiency to the Member of Parliament Local Area Development Scheme (MPLADS). By leveraging machine learning anomaly detection, geospatial intelligence, and automated risk scoring on public project lifecycle data, the system identifies implementation bottlenecks, fund misallocations, vendor clustering, and duplicate project sanctions, empowering administrators, auditors, and citizens with actionable oversight and data-driven field verification capabilities.

## Planned Architecture
The platform is structured into modular layers designed for scalability, data integrity, and high performance:
- **Presentation Layer (Frontend):** Responsive user dashboard offering geospatial mapping, analytical charts, risk alert feeds, and interactive query tools.
- **Application & API Layer (Backend):** Fast and robust REST API managing authentication, project workflows, ingestion pipelines, and ML inference endpoints.
- **Analytics & Intelligence Layer (ML & AI):** Anomaly detection, clustering, risk prioritization models, and LLM-powered natural language query assistance and automated summary generation.
- **Data & Spatial Storage Layer (Database & GIS):** Relational database with spatial indexing to efficiently manage constituency geospatial boundaries, project locations, and transaction histories.

## Planned Technology Stack
- **Frontend:** React, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI
- **Machine Learning:** Python, Pandas, scikit-learn
- **Database:** PostgreSQL / Supabase
- **GIS:** PostGIS, Leaflet / MapLibre
- **AI Assistant:** LLM API

## Project Structure
```
MPLADS-IntelliTrack/
├── frontend/
├── backend/
├── ml/
├── data/
│   ├── raw/
│   └── processed/
├── docs/
├── .gitignore
└── README.md
```

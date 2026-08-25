# MPLADS-IntelliTrack - Backend API

FastAPI backend service for **MPLADS-IntelliTrack** (SIH PS 26102 prototype).

## Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py          # Application configuration and path resolution
│   ├── data_loader.py     # Reusable CSV loader utilities for data/raw/
│   ├── main.py            # FastAPI entry point, CORS, and endpoints
│   ├── anomaly_engine/    # Modular Rule-Based Anomaly Detection Engine (12 Rules)
│   │   ├── __init__.py
│   │   ├── models.py      # Data structures, SeverityEnum, AnomalyTypeEnum, ThresholdConfig
│   │   ├── cost.py        # Cost overrun detection rules
│   │   ├── financial.py   # Financial, progress mismatch, and payment pattern rules
│   │   ├── progress.py    # Timeline, delay, milestone lag, and completion risk rules
│   │   └── engine.py      # Core AnomalyEngine coordinator
│   └── routers/
│       └── __init__.py    # Modular route package for future endpoints
├── requirements.txt       # Python dependencies
└── README.md              # Documentation and setup instructions
```

## Prerequisites

- Python 3.10+
- Raw CSV datasets located in `data/raw/`:
  - `projects.csv`
  - `financials.csv`
  - `progress_updates.csv`
  - `payments.csv`
  - `vendors.csv`
  - `implementing_agencies.csv`
  - `evidence.csv`
  - `compliance.csv`

## Setup & Installation

### 1. Create and Activate Virtual Environment (Recommended)

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Running the Server

Start the development server using Uvicorn:

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at: `http://localhost:8000`

## API Endpoints

- **Interactive Swagger Docs:** `http://localhost:8000/docs`
- **Alternative Redoc Docs:** `http://localhost:8000/redoc`
- **Health Check:** `GET /health`
- **Projects List:** `GET /api/projects?limit=50&offset=0`
- **All Anomalies:** `GET /api/anomalies?severity=CRITICAL&anomaly_type=PROJECT_DELAY`
- **Single Project Anomalies:** `GET /api/anomalies/{project_id}`

# MPLADS-IntelliTrack - Machine Learning Anomaly Detection Layer

Unsupervised Machine Learning anomaly detection engine for **MPLADS-IntelliTrack** (SIH PS 26102 prototype).

## Architectural Role & Independence

The ML engine operates as an **independent unsupervised anomaly detection layer** alongside the deterministic 31-rule engine.
It detects multidimensional statistical outliers and unusual project patterns across 29 engineered features without requiring ground-truth fraud labels.

```
Raw CSV Datasets (8 files)
         ↓
Feature Engineering (29 independent features across Financial, Progress, Payment, Vendor, Compliance, Geo)
         ↓
StandardScaler Preprocessing
         ↓
Isolation Forest (Unsupervised statistical outlier detection)
         ↓
Normalized 0–100 ML Anomaly Score & Flag
         ↓
FastAPI Endpoints (/api/ml/anomalies)
```

## Fundamental ML Principles

1. **Unsupervised Formulation**: The system detects **statistical irregularity and distributional outliers**, not legal/financial fraud.
2. **No Circular Leakage**: Features are derived strictly from raw continuous data and neutral statistical descriptors. No anomaly flags, severity weights, or rule-engine thresholds are used as ML features.
3. **Geographic Neutrality**: Raw GPS coordinates (`latitude`, `longitude`) are excluded to avoid boundary bias across national coordinates. Relative spatial proximity (`nearby_projects_count_5km`) is retained.
4. **Operational Contamination Rate**: The `contamination=0.10` setting is an operational threshold defining the top 10% most isolated multidimensional outliers.

## Features (29 Total)

1. **Financial (6 features)**:
   - `sanctioned_amount_lakh`, `estimated_cost_lakh`, `expenditure_lakh`, `expenditure_to_sanction_ratio`, `cost_variance_pct`, `utilization_pct`
2. **Progress & Timeline (7 features)**:
   - `physical_progress_pct`, `planned_progress_pct`, `progress_financial_gap`, `planned_duration_days`, `delay_days`, `progress_updates_count`, `days_since_last_update`
3. **Payments (6 features)**:
   - `payment_count`, `total_payment_amount_lakh`, `avg_payment_amount_lakh`, `max_payment_amount_lakh`, `max_payment_ratio`, `payment_date_span_days`
4. **Vendor & Agency Descriptors (7 features)**:
   - `vendor_total_projects`, `vendor_average_expenditure`, `vendor_expenditure_std`, `vendor_average_project_cost`, `agency_total_projects`, `agency_average_expenditure`, `agency_expenditure_std`
5. **Compliance & Evidence (2 features)**:
   - `missing_compliance_count`, `total_evidence_count`
6. **Geographic Intelligence (1 feature)**:
   - `nearby_projects_count_5km`

## Model Configuration

- **Algorithm**: `IsolationForest` (scikit-learn)
- **Estimators**: 150
- **Contamination**: 0.10 (10% statistical outlier threshold)
- **Random State**: 42 (deterministic reproducibility)
- **Version**: `v1.0.0-isolation-forest`

## Running Training

```bash
python ml/train.py
```

Trained model artifacts are stored in `ml/model_artifacts/`:
- `model.joblib`: Trained Isolation Forest estimator
- `scaler.joblib`: Fitted StandardScaler
- `features.json`: Ordered list of 29 feature names
- `config.json`: Model version and calibration hyperparameters

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from app.config import settings

# Raw data file mappings
RAW_DATA_FILES = {
    "projects": "projects.csv",
    "financials": "financials.csv",
    "progress_updates": "progress_updates.csv",
    "payments": "payments.csv",
    "vendors": "vendors.csv",
    "implementing_agencies": "implementing_agencies.csv",
    "evidence": "evidence.csv",
    "compliance": "compliance.csv",
}


def resolve_data_path(filename: str, data_dir: Optional[Path | str] = None) -> Path:
    """
    Resolves the absolute path of a data file.
    Checks the provided data_dir or settings.DATA_RAW_DIR, with fallbacks.
    """
    candidate_dirs: List[Path] = []

    if data_dir:
        candidate_dirs.append(Path(data_dir))

    candidate_dirs.extend([
        settings.DATA_RAW_DIR,
        Path(__file__).resolve().parent.parent.parent / "data" / "raw",
        Path("../data/raw").resolve(),
        Path("data/raw").resolve(),
    ])

    for base_dir in candidate_dirs:
        candidate_path = (base_dir / filename).resolve()
        if candidate_path.is_file():
            return candidate_path

    # If not found in any candidate, return the primary configured path for error reporting
    return (Path(data_dir) if data_dir else settings.DATA_RAW_DIR) / filename


def dataframe_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Converts a pandas DataFrame into a JSON-serializable list of dictionaries,
    properly converting NaN and NaT values to None.
    """
    json_str = df.to_json(orient="records", date_format="iso")
    return json.loads(json_str)


def load_csv(filename: str, data_dir: Optional[Path | str] = None) -> pd.DataFrame:
    """
    Loads a CSV file into a pandas DataFrame with error handling.

    Raises:
        FileNotFoundError: If the CSV file is not found in the raw data directory.
        RuntimeError: If there is an issue reading the CSV file.
    """
    file_path = resolve_data_path(filename, data_dir)
    if not file_path.exists():
        raise FileNotFoundError(
            f"Dataset '{filename}' not found at '{file_path}'. "
            f"Please verify that the raw CSV data files exist in the 'data/raw/' directory."
        )

    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        raise RuntimeError(f"Failed to read CSV dataset from '{file_path}': {str(e)}") from e


def load_projects(data_dir: Optional[Path | str] = None) -> pd.DataFrame:
    """Load projects.csv dataset."""
    return load_csv(RAW_DATA_FILES["projects"], data_dir)


def load_financials(data_dir: Optional[Path | str] = None) -> pd.DataFrame:
    """Load financials.csv dataset."""
    return load_csv(RAW_DATA_FILES["financials"], data_dir)


def load_progress_updates(data_dir: Optional[Path | str] = None) -> pd.DataFrame:
    """Load progress_updates.csv dataset."""
    return load_csv(RAW_DATA_FILES["progress_updates"], data_dir)


def load_payments(data_dir: Optional[Path | str] = None) -> pd.DataFrame:
    """Load payments.csv dataset."""
    return load_csv(RAW_DATA_FILES["payments"], data_dir)


def load_vendors(data_dir: Optional[Path | str] = None) -> pd.DataFrame:
    """Load vendors.csv dataset."""
    return load_csv(RAW_DATA_FILES["vendors"], data_dir)


def load_implementing_agencies(data_dir: Optional[Path | str] = None) -> pd.DataFrame:
    """Load implementing_agencies.csv dataset."""
    return load_csv(RAW_DATA_FILES["implementing_agencies"], data_dir)


def load_evidence(data_dir: Optional[Path | str] = None) -> pd.DataFrame:
    """Load evidence.csv dataset."""
    return load_csv(RAW_DATA_FILES["evidence"], data_dir)


def load_compliance(data_dir: Optional[Path | str] = None) -> pd.DataFrame:
    """Load compliance.csv dataset."""
    return load_csv(RAW_DATA_FILES["compliance"], data_dir)


def load_all_datasets(data_dir: Optional[Path | str] = None) -> Dict[str, pd.DataFrame]:
    """Loads all 8 raw CSV datasets into a dictionary of DataFrames."""
    return {name: load_csv(filename, data_dir) for name, filename in RAW_DATA_FILES.items()}

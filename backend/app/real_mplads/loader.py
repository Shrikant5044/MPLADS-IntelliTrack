import os
from pathlib import Path
import threading
from typing import Dict, List, Optional
import pandas as pd
from app.config import settings
from app.real_mplads.models import RealWorkRecord, RealMPLADSStatsResponse


class RealMPLADSLoader:
    """
    Thread-safe data loader and memory cache for the real MPLADS dataset.
    Loads and standardizes recommended works, completed works, and macro financial summaries.
    """
    _instance: Optional["RealMPLADSLoader"] = None
    _lock = threading.Lock()

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            self.data_dir = data_dir
        else:
            candidate_dirs = [
                settings.DATA_REAL_MPLADS_DIR,
                Path(__file__).resolve().parent.parent.parent.parent / "data" / "real_mplads",
                Path(__file__).resolve().parent.parent.parent / "data" / "real_mplads",
                Path("../data/real_mplads").resolve(),
                Path("data/real_mplads").resolve(),
            ]
            self.data_dir = str(candidate_dirs[0])
            for d in candidate_dirs:
                p = Path(d)
                if p.is_dir() and (p / "mplads_recommended_works_2026-08-25.csv").is_file():
                    self.data_dir = str(p.resolve())
                    break
        self.recommended_df: pd.DataFrame = pd.DataFrame()
        self.completed_df: pd.DataFrame = pd.DataFrame()
        self.expenditures_df: pd.DataFrame = pd.DataFrame()
        self.mp_summary_df: pd.DataFrame = pd.DataFrame()
        self.allocated_limit_df: pd.DataFrame = pd.DataFrame()
        self.calamity_df: pd.DataFrame = pd.DataFrame()

        self.recommended_records: List[RealWorkRecord] = []
        self.completed_records: List[RealWorkRecord] = []
        self.recommended_by_id: Dict[int, RealWorkRecord] = {}
        self.completed_by_id: Dict[int, RealWorkRecord] = {}
        self._is_loaded = False

    def load_all(self, force_reload: bool = False) -> None:
        if self._is_loaded and not force_reload:
            return

        with self._lock:
            if self._is_loaded and not force_reload:
                return

            # 1. Recommended Works
            rec_path = os.path.join(self.data_dir, "mplads_recommended_works_2026-08-25.csv")
            if os.path.exists(rec_path):
                df = pd.read_csv(rec_path, low_memory=False, encoding="utf-8")
                amt_col = [c for c in df.columns if "Amount" in c][0]
                df["work_id"] = pd.to_numeric(df["Work ID"], errors="coerce").fillna(0).astype(int)
                df["work_description"] = df["Work Description"].fillna("").astype(str)
                df["category"] = df["Category"].fillna("Normal/Others").astype(str)
                df["mp_name"] = df["MP Name"].fillna("").astype(str)
                df["constituency"] = df["Constituency"].fillna("").astype(str)
                df["state"] = df["State"].fillna("").astype(str)
                df["house"] = df["House"].fillna("").astype(str)
                df["amount"] = pd.to_numeric(df[amt_col], errors="coerce").fillna(0.0).astype(float)
                df["amount_lakh"] = (df["amount"] / 100000.0).round(2)
                df["date"] = df["Recommendation Date"].fillna("").astype(str)
                df["has_images"] = df["Has Images"].fillna(False).astype(bool)
                df["ida"] = df["IDA"].fillna("").astype(str)
                self.recommended_df = df

                records = []
                by_id = {}
                for _, row in df.iterrows():
                    rec = RealWorkRecord(
                        work_id=int(row["work_id"]),
                        work_description=str(row["work_description"]),
                        category=str(row["category"]),
                        mp_name=str(row["mp_name"]),
                        constituency=str(row["constituency"]),
                        state=str(row["state"]),
                        house=str(row["house"]),
                        amount=float(row["amount"]),
                        amount_lakh=float(row["amount_lakh"]),
                        date=str(row["date"]),
                        has_images=bool(row["has_images"]),
                        ida=str(row["ida"]),
                        dataset_source="recommended_works",
                    )
                    records.append(rec)
                    # Use first occurrence if duplicate Work ID
                    if rec.work_id not in by_id:
                        by_id[rec.work_id] = rec
                self.recommended_records = records
                self.recommended_by_id = by_id

            # 2. Completed Works
            comp_path = os.path.join(self.data_dir, "mplads_completed_works_2026-08-25.csv")
            if os.path.exists(comp_path):
                df = pd.read_csv(comp_path, low_memory=False, encoding="utf-8")
                amt_col = [c for c in df.columns if "Amount" in c][0]
                df["work_id"] = pd.to_numeric(df["Work ID"], errors="coerce").fillna(0).astype(int)
                df["work_description"] = df["Work Description"].fillna("").astype(str)
                df["category"] = df["Category"].fillna("Normal/Others").astype(str)
                df["mp_name"] = df["MP Name"].fillna("").astype(str)
                df["constituency"] = df["Constituency"].fillna("").astype(str)
                df["state"] = df["State"].fillna("").astype(str)
                df["house"] = df["House"].fillna("").astype(str)
                df["amount"] = pd.to_numeric(df[amt_col], errors="coerce").fillna(0.0).astype(float)
                df["amount_lakh"] = (df["amount"] / 100000.0).round(2)
                df["date"] = df["Completed Date"].fillna("").astype(str)
                df["has_images"] = df["Has Images"].fillna(False).astype(bool)
                df["ida"] = df["IDA"].fillna("").astype(str)
                self.completed_df = df

                records = []
                by_id = {}
                for _, row in df.iterrows():
                    rec = RealWorkRecord(
                        work_id=int(row["work_id"]),
                        work_description=str(row["work_description"]),
                        category=str(row["category"]),
                        mp_name=str(row["mp_name"]),
                        constituency=str(row["constituency"]),
                        state=str(row["state"]),
                        house=str(row["house"]),
                        amount=float(row["amount"]),
                        amount_lakh=float(row["amount_lakh"]),
                        date=str(row["date"]),
                        has_images=bool(row["has_images"]),
                        ida=str(row["ida"]),
                        dataset_source="completed_works",
                    )
                    records.append(rec)
                    if rec.work_id not in by_id:
                        by_id[rec.work_id] = rec
                self.completed_records = records
                self.completed_by_id = by_id

            # 3. Expenditures
            exp_path = os.path.join(self.data_dir, "mplads_expenditures_2026-08-25.csv")
            if os.path.exists(exp_path):
                self.expenditures_df = pd.read_csv(exp_path, low_memory=False, encoding="utf-8")

            # 4. MP Summary
            mp_path = os.path.join(self.data_dir, "mplads_mp_summary_2026-08-25.csv")
            if os.path.exists(mp_path):
                self.mp_summary_df = pd.read_csv(mp_path, low_memory=False, encoding="utf-8")

            # 5. Allocated Limit
            alloc_path = os.path.join(self.data_dir, "Allocated Limit for Honble MPs.csv")
            if os.path.exists(alloc_path):
                self.allocated_limit_df = pd.read_csv(alloc_path, low_memory=False, encoding="utf-8")

            # 6. Calamity
            cal_path = os.path.join(self.data_dir, "Amount consented for Calamity.csv")
            if os.path.exists(cal_path):
                self.calamity_df = pd.read_csv(cal_path, low_memory=False, encoding="utf-8")

            self._is_loaded = True

    def get_stats(self) -> RealMPLADSStatsResponse:
        self.load_all()

        rec_amt_total = float(self.recommended_df["amount"].sum()) if not self.recommended_df.empty else 0.0
        comp_amt_total = float(self.completed_df["amount"].sum()) if not self.completed_df.empty else 0.0
        
        exp_amt_total = 0.0
        if not self.expenditures_df.empty:
            exp_col = [c for c in self.expenditures_df.columns if "Amount" in c]
            if exp_col:
                exp_amt_total = float(pd.to_numeric(self.expenditures_df[exp_col[0]], errors="coerce").fillna(0.0).sum())

        cat_dist = {}
        if not self.recommended_df.empty:
            cat_dist = self.recommended_df["category"].value_counts().to_dict()

        state_dist = {}
        if not self.recommended_df.empty:
            state_dist = self.recommended_df["state"].value_counts().head(10).to_dict()

        return RealMPLADSStatsResponse(
            total_recommended_works=len(self.recommended_records),
            total_completed_works=len(self.completed_records),
            total_expenditure_records=len(self.expenditures_df),
            total_mp_summary_records=len(self.mp_summary_df),
            total_recommended_amount_lakh=round(rec_amt_total / 100000.0, 2),
            total_completed_final_amount_lakh=round(comp_amt_total / 100000.0, 2),
            total_disbursed_expenditure_lakh=round(exp_amt_total / 100000.0, 2),
            categories_distribution=cat_dist,
            top_states_by_works=state_dist,
        )


_loader_instance = RealMPLADSLoader()


def get_real_data_loader() -> RealMPLADSLoader:
    if not _loader_instance._is_loaded:
        _loader_instance.load_all()
    return _loader_instance

from app.real_mplads.benchmarking import (
    RealPeerBenchmarkEngine,
    are_asset_domains_compatible,
    detect_asset_domain,
    get_real_benchmark_engine,
)
from app.real_mplads.loader import (
    RealMPLADSLoader,
    get_real_data_loader,
)
from app.real_mplads.models import (
    RealComparableWorkPeer,
    RealMPLADSStatsResponse,
    RealWorkBenchmarkResult,
    RealWorkRecord,
    RealWorksListResponse,
)
from app.real_mplads.search_index import (
    RealMPLADSSearchIndex,
    clean_work_description,
    get_real_search_index,
)

__all__ = [
    "RealMPLADSLoader",
    "get_real_data_loader",
    "RealMPLADSSearchIndex",
    "get_real_search_index",
    "RealPeerBenchmarkEngine",
    "get_real_benchmark_engine",
    "RealWorkRecord",
    "RealComparableWorkPeer",
    "RealWorkBenchmarkResult",
    "RealWorksListResponse",
    "RealMPLADSStatsResponse",
    "clean_work_description",
    "detect_asset_domain",
    "are_asset_domains_compatible",
]

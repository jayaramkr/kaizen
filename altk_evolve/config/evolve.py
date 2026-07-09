from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class EvolveConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EVOLVE_", env_file=".env", extra="ignore")
    backend: Literal["milvus", "filesystem", "postgres"] = "filesystem"
    namespace_id: str = "evolve"
    settings: BaseSettings | None = None
    clustering_threshold: float = 0.80
    segmentation_enabled: bool = True
    # Consolidation dosage knobs (see docs: capability-dependent dosage).
    #   none     - skip consolidation entirely
    #   lossless - merge only equivalent guidelines; conserve support (default)
    #   lossy    - merge more aggressively (fewer, broader guidelines); support still conserved
    # Support-threshold *filtering* (sup2/sup3) is applied non-destructively at selection
    # time, not by deleting entities here.
    consolidation_mode: Literal["none", "lossless", "lossy"] = "lossless"
    lossy_target_num_guidelines: int = 12
    # Dosage-aware retrieval knobs (see docs: capability-dependent dosage).
    #   static    - inject the whole playbook (best for strong models)
    #   retrieval - inject core (support >= core_support) + top-k task-relevant guidelines
    injection_mode: Literal["static", "retrieval"] = "retrieval"
    retrieval_top_k: int = 10
    core_support: int = 3
    min_support: int = 1  # non-destructive sup2/sup3 filter on the candidate pool
    retrieval_similarity_key: Literal["source_task", "guideline_text"] = "source_task"
    retrieval_near_core_thresh: float = 0.75
    retrieval_dedup_thresh: float = 0.90
    evidence_filter: Literal["all", "success", "failure"] = "all"


# to reload settings call evolve_config.__init__()
evolve_config = EvolveConfig()

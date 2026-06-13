from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    version: str
    message: str


class ChartItem(BaseModel):
    label: str
    value: int


class DashboardStatsResponse(BaseModel):
    total_text_records: int
    full_text_count: int
    metadata_only_count: int
    retrieval_unit_count: int
    fts_row_count: int
    amount_mention_count: int
    entity_mention_count: int
    place_mention_count: int
    evidence_count: int
    remittance_record_count: int


class DashboardDistributionsResponse(BaseModel):
    text_quality_distribution: List[ChartItem]
    main_intent_distribution: List[ChartItem]
    relationship_distribution: List[ChartItem]
    unit_type_distribution: List[ChartItem]
    top_places: List[ChartItem]
    top_countries_or_regions: List[ChartItem]
    year_distribution: List[ChartItem]


class SearchRequest(BaseModel):
    query: str = ""
    top_k: int = Field(default=10, ge=1, le=100)
    unit_types: List[str] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    expansion_mode: Literal["strict", "balanced", "broad"] = "balanced"


class SearchResult(BaseModel):
    record_id: str
    unit_id: str
    unit_type: str
    title_reference: str
    sender: str
    recipient: str
    date_text: str
    main_intent: str
    unit_text: str
    snippet: str
    matched_text: str
    matched_reason: str
    bm25_score: float
    semantic_score: float = 0.0
    final_score: float
    retrieval_sources: List[str] = Field(default_factory=list)
    original_hit_count: int
    strong_hit_count: int
    medium_hit_count: int
    weak_hit_count: int
    evidence_type: str
    source_column: str


class GroupedMatchedUnit(BaseModel):
    unit_id: str
    unit_type: str
    unit_text: str
    source_column: str
    evidence_type: str
    bm25_score: float
    semantic_score: float = 0.0
    final_score: float
    retrieval_sources: List[str] = Field(default_factory=list)
    matched_reason: str
    original_hit_count: int
    strong_hit_count: int
    medium_hit_count: int
    weak_hit_count: int


class GroupedSearchRecord(BaseModel):
    record_id: str
    title_reference: str
    sender: str
    recipient: str
    date_text: str
    main_intent: str
    best_score: float
    matched_units: List[GroupedMatchedUnit]


class SearchResponse(BaseModel):
    query: str
    normalized_query: str
    expanded_query: str
    expansion_mode: Literal["strict", "balanced", "broad"]
    original_terms: List[str]
    strong_expansion_terms: List[str]
    medium_expansion_terms: List[str]
    weak_expansion_terms: List[str]
    expansion_terms: List[str]
    top_k: int
    semantic_enabled: bool
    results: List[SearchResult]
    grouped_by_record: List[GroupedSearchRecord]
    fusion_method: Optional[str] = None
    error_message: Optional[str] = None


class HybridSearchResponse(SearchResponse):
    fusion_method: str
    error_message: Optional[str] = None


class SemanticSearchRequest(BaseModel):
    query: str = ""
    top_k: int = Field(default=10, ge=1, le=100)
    unit_types: List[str] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)


class SemanticSearchResponse(BaseModel):
    query: str
    top_k: int
    semantic_enabled: bool
    results: List[SearchResult]
    error_message: Optional[str] = None
    index_backend: Optional[str] = None


class SemanticStatusResponse(BaseModel):
    semantic_enabled: bool
    configured_enabled: bool
    index_exists: bool
    metadata_exists: bool
    embedding_provider: str
    embedding_model: str
    index_path: str
    metadata_path: str
    vector_count: int
    error_message: Optional[str] = None


class RagContextRequest(BaseModel):
    query: str
    top_k: int = Field(default=8, ge=1, le=50)
    unit_types: List[str] = Field(
        default_factory=lambda: [
            "body_core",
            "remittance",
            "family_care",
            "instruction",
            "rag_summary",
        ]
    )
    filters: Dict[str, Any] = Field(default_factory=dict)
    expansion_mode: Literal["strict", "balanced", "broad"] = "balanced"
    retrieval_mode: Literal["keyword", "semantic", "hybrid"] = "hybrid"


class RagContextItem(BaseModel):
    record_id: str
    unit_id: str
    unit_type: str
    title_reference: str
    sender: str
    recipient: str
    date_text: str
    main_intent: str
    unit_text: str
    source_column: str
    evidence_type: str
    matched_reason: str
    final_score: float


class RagContextResponse(BaseModel):
    query: str
    normalized_query: str
    expanded_query: str
    expansion_mode: Literal["strict", "balanced", "broad"]
    semantic_enabled: bool
    contexts: List[RagContextItem]
    grouped_contexts: List[GroupedSearchRecord]
    prompt_context: str
    evidence_count: int
    source_record_count: int


class StyleContextRequest(BaseModel):
    query: str
    top_k: int = Field(default=3, ge=1, le=20)
    filters: Dict[str, Any] = Field(default_factory=dict)
    expansion_mode: Literal["strict", "balanced", "broad"] = "balanced"


class StyleSlotExample(BaseModel):
    record_id: str
    unit_id: str
    unit_type: str
    title_reference: str
    unit_text: str
    source_column: str
    evidence_type: str
    matched_reason: str
    final_score: float


class StyleContextResponse(BaseModel):
    query: str
    normalized_query: str
    expanded_query: str
    expansion_mode: Literal["strict", "balanced", "broad"]
    semantic_enabled: bool
    style_slots: Dict[str, List[StyleSlotExample]]
    grouped_contexts: List[GroupedSearchRecord]
    prompt_context: str
    source_record_count: int


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class EvidenceReference(BaseModel):
    record_id: str
    unit_id: str
    unit_type: str
    title_reference: str
    source_column: str
    evidence_type: str
    unit_text: str


class ValidationEvidenceCoverage(BaseModel):
    has_evidence_references: bool
    evidence_count: int
    covered_unit_types: List[str]


class ValidationCheckItem(BaseModel):
    name: str
    status: Literal["pass", "warn", "fail"]
    message: str


class ValidationReport(BaseModel):
    is_consistent: bool
    risk_level: Literal["low", "medium", "high"]
    summary: str
    preserved_facts: List[str] = Field(default_factory=list)
    possible_hallucinations: List[str] = Field(default_factory=list)
    missing_required_facts: List[str] = Field(default_factory=list)
    unsupported_new_facts: List[str] = Field(default_factory=list)
    evidence_coverage: ValidationEvidenceCoverage
    checks: List[ValidationCheckItem]


class ConsistencyCheckRequest(BaseModel):
    task_type: Literal["interpret", "style-transfer"]
    input_text: str
    generated_text: str
    evidence_references: List[EvidenceReference] = Field(default_factory=list)
    record_id: Optional[str] = None


class ConsistencyCheckResponse(BaseModel):
    validation_report: ValidationReport


class GenerationInterpretRequest(BaseModel):
    query: str
    record_id: Optional[str] = None
    top_k: int = Field(default=8, ge=1, le=50)
    filters: Dict[str, Any] = Field(default_factory=dict)
    expansion_mode: Literal["strict", "balanced", "broad"] = "balanced"
    dry_run: bool = False


class GenerationInterpretResponse(BaseModel):
    task_type: Literal["interpret"]
    query: str
    record_id: Optional[str] = None
    semantic_enabled: bool
    prompt_context: str
    generated_text: str
    evidence_references: List[EvidenceReference]
    model: str
    dry_run: bool
    messages: List[ChatMessage] = Field(default_factory=list)
    error_message: Optional[str] = None
    validation_report: Optional[ValidationReport] = None


class GenerationStyleTransferRequest(BaseModel):
    plain_text: str
    top_k: int = Field(default=3, ge=1, le=20)
    filters: Dict[str, Any] = Field(default_factory=dict)
    expansion_mode: Literal["strict", "balanced", "broad"] = "balanced"
    dry_run: bool = False


class GenerationStyleTransferResponse(BaseModel):
    task_type: Literal["style-transfer"]
    plain_text: str
    semantic_enabled: bool
    style_slots: Dict[str, List[StyleSlotExample]]
    prompt_context: str
    generated_text: str
    evidence_references: List[EvidenceReference]
    model: str
    dry_run: bool
    messages: List[ChatMessage] = Field(default_factory=list)
    error_message: Optional[str] = None
    validation_report: Optional[ValidationReport] = None


class PromptPreviewRequest(BaseModel):
    task_type: Literal["interpret", "style-transfer"]
    input_text: str
    record_id: Optional[str] = None
    top_k: int = Field(default=3, ge=1, le=50)
    filters: Dict[str, Any] = Field(default_factory=dict)
    expansion_mode: Literal["strict", "balanced", "broad"] = "balanced"


class PromptPreviewResponse(BaseModel):
    task_type: Literal["interpret", "style-transfer"]
    input_text: str
    prompt_context: str
    messages: List[ChatMessage]
    evidence_references: List[EvidenceReference]


class QwenConfigStatusResponse(BaseModel):
    enabled: bool
    api_key_configured: bool
    base_url_configured: bool
    model: str
    timeout_seconds: int
    project_env_exists: bool
    backend_env_exists: bool
    live_generation_ready: bool


class AmountMention(BaseModel):
    mention_id: str
    record_id: str
    raw_text: str
    amount_text: str
    amount_number: Optional[float] = None
    currency: str
    sentence: str
    is_primary_candidate: Optional[int] = None
    source_field: str


class EntityItem(BaseModel):
    mention_id: Optional[str] = None
    record_id: Optional[str] = None
    entity_type: str
    value: str
    source_text: str
    normalized_text: str = ""
    source_field: str = ""
    confidence: Optional[float] = None


class PlaceMention(BaseModel):
    mention_id: str
    record_id: str
    alias_text: str
    normalized_place: str
    country_or_region: str
    source_field: str


class EvidenceItem(BaseModel):
    evidence_id: Optional[str] = None
    record_id: Optional[str] = None
    evidence_type: Optional[str] = None
    evidence_text: Optional[str] = None
    source_column: Optional[str] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    source_field: Optional[str] = None
    source_text: Optional[str] = None
    reason: Optional[str] = None
    similarity_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class RetrievalUnit(BaseModel):
    unit_id: str
    record_id: str
    unit_type: str
    source_column: str
    unit_text: str
    title_reference: str
    sender: str
    recipient: str
    date_text: str
    main_intent: str
    theme_tags: str
    style_keywords: str
    relationship_type: str
    place_mentions_normalized: str
    retrieval_keywords: str
    weight: float
    evidence_type: str
    fts_text: str


class RecordDetailResponse(BaseModel):
    record_id: str
    title_reference: str
    sender: str
    recipient: str
    sender_name_clean: str
    recipient_name_clean: str
    date_text: str
    year_normalized: str
    body_clean: str
    body_core: str
    main_intent: str
    theme_tags: str
    text_quality_level: str
    has_full_text: int
    has_remittance: int
    relationship_type: str
    place_mentions_normalized: str
    retrieval_keywords: str
    rag_summary_text: str
    style_reference_text: str
    raw_fields: Dict[str, Any]


class AmountsResponse(BaseModel):
    record_id: str
    amounts: List[AmountMention]


class EntityResponse(BaseModel):
    record_id: str
    entities: List[EntityItem]


class PlacesResponse(BaseModel):
    record_id: str
    places: List[PlaceMention]


class EvidenceResponse(BaseModel):
    record_id: str
    evidence: List[EvidenceItem]


class RetrievalUnitsResponse(BaseModel):
    record_id: str
    retrieval_units: List[RetrievalUnit]


class EvidenceMappingItem(BaseModel):
    target_span: str
    source_field: str
    source_text: str
    reason: str
    similarity_score: float = Field(ge=0.0, le=1.0)


class ConsistencyCheck(BaseModel):
    status: str
    warnings: List[str] = Field(default_factory=list)
    passed_rules: List[str] = Field(default_factory=list)
    failed_rules: List[str] = Field(default_factory=list)


class PlainInterpretationRequest(BaseModel):
    record_id: Optional[str] = None
    original_text: Optional[str] = None


class PlainInterpretationResponse(BaseModel):
    record_id: Optional[str]
    generated_text: str
    summary: List[str]
    slots: Dict[str, str]
    evidence: List[EvidenceItem]
    evidence_mapping: List[EvidenceMappingItem]
    consistency_check: ConsistencyCheck


class StyleTransferRequest(BaseModel):
    plain_text: str
    slots: Dict[str, str] = Field(default_factory=dict)


class StyleTransferResponse(BaseModel):
    generated_text: str
    summary: List[str]
    slots: Dict[str, str]
    evidence: List[EvidenceItem]
    evidence_mapping: List[EvidenceMappingItem]
    consistency_check: ConsistencyCheck

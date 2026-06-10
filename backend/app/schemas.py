from __future__ import annotations

from typing import Any, Dict, List, Optional

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
    bm25_score: float
    evidence_type: str
    source_column: str


class SearchResponse(BaseModel):
    query: str
    top_k: int
    results: List[SearchResult]


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

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    version: str
    message: str


class ChartItem(BaseModel):
    label: str
    value: int


class DashboardStatsResponse(BaseModel):
    total_records: int
    text_records: int
    origin_places: List[ChartItem]
    destination_places: List[ChartItem]
    kinship_distribution: List[ChartItem]
    money_distribution: List[ChartItem]
    timeline: List[ChartItem]


class EvidenceItem(BaseModel):
    source_field: str
    source_text: str
    reason: str
    similarity_score: float = Field(ge=0.0, le=1.0)


class SearchRequest(BaseModel):
    query: str = ""
    filters: Dict[str, Optional[str]] = Field(default_factory=dict)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


class SearchResult(BaseModel):
    record_id: str
    title: str
    origin_place: str
    destination_place: str
    date: str
    sender: str
    recipient: str
    kinship: str
    money: str
    snippet: str
    score: float = Field(ge=0.0, le=1.0)
    evidence: List[EvidenceItem]


class SearchResponse(BaseModel):
    mode: str
    query: str
    total: int
    results: List[SearchResult]


class EntityItem(BaseModel):
    entity_type: str
    value: str
    source_text: str
    confidence: float = Field(ge=0.0, le=1.0)


class RecordDetailResponse(BaseModel):
    record_id: str
    title: str
    metadata: Dict[str, str]
    original_text: str
    normalized_text: str
    entities: List[EntityItem]
    evidence: List[EvidenceItem]


class EntityResponse(BaseModel):
    record_id: str
    entities: List[EntityItem]


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


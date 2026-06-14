from fastapi import APIRouter, HTTPException, Query

from app.schemas import (
    GraphNeighborsResponse,
    GraphOverviewResponse,
    GraphPlaceFlowsResponse,
    GraphRecordResponse,
    GraphStatsResponse,
)
from app.services.graph_service import (
    get_graph_overview,
    get_graph_stats,
    get_node_neighbors,
    get_place_flows,
    get_record_graph,
)


router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/stats", response_model=GraphStatsResponse)
def graph_stats() -> GraphStatsResponse:
    return GraphStatsResponse(**get_graph_stats())


@router.get("/record/{record_id}", response_model=GraphRecordResponse)
def graph_record(record_id: str) -> GraphRecordResponse:
    graph = get_record_graph(record_id)
    if graph is None:
        raise HTTPException(status_code=404, detail=f"Graph record not found: {record_id}")
    return GraphRecordResponse(**graph)


@router.get("/node/{node_id}/neighbors", response_model=GraphNeighborsResponse)
def graph_node_neighbors(
    node_id: str,
    depth: int = Query(default=1, ge=1, le=2),
    limit: int = Query(default=50, ge=1, le=200),
) -> GraphNeighborsResponse:
    graph = get_node_neighbors(node_id, depth=depth, limit=limit)
    if graph is None:
        raise HTTPException(status_code=404, detail=f"Graph node not found: {node_id}")
    return GraphNeighborsResponse(**graph)


@router.get("/overview", response_model=GraphOverviewResponse)
def graph_overview(
    limit_nodes: int = Query(default=80, ge=1, le=200),
    limit_edges: int = Query(default=120, ge=1, le=300),
) -> GraphOverviewResponse:
    return GraphOverviewResponse(
        **get_graph_overview(limit_nodes=limit_nodes, limit_edges=limit_edges)
    )


@router.get("/flows/places", response_model=GraphPlaceFlowsResponse)
def graph_place_flows(
    limit: int = Query(default=50, ge=1, le=200),
) -> GraphPlaceFlowsResponse:
    return GraphPlaceFlowsResponse(**get_place_flows(limit=limit))

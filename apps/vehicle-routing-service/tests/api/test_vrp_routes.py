from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from vehicle_routing_service.presentation.api.app import app


def _arc(distance_m: int, time_min: int) -> dict:
    return {"distance_m": distance_m, "time_min": time_min, "mixed_cost": distance_m}


def _build_cost_matrix(size: int) -> list[list[dict]]:
    matrix: list[list[dict]] = []
    for i in range(size):
        row: list[dict] = []
        for j in range(size):
            if i == j:
                row.append(_arc(0, 0))
            else:
                row.append(_arc(1000, 10))
        matrix.append(row)
    return matrix


def _happy_path_payload() -> dict:
    """1 depot node + 2 service points, 1 vehicle starting/ending at the depot."""
    return {
        "nodes": {
            "0": {"identifier": "depot", "coord": [0.0, 0.0], "label": "Depot"},
            "1": {"identifier": "sp-1", "coord": [1.0, 0.0], "label": "Service Point 1"},
            "2": {"identifier": "sp-2", "coord": [2.0, 0.0], "label": "Service Point 2"},
        },
        "node_demand": [0, 1, 1],
        "number_of_service_points": 2,
        "service_point_service_time": [5, 5],
        "service_point_priorities": {"1": "medium", "2": "low"},
        "vehicle_start_nodes": [0],
        "vehicle_end_nodes": [0],
        "vehicle_capacities": [10],
        "time_window_start": "08:00",
        "time_window_end": "17:00",
        "time_window_crosses_midnight": False,
        "time_window_enabled": False,
        "prefer_earliest_departure": True,
        "departure_time_preference_penalty": 0,
        "max_vehicle_duration_min": 480,
        "include_first_leg_cost": [True],
        "include_first_leg_time": [True],
        "include_last_leg_cost": [True],
        "include_last_leg_time": [True],
        "cost_matrix": _build_cost_matrix(3),
        "routing_arc_cost_type": "DISTANCE_COST",
        "omission_penalty_base": 1000,
        "solver_search_time_limit_seconds": 2,
        "co2_kg_per_km": 0.1,
    }


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


async def test_solve_vrp_returns_a_feasible_solution_for_valid_input(client: AsyncClient) -> None:
    response = await client.post("/api/v1/vrp/solve", json=_happy_path_payload())

    assert response.status_code == 200
    body = response.json()

    assert body["status"] in {"OPTIMAL", "FEASIBLE"}
    assert body["total_service_points"] == 2
    assert len(body["solved_routes"]) == 1

    route = body["solved_routes"][0]
    assert route["vehicle_id"] == 0
    assert route["total_stops"] >= 2
    assert "stops" in route and isinstance(route["stops"], list)

    # OR-Tools internals must never leak through the API response.
    assert "manager" not in body
    assert "routing" not in body
    assert "time_dimension" not in body
    assert "solution" not in body


async def test_solve_vrp_rejects_mismatched_vehicle_start_end_nodes_with_problem_details(
    client: AsyncClient,
) -> None:
    payload = _happy_path_payload()
    # solve_vrp itself raises ValueError when start/end node counts differ.
    payload["vehicle_end_nodes"] = [0, 0]

    response = await client.post("/api/v1/vrp/solve", json=payload)

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")

    body = response.json()
    assert body["status"] == 422
    assert "title" in body
    assert "detail" in body
    assert "same length" in body["detail"]


async def test_solve_vrp_rejects_structurally_invalid_payload(client: AsyncClient) -> None:
    payload = _happy_path_payload()
    del payload["node_demand"]

    response = await client.post("/api/v1/vrp/solve", json=payload)

    assert response.status_code == 422


async def test_solve_vrp_rejects_non_contiguous_node_ids(client: AsyncClient) -> None:
    payload = _happy_path_payload()
    # Skips id "1", leaving a gap -- would desynchronize from cost_matrix/
    # vehicle_start_nodes, which still address nodes positionally by id.
    payload["nodes"] = {
        "0": {"identifier": "depot", "coord": [0.0, 0.0], "label": "Depot"},
        "2": {"identifier": "sp-2", "coord": [2.0, 0.0], "label": "Service Point 2"},
    }

    response = await client.post("/api/v1/vrp/solve", json=payload)

    assert response.status_code == 422

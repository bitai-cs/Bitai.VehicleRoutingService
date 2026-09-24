from __future__ import annotations

from fastapi import APIRouter, status

from vehicle_routing_service.application.vrp.solve_vrp_use_case import SolveVrpUseCase
from vehicle_routing_service.presentation.api.schemas.vrp import (
    SolveVrpRequest,
    SolveVrpResponse,
)

router = APIRouter()

_use_case = SolveVrpUseCase()


def get_solve_vrp_use_case() -> SolveVrpUseCase:
    """Composition point for the use case.

    The use case is stateless (it wraps a pure domain function), so a
    module-level singleton is returned rather than constructed per request.
    """
    return _use_case


@router.post(
    "/solve",
    response_model=SolveVrpResponse,
    status_code=status.HTTP_200_OK,
    summary="Solve a vehicle routing problem",
)
async def solve_vrp(request: SolveVrpRequest) -> SolveVrpResponse:
    """Solve a vehicle routing problem instance.

    A well-formed request that yields no feasible OR-Tools solution is not
    an error: the response is still HTTP 200, with empty `solved_routes` and
    populated `infeasibility_hints`. Structurally/logically invalid input
    (e.g. mismatched list lengths, an invalid time window) results in
    HTTP 422 with a problem-details body.
    """
    use_case = get_solve_vrp_use_case()
    command = request.to_command()
    result = await use_case.execute(command)
    return SolveVrpResponse.from_domain(result)

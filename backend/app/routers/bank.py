from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.deps import get_db
from app.models import Test
from app.schemas.coverage import CoverageOut
from app.schemas.stats import ProblemStatsOut
from app.services.coverage_service import compute_coverage
from app.services.lookup import get_or_404
from app.services.stats_service import compute_problem_stats

router = APIRouter(tags=["bank"])


@router.get("/tests/{test_id}/coverage", response_model=CoverageOut)
def get_coverage(
    test_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CoverageOut:
    test = get_or_404(db, Test, test_id, "テスト")
    return compute_coverage(db, test, settings.required_multiplier)


@router.get("/problems/stats", response_model=ProblemStatsOut)
def get_problem_stats(
    test_id: int | None = Query(default=None),
    round: int | None = Query(default=None),
    level: str | None = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ProblemStatsOut:
    return compute_problem_stats(db, settings, test_id=test_id, round_=round, level=level)

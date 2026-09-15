from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.deps import get_db
from app.models import Format, Test, TestTrend, Unit, User
from app.schemas.trend import TestTrendsOut, TrendItemOut, TrendPutRequest, UnitTrendSummary
from app.services.lookup import get_or_404

router = APIRouter(prefix="/tests", tags=["trends"])


def _build_out(test_id: int, db: Session) -> TestTrendsOut:
    rows = db.query(TestTrend).filter(TestTrend.test_id == test_id).order_by(TestTrend.id).all()

    unit_names = {u.id: u.name for u in db.query(Unit.id, Unit.name).all()}
    format_names = {f.id: f.name for f in db.query(Format.id, Format.name).all()}

    items = [
        TrendItemOut(
            id=r.id,
            test_id=r.test_id,
            unit_id=r.unit_id,
            unit_name=unit_names.get(r.unit_id) if r.unit_id else None,
            format_id=r.format_id,
            format_name=format_names.get(r.format_id, ""),
            question_no=r.question_no,
            points=r.points,
            difficulty=r.difficulty,
            source=r.source,
            llm_job_id=r.llm_job_id,
            reviewed=r.reviewed,
            reviewed_by=r.reviewed_by,
            reviewed_at=r.reviewed_at,
        )
        for r in rows
    ]

    reviewed_with_unit = [r for r in rows if r.reviewed and r.unit_id is not None]
    total_points = sum(r.points for r in reviewed_with_unit)

    summary_map: dict[int, dict] = {}
    for r in reviewed_with_unit:
        entry = summary_map.setdefault(r.unit_id, {"question_count": 0, "points": 0})
        entry["question_count"] += 1
        entry["points"] += r.points

    summary = [
        UnitTrendSummary(
            unit_id=unit_id,
            unit_name=unit_names.get(unit_id, ""),
            question_count=data["question_count"],
            point_ratio=(data["points"] / total_points) if total_points else 0.0,
        )
        for unit_id, data in summary_map.items()
    ]

    return TestTrendsOut(test_id=test_id, items=items, summary=summary)


@router.get("/{test_id}/trends", response_model=TestTrendsOut)
def get_trends(test_id: int, db: Session = Depends(get_db)) -> TestTrendsOut:
    get_or_404(db, Test, test_id, "テスト")
    return _build_out(test_id, db)


@router.put("/{test_id}/trends", response_model=TestTrendsOut)
def put_trends(test_id: int, payload: TrendPutRequest, db: Session = Depends(get_db)) -> TestTrendsOut:
    test = get_or_404(db, Test, test_id, "テスト")
    get_or_404(db, User, payload.user_id, "ユーザー")

    existing = {r.id: r for r in db.query(TestTrend).filter(TestTrend.test_id == test_id).all()}
    seen_ids: set[int] = set()
    now = datetime.now(UTC).replace(tzinfo=None)

    for item in payload.items:
        if item.unit_id is not None:
            unit = get_or_404(db, Unit, item.unit_id, "単元")
            if unit.textbook_id != test.textbook_id:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="このテストの教科書に属さない単元です",
                    status_code=400,
                )
        get_or_404(db, Format, item.format_id, "形式")

        if item.id is not None:
            row = existing.get(item.id)
            if row is None:
                raise AppError(
                    code="NOT_FOUND",
                    message=f"出題傾向 id={item.id} がこのテストに見つかりません",
                    status_code=404,
                )
            row.unit_id = item.unit_id
            row.format_id = item.format_id
            row.question_no = item.question_no
            row.points = item.points
            row.difficulty = item.difficulty
            row.source = item.source
            row.llm_job_id = item.llm_job_id
            row.reviewed = True
            row.reviewed_by = payload.user_id
            row.reviewed_at = now
            seen_ids.add(item.id)
        else:
            row = TestTrend(
                test_id=test_id,
                unit_id=item.unit_id,
                format_id=item.format_id,
                question_no=item.question_no,
                points=item.points,
                difficulty=item.difficulty,
                source=item.source,
                llm_job_id=item.llm_job_id,
                reviewed=True,
                reviewed_by=payload.user_id,
                reviewed_at=now,
            )
            db.add(row)

    for old_id, row in existing.items():
        if old_id not in seen_ids:
            db.delete(row)

    test.image_discarded_at = now

    db.commit()
    return _build_out(test_id, db)

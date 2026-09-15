from app.models import Attempt, WorksheetItem

RETURN_BLANK = "RETURN_BLANK"
CORRECT_WITH_RED_CARD = "CORRECT_WITH_RED_CARD"
RETURN_CORRECT_WITH_RED_CARD = "RETURN_CORRECT_WITH_RED_CARD"

_MESSAGES = {
    RETURN_BLANK: "戻り問題の結果が未入力です",
    CORRECT_WITH_RED_CARD: "正解なのに赤カードが立っています",
    RETURN_CORRECT_WITH_RED_CARD: "戻り問題に正解したのに赤カードが立っています",
}


def build_warnings(
    worksheet_items: list[WorksheetItem],
    attempts_by_item: dict[int, Attempt],
    submitted_item_ids: set[int],
) -> list[dict]:
    items_by_id = {wi.id: wi for wi in worksheet_items}
    children_by_parent: dict[int, list[WorksheetItem]] = {}
    for wi in worksheet_items:
        if wi.parent_item_id is not None:
            children_by_parent.setdefault(wi.parent_item_id, []).append(wi)

    warnings: list[dict] = []
    for item_id in submitted_item_ids:
        attempt = attempts_by_item.get(item_id)
        item = items_by_id.get(item_id)
        if attempt is None or item is None:
            continue

        if attempt.went_return:
            children = children_by_parent.get(item_id, [])
            if children and not any(c.id in attempts_by_item for c in children):
                warnings.append(_warning(item_id, RETURN_BLANK))

        if attempt.is_correct and attempt.red_card:
            code = RETURN_CORRECT_WITH_RED_CARD if item.is_return else CORRECT_WITH_RED_CARD
            warnings.append(_warning(item_id, code))

    return warnings


def _warning(worksheet_item_id: int, code: str) -> dict:
    return {"worksheet_item_id": worksheet_item_id, "code": code, "message": _MESSAGES[code]}

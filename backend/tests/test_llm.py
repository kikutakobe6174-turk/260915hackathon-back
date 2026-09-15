"""LLM endpoint tests. The google-genai SDK is always mocked here -- no network calls."""

from app.core.security import hash_password
from app.models import LlmJob, User


def _create_operator(db_session):
    user = User(
        login_id="operator1",
        password_hash=hash_password("password123"),
        name="運営 太郎",
        role="operator",
        active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _setup_textbook_units(client):
    textbook = client.post(
        "/textbooks", json={"publisher": "サンプル出版", "title": "新編数学1", "subject": "数学"}
    ).json()
    unit1 = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "一次方程式", "order_no": 1}).json()
    unit2 = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "文字と式", "order_no": 2}).json()
    fmt = client.post("/formats", json={"name": "計算"}).json()
    return textbook, unit1, unit2, fmt


def _mock_call_structured(monkeypatch, module_path: str, return_value):
    def _fake(settings, input_parts, json_schema, system_instruction=None):
        return return_value

    monkeypatch.setattr(f"{module_path}.call_structured", _fake)


def test_trend_draft_success_flags_low_confidence_unit(client, db_session, monkeypatch):
    operator = _create_operator(db_session)
    school = client.post("/schools", json={"name": "ひかり中学校"}).json()
    textbook, unit1, unit2, fmt = _setup_textbook_units(client)
    test = client.post(
        "/tests",
        json={
            "school_id": school["id"],
            "textbook_id": textbook["id"],
            "year": 2025,
            "grade": "中1",
            "term": "期末",
            "kind": "past",
            "unit_ids": [unit1["id"], unit2["id"]],
        },
    ).json()

    _mock_call_structured(
        monkeypatch,
        "app.llm.trend_draft",
        {
            "items": [
                {
                    "question_no": "1(1)",
                    "unit_id": unit1["id"],
                    "format_id": fmt["id"],
                    "points": 4,
                    "difficulty": 1,
                    "confidence": 0.9,
                },
                {
                    "question_no": "2",
                    "unit_id": 999999,  # not a valid unit -> should be nulled
                    "format_id": fmt["id"],
                    "points": 12,
                    "difficulty": 9,  # out of range -> clamped to 3
                    "confidence": 0.4,
                },
            ]
        },
    )

    res = client.post(
        "/llm/trend-draft",
        json={"test_id": test["id"], "user_id": operator.id, "image_base64": "ZmFrZQ==", "media_type": "image/jpeg"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["image_discarded"] is True
    assert len(body["items"]) == 2
    assert body["items"][0]["unit_id"] == unit1["id"]
    assert body["items"][1]["unit_id"] is None  # invalid id nulled -> 要確認
    assert body["items"][1]["difficulty"] == 3  # clamped

    job = db_session.query(LlmJob).filter(LlmJob.id == body["job_id"]).one()
    assert job.status == "done"
    assert job.kind == "trend"
    assert "image_base64" not in job.request_params
    assert "image" not in str(job.request_params).lower() or "image_base64" not in str(job.request_params)


def test_trend_draft_llm_failure_returns_502_and_records_failed_job(client, db_session, monkeypatch):
    operator = _create_operator(db_session)
    school = client.post("/schools", json={"name": "ひかり中学校"}).json()
    textbook, unit1, unit2, fmt = _setup_textbook_units(client)
    test = client.post(
        "/tests",
        json={
            "school_id": school["id"],
            "textbook_id": textbook["id"],
            "year": 2025,
            "grade": "中1",
            "term": "期末",
            "kind": "past",
            "unit_ids": [unit1["id"]],
        },
    ).json()

    def _raise(settings, input_parts, json_schema, system_instruction=None):
        from app.llm.client import LlmCallError

        raise LlmCallError("timeout")

    monkeypatch.setattr("app.llm.trend_draft.call_structured", _raise)

    res = client.post(
        "/llm/trend-draft",
        json={"test_id": test["id"], "user_id": operator.id, "image_base64": "ZmFrZQ==", "media_type": "image/jpeg"},
    )
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "LLM_ERROR"

    jobs = db_session.query(LlmJob).all()
    assert len(jobs) == 1
    assert jobs[0].status == "failed"
    assert jobs[0].error_message == "timeout"


def test_prereq_suggest_filters_invalid_and_self_reference(client, db_session, monkeypatch):
    operator = _create_operator(db_session)
    textbook, unit1, unit2, fmt = _setup_textbook_units(client)  # unit1 order 1, unit2 order 2

    _mock_call_structured(
        monkeypatch,
        "app.llm.prereq_suggest",
        {
            "suggestions": [
                {"prerequisite_unit_id": unit1["id"], "reason": "計算の基礎になる"},
                {"prerequisite_unit_id": 999999, "reason": "存在しない単元"},
            ]
        },
    )

    res = client.post("/llm/prereq-suggest", json={"unit_id": unit2["id"], "user_id": operator.id})
    assert res.status_code == 200
    body = res.json()
    assert len(body["suggestions"]) == 1
    assert body["suggestions"][0]["prerequisite_unit_id"] == unit1["id"]


def test_problem_draft_discards_drafts_without_exactly_three_hints(client, db_session, monkeypatch):
    operator = _create_operator(db_session)
    textbook, unit1, unit2, fmt = _setup_textbook_units(client)

    _mock_call_structured(
        monkeypatch,
        "app.llm.problem_draft",
        {
            "drafts": [
                {
                    "body": "問題1",
                    "answer": "答え1",
                    "explanation": "解説1",
                    "hints": [
                        {"step": 1, "body": "h1"},
                        {"step": 2, "body": "h2"},
                        {"step": 3, "body": "h3"},
                    ],
                },
                {
                    "body": "問題2（ヒント不足）",
                    "answer": "答え2",
                    "explanation": "解説2",
                    "hints": [{"step": 1, "body": "h1"}],
                },
            ]
        },
    )

    res = client.post(
        "/llm/problem-draft",
        json={
            "unit_id": unit1["id"],
            "format_id": fmt["id"],
            "difficulty": 2,
            "prerequisite_unit_ids": [unit2["id"]],
            "is_return": False,
            "count": 2,
            "user_id": operator.id,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["drafts"]) == 1
    assert body["drafts"][0]["body"] == "問題1"
    assert [h["step"] for h in body["drafts"][0]["hints"]] == [1, 2, 3]
    assert body["drafts"][0]["prerequisite_unit_ids"] == [unit2["id"]]


def test_sheet_draft_resolves_item_no_and_sets_llm_draft_status(client, db_session, monkeypatch):
    operator = _create_operator(db_session)
    school = client.post("/schools", json={"name": "ひかり中学校"}).json()
    textbook, unit1, unit2, fmt = _setup_textbook_units(client)
    test = client.post(
        "/tests",
        json={
            "school_id": school["id"],
            "textbook_id": textbook["id"],
            "year": 2025,
            "grade": "中1",
            "term": "期末",
            "kind": "target",
            "unit_ids": [unit1["id"]],
        },
    ).json()
    problem = client.post(
        "/problems",
        json={
            "unit_id": unit1["id"],
            "format_id": fmt["id"],
            "difficulty": 2,
            "body": "x",
            "answer": "y",
            "hints": ["1", "2", "3"],
        },
    ).json()
    client.post(f"/problems/{problem['id']}/review", json={"user_id": operator.id})
    worksheet = client.post(
        f"/tests/{test['id']}/worksheets",
        json={"level": "A", "items": [{"problem_id": problem["id"]}]},
    ).json()
    student = client.post(
        "/students", json={"student_code": "S0001", "school_id": school["id"], "grade": "中1", "level": "A"}
    ).json()
    lesson = client.post(
        "/lessons", json={"test_id": test["id"], "lesson_date": "2025-09-20", "class_name": "中1A", "round": 1}
    ).json()
    answer_sheet = client.post(
        f"/lessons/{lesson['id']}/answer-sheets",
        json={"assignments": [{"student_id": student["id"], "worksheet_id": worksheet["id"]}]},
    ).json()[0]
    item_no = worksheet["items"][0]["item_no"]
    worksheet_item_id = worksheet["items"][0]["id"]

    _mock_call_structured(
        monkeypatch,
        "app.llm.sheet_draft",
        {
            "rows": [
                {
                    "item_no": item_no,
                    "is_correct": False,
                    "hint_step": 9,  # out of range -> clamped to 3
                    "went_return": False,
                    "red_card": False,
                    "confidence": 0.7,
                },
                {
                    "item_no": "存在しない番号",
                    "is_correct": True,
                    "hint_step": 0,
                    "went_return": False,
                    "red_card": False,
                    "confidence": 0.3,
                },
            ]
        },
    )

    res = client.post(
        "/llm/sheet-draft",
        json={
            "answer_sheet_id": answer_sheet["id"],
            "user_id": operator.id,
            "image_base64": "ZmFrZQ==",
            "media_type": "image/jpeg",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["image_discarded"] is True
    assert len(body["rows"]) == 2
    assert body["rows"][0]["worksheet_item_id"] == worksheet_item_id
    assert body["rows"][0]["hint_step"] == 3
    assert body["rows"][1]["worksheet_item_id"] is None  # unmatched item_no -> 要確認

    detail = client.get(f"/answer-sheets/{answer_sheet['id']}").json()
    assert detail["status"] == "llm_draft"
    assert detail["source"] == "llm"

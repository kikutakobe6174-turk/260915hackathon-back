"""Tests for /llm/trend-problem-draft (問題作成：過去問の傾向から). google-genai is always mocked."""

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


def _setup_test_with_trend(client, operator_id):
    school = client.post("/schools", json={"name": "ひかり中学校"}).json()
    textbook = client.post(
        "/textbooks", json={"publisher": "サンプル出版", "title": "新編数学1", "subject": "数学"}
    ).json()
    unit1 = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "文字と式", "order_no": 1}).json()
    unit2 = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "一次方程式", "order_no": 2}).json()
    fmt_calc = client.post("/formats", json={"name": "計算"}).json()
    fmt_word = client.post("/formats", json={"name": "文章題"}).json()
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

    # 出題傾向を登録（PUTで reviewed=True になる）: unit2 に対して 計算2問・文章題1問
    client.put(
        f"/tests/{test['id']}/trends",
        json={
            "user_id": operator_id,
            "items": [
                {
                    "unit_id": unit2["id"],
                    "format_id": fmt_calc["id"],
                    "question_no": "1(1)",
                    "points": 4,
                    "difficulty": 1,
                    "source": "manual",
                },
                {
                    "unit_id": unit2["id"],
                    "format_id": fmt_calc["id"],
                    "question_no": "1(2)",
                    "points": 4,
                    "difficulty": 2,
                    "source": "manual",
                },
                {
                    "unit_id": unit2["id"],
                    "format_id": fmt_word["id"],
                    "question_no": "2",
                    "points": 8,
                    "difficulty": 3,
                    "source": "manual",
                },
            ],
        },
    )

    return test, unit1, unit2, fmt_calc, fmt_word


def _mock_call_structured(monkeypatch, return_value):
    def _fake(settings, input_parts, json_schema, system_instruction=None):
        return return_value

    monkeypatch.setattr("app.llm.trend_problem_draft.call_structured", _fake)


def test_trend_problem_draft_success_with_fallback_format(client, db_session, monkeypatch):
    operator = _create_operator(db_session)
    test, unit1, unit2, fmt_calc, fmt_word = _setup_test_with_trend(client, operator.id)

    _mock_call_structured(
        monkeypatch,
        {
            "drafts": [
                {
                    "test_id": test["id"],
                    "unit_id": unit2["id"],
                    "format_id": 999999,  # invalid -> should fall back to the trend's most common format
                    "difficulty": 9,  # out of range -> clamped to 3
                    "body": "3x + 2 = 11 を解け",
                    "answer": "x = 3",
                    "explanation": "両辺から2を引いて3で割る",
                    "hints": [
                        {"step": 1, "body": "まず移項しよう"},
                        {"step": 2, "body": "両辺から2を引く"},
                        {"step": 3, "body": "3x = 9 になる"},
                    ],
                    "prerequisite_unit_ids": [unit1["id"], 999999],
                }
            ]
        },
    )

    res = client.post(
        "/llm/trend-problem-draft",
        json={"user_id": operator.id, "targets": [{"test_id": test["id"], "unit_id": unit2["id"]}]},
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["drafts"]) == 1
    draft = body["drafts"][0]
    assert draft["test_id"] == test["id"]
    assert draft["unit_id"] == unit2["id"]
    assert draft["format_id"] == fmt_calc["id"]  # fallback to most common trend format
    assert draft["difficulty"] == 3  # clamped
    assert [h["step"] for h in draft["hints"]] == [1, 2, 3]
    assert draft["prerequisite_unit_ids"] == [unit1["id"]]  # invalid id filtered out

    job = db_session.query(LlmJob).filter(LlmJob.id == body["job_id"]).one()
    assert job.status == "done"
    assert job.kind == "trend_problem"


def test_trend_problem_draft_discards_drafts_without_exactly_three_hints(client, db_session, monkeypatch):
    operator = _create_operator(db_session)
    test, unit1, unit2, fmt_calc, fmt_word = _setup_test_with_trend(client, operator.id)

    _mock_call_structured(
        monkeypatch,
        {
            "drafts": [
                {
                    "test_id": test["id"],
                    "unit_id": unit2["id"],
                    "format_id": fmt_calc["id"],
                    "difficulty": 2,
                    "body": "問題（ヒント不足）",
                    "answer": "答え",
                    "explanation": "解説",
                    "hints": [{"step": 1, "body": "h1"}],
                    "prerequisite_unit_ids": [],
                }
            ]
        },
    )

    res = client.post(
        "/llm/trend-problem-draft",
        json={"user_id": operator.id, "targets": [{"test_id": test["id"], "unit_id": unit2["id"]}]},
    )
    assert res.status_code == 200
    assert res.json()["drafts"] == []


def test_trend_problem_draft_skips_target_without_trend_data_and_avoids_llm_call(client, db_session, monkeypatch):
    operator = _create_operator(db_session)
    test, unit1, unit2, fmt_calc, fmt_word = _setup_test_with_trend(client, operator.id)

    called = False

    def _fake(settings, input_parts, json_schema, system_instruction=None):
        nonlocal called
        called = True
        return {"drafts": []}

    monkeypatch.setattr("app.llm.trend_problem_draft.call_structured", _fake)

    # unit1 には出題傾向データを登録していない
    res = client.post(
        "/llm/trend-problem-draft",
        json={"user_id": operator.id, "targets": [{"test_id": test["id"], "unit_id": unit1["id"]}]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["drafts"] == []
    assert called is False  # no reviewed trend data -> LLM should not be called

    job = db_session.query(LlmJob).filter(LlmJob.id == body["job_id"]).one()
    assert job.status == "done"
    assert job.response_json == {"drafts": []}


def test_trend_problem_draft_rejects_unit_not_in_test_textbook(client, db_session, monkeypatch):
    operator = _create_operator(db_session)
    test, unit1, unit2, fmt_calc, fmt_word = _setup_test_with_trend(client, operator.id)

    other_textbook = client.post(
        "/textbooks", json={"publisher": "別出版", "title": "新編数学2", "subject": "数学"}
    ).json()
    other_unit = client.post(
        f"/textbooks/{other_textbook['id']}/units", json={"name": "連立方程式", "order_no": 1}
    ).json()

    res = client.post(
        "/llm/trend-problem-draft",
        json={"user_id": operator.id, "targets": [{"test_id": test["id"], "unit_id": other_unit["id"]}]},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_trend_problem_draft_llm_failure_returns_502_and_records_failed_job(client, db_session, monkeypatch):
    operator = _create_operator(db_session)
    test, unit1, unit2, fmt_calc, fmt_word = _setup_test_with_trend(client, operator.id)

    def _raise(settings, input_parts, json_schema, system_instruction=None):
        from app.llm.client import LlmCallError

        raise LlmCallError("timeout")

    monkeypatch.setattr("app.llm.trend_problem_draft.call_structured", _raise)

    res = client.post(
        "/llm/trend-problem-draft",
        json={"user_id": operator.id, "targets": [{"test_id": test["id"], "unit_id": unit2["id"]}]},
    )
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "LLM_ERROR"

    jobs = db_session.query(LlmJob).all()
    assert len(jobs) == 1
    assert jobs[0].status == "failed"
    assert jobs[0].kind == "trend_problem"

from app.core.security import hash_password
from app.models import User


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


def _setup(client, operator_id):
    school = client.post("/schools", json={"name": "ひかり中学校"}).json()
    textbook = client.post(
        "/textbooks", json={"publisher": "サンプル出版", "title": "新編数学1", "subject": "数学"}
    ).json()
    unit1 = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "一次方程式", "order_no": 1}).json()
    unit2 = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "文字と式", "order_no": 2}).json()
    fmt = client.post("/formats", json={"name": "計算"}).json()
    test = client.post(
        "/tests",
        json={
            "school_id": school["id"],
            "textbook_id": textbook["id"],
            "year": 2025,
            "grade": "中1",
            "term": "期末",
            "kind": "target",
            "unit_ids": [unit1["id"], unit2["id"]],
        },
    ).json()

    def reviewed_problem(unit_id, is_return=False):
        p = client.post(
            "/problems",
            json={
                "unit_id": unit_id,
                "format_id": fmt["id"],
                "difficulty": 2,
                "body": "x",
                "answer": "y",
                "hints": ["1", "2", "3"],
                "is_return": is_return,
            },
        ).json()
        client.post(f"/problems/{p['id']}/review", json={"user_id": operator_id})
        return p

    main_problem = reviewed_problem(unit1["id"])
    return_problem = reviewed_problem(unit2["id"], is_return=True)

    worksheet = client.post(
        f"/tests/{test['id']}/worksheets",
        json={
            "level": "A",
            "items": [
                {"problem_id": main_problem["id"]},
                {"problem_id": return_problem["id"], "is_return": True, "parent_index": 0},
            ],
        },
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

    main_item_id = worksheet["items"][0]["id"]
    return_item_id = worksheet["items"][1]["id"]
    return school, test, worksheet, student, lesson, answer_sheet, main_item_id, return_item_id


def test_get_answer_sheet_detail_initial(client, db_session):
    operator = _create_operator(db_session)
    _, _, _, _, _, answer_sheet, main_item_id, return_item_id = _setup(client, operator.id)

    res = client.get(f"/answer-sheets/{answer_sheet['id']}")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "empty"
    assert body["round"] == 1
    assert len(body["items"]) == 2
    assert all(i["attempt"] is None for i in body["items"])


def test_put_attempts_sets_in_progress_and_round_from_lesson(client, db_session):
    operator = _create_operator(db_session)
    _, _, _, _, _, answer_sheet, main_item_id, return_item_id = _setup(client, operator.id)

    res = client.put(
        f"/answer-sheets/{answer_sheet['id']}/attempts",
        json={
            "attempts": [
                {"worksheet_item_id": main_item_id, "is_correct": True, "hint_step": 1},
            ]
        },
    )
    assert res.status_code == 200
    assert res.json()["saved"] == 1
    assert res.json()["warnings"] == []

    detail = client.get(f"/answer-sheets/{answer_sheet['id']}").json()
    assert detail["status"] == "in_progress"
    item = next(i for i in detail["items"] if i["worksheet_item_id"] == main_item_id)
    assert item["attempt"]["is_correct"] is True


def test_return_blank_warning(client, db_session):
    operator = _create_operator(db_session)
    _, _, _, _, _, answer_sheet, main_item_id, return_item_id = _setup(client, operator.id)

    res = client.put(
        f"/answer-sheets/{answer_sheet['id']}/attempts",
        json={
            "attempts": [
                {
                    "worksheet_item_id": main_item_id,
                    "is_correct": False,
                    "hint_step": 3,
                    "went_return": True,
                }
            ]
        },
    )
    warnings = res.json()["warnings"]
    assert len(warnings) == 1
    assert warnings[0]["code"] == "RETURN_BLANK"
    assert warnings[0]["worksheet_item_id"] == main_item_id


def test_return_blank_warning_clears_once_return_item_saved(client, db_session):
    operator = _create_operator(db_session)
    _, _, _, _, _, answer_sheet, main_item_id, return_item_id = _setup(client, operator.id)

    client.put(
        f"/answer-sheets/{answer_sheet['id']}/attempts",
        json={
            "attempts": [
                {"worksheet_item_id": main_item_id, "is_correct": False, "hint_step": 3, "went_return": True}
            ]
        },
    )
    res = client.put(
        f"/answer-sheets/{answer_sheet['id']}/attempts",
        json={"attempts": [{"worksheet_item_id": return_item_id, "is_correct": True, "hint_step": 0}]},
    )
    assert res.json()["warnings"] == []


def test_correct_with_red_card_warnings(client, db_session):
    operator = _create_operator(db_session)
    _, _, _, _, _, answer_sheet, main_item_id, return_item_id = _setup(client, operator.id)

    res = client.put(
        f"/answer-sheets/{answer_sheet['id']}/attempts",
        json={
            "attempts": [
                {"worksheet_item_id": main_item_id, "is_correct": True, "hint_step": 0, "red_card": True},
                {"worksheet_item_id": return_item_id, "is_correct": True, "hint_step": 0, "red_card": True},
            ]
        },
    )
    warnings = {w["worksheet_item_id"]: w["code"] for w in res.json()["warnings"]}
    assert warnings[main_item_id] == "CORRECT_WITH_RED_CARD"
    assert warnings[return_item_id] == "RETURN_CORRECT_WITH_RED_CARD"


def test_put_attempts_rejects_item_from_other_worksheet(client, db_session):
    operator = _create_operator(db_session)
    _, _, _, _, _, answer_sheet, _, _ = _setup(client, operator.id)

    res = client.put(
        f"/answer-sheets/{answer_sheet['id']}/attempts",
        json={"attempts": [{"worksheet_item_id": 99999, "is_correct": True, "hint_step": 0}]},
    )
    assert res.status_code == 400


def test_confirm_flow_and_lock(client, db_session):
    operator = _create_operator(db_session)
    _, _, _, _, lesson, answer_sheet, main_item_id, return_item_id = _setup(client, operator.id)

    client.put(
        f"/answer-sheets/{answer_sheet['id']}/attempts",
        json={"attempts": [{"worksheet_item_id": main_item_id, "is_correct": True, "hint_step": 0}]},
    )

    res = client.post(f"/answer-sheets/{answer_sheet['id']}/confirm", json={"user_id": operator.id})
    assert res.status_code == 200
    body = res.json()
    assert body["answer_sheet"]["status"] == "confirmed"
    assert body["answer_sheet"]["confirmed_by"] == operator.id
    assert body["next_answer_sheet_id"] is None  # only sheet in this lesson

    # editing after confirm should be rejected
    res = client.put(
        f"/answer-sheets/{answer_sheet['id']}/attempts",
        json={"attempts": [{"worksheet_item_id": main_item_id, "is_correct": False, "hint_step": 1}]},
    )
    assert res.status_code == 409


def test_confirm_returns_next_unconfirmed_sheet(client, db_session):
    operator = _create_operator(db_session)
    school, test, worksheet, student, lesson, answer_sheet, main_item_id, _ = _setup(client, operator.id)

    student2 = client.post(
        "/students", json={"student_code": "S0002", "school_id": school["id"], "grade": "中1", "level": "A"}
    ).json()
    sheets = client.post(
        f"/lessons/{lesson['id']}/answer-sheets",
        json={"assignments": [{"student_id": student2["id"], "worksheet_id": worksheet["id"]}]},
    ).json()
    other_sheet_id = next(s["id"] for s in sheets if s["student_id"] == student2["id"])

    res = client.post(f"/answer-sheets/{answer_sheet['id']}/confirm", json={"user_id": operator.id})
    assert res.json()["next_answer_sheet_id"] == other_sheet_id

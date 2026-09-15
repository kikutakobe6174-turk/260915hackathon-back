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


def _setup_test_with_worksheet(client, operator_id):
    school = client.post("/schools", json={"name": "ひかり中学校"}).json()
    textbook = client.post(
        "/textbooks", json={"publisher": "サンプル出版", "title": "新編数学1", "subject": "数学"}
    ).json()
    unit1 = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "一次方程式", "order_no": 1}).json()
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
    client.post(f"/problems/{problem['id']}/review", json={"user_id": operator_id})
    worksheet = client.post(
        f"/tests/{test['id']}/worksheets",
        json={"level": "A", "items": [{"problem_id": problem["id"]}]},
    ).json()
    student1 = client.post(
        "/students", json={"student_code": "S0001", "school_id": school["id"], "grade": "中1", "level": "A"}
    ).json()
    student2 = client.post(
        "/students", json={"student_code": "S0002", "school_id": school["id"], "grade": "中1", "level": "A"}
    ).json()
    return school, test, worksheet, student1, student2


def test_create_lesson(client, db_session):
    operator = _create_operator(db_session)
    school, test, worksheet, student1, student2 = _setup_test_with_worksheet(client, operator.id)

    res = client.post(
        "/lessons", json={"test_id": test["id"], "lesson_date": "2025-09-20", "class_name": "中1A", "round": 1}
    )
    assert res.status_code == 201
    lesson = res.json()
    assert lesson["round"] == 1

    res = client.get("/lessons", params={"test_id": test["id"]})
    assert len(res.json()) == 1


def test_create_answer_sheets_assigns_and_skips_duplicates(client, db_session):
    operator = _create_operator(db_session)
    school, test, worksheet, student1, student2 = _setup_test_with_worksheet(client, operator.id)
    lesson = client.post(
        "/lessons", json={"test_id": test["id"], "lesson_date": "2025-09-20", "class_name": "中1A", "round": 1}
    ).json()

    res = client.post(
        f"/lessons/{lesson['id']}/answer-sheets",
        json={
            "assignments": [
                {"student_id": student1["id"], "worksheet_id": worksheet["id"]},
                {"student_id": student2["id"], "worksheet_id": worksheet["id"]},
            ]
        },
    )
    assert res.status_code == 201
    sheets = res.json()
    assert len(sheets) == 2
    assert all(s["status"] == "empty" for s in sheets)
    assert {s["student_code"] for s in sheets} == {"S0001", "S0002"}
    assert sheets[0]["school_name"] == "ひかり中学校"

    # re-assigning the same student should not create a duplicate
    res = client.post(
        f"/lessons/{lesson['id']}/answer-sheets",
        json={"assignments": [{"student_id": student1["id"], "worksheet_id": worksheet["id"]}]},
    )
    assert res.status_code == 201
    assert len(res.json()) == 2

    res = client.get(f"/lessons/{lesson['id']}/answer-sheets")
    assert len(res.json()) == 2

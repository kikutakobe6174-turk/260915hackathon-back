from datetime import date

from app.core.security import hash_password
from app.models import AnswerSheet, Attempt, Lesson, School, Student, User


def _setup(client, db_session):
    if not db_session.query(User).first():
        operator = User(
            login_id="operator1",
            password_hash=hash_password("x"),
            name="op",
            role="operator",
            active=True,
        )
        db_session.add(operator)
        db_session.commit()

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

    def make_reviewed_problem(unit_id, is_return=False):
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
        client.post(f"/problems/{p['id']}/review", json={"user_id": 1})
        return p

    return school, test, unit1, unit2, make_reviewed_problem


def test_create_worksheet_assigns_item_numbers(client, db_session):
    school, test, unit1, unit2, make_problem = _setup(client, db_session)
    main_problem = make_problem(unit1["id"])
    return_problem = make_problem(unit2["id"], is_return=True)

    res = client.post(
        f"/tests/{test['id']}/worksheets",
        json={
            "level": "B",
            "items": [
                {"problem_id": main_problem["id"], "is_return": False},
                {"problem_id": return_problem["id"], "is_return": True, "parent_index": 0},
            ],
        },
    )
    assert res.status_code == 201
    worksheet = res.json()
    assert worksheet["version"] == 1
    assert worksheet["locked"] is False
    assert [i["item_no"] for i in worksheet["items"]] == ["1", "R-1"]
    assert worksheet["items"][1]["parent_item_id"] == worksheet["items"][0]["id"]


def test_worksheet_rejects_draft_problem(client, db_session):
    school, test, unit1, unit2, _ = _setup(client, db_session)
    draft_problem = client.post(
        "/problems",
        json={
            "unit_id": unit1["id"],
            "format_id": 1,
            "difficulty": 2,
            "body": "x",
            "answer": "y",
            "hints": ["1", "2", "3"],
        },
    ).json()

    res = client.post(
        f"/tests/{test['id']}/worksheets",
        json={"level": "A", "items": [{"problem_id": draft_problem["id"]}]},
    )
    assert res.status_code == 400


def test_worksheet_lock_after_attempt_and_new_version_on_recreate(client, db_session):
    school, test, unit1, unit2, make_problem = _setup(client, db_session)
    problem = make_problem(unit1["id"])

    worksheet = client.post(
        f"/tests/{test['id']}/worksheets",
        json={"level": "A", "items": [{"problem_id": problem["id"]}]},
    ).json()

    # record an attempt directly against the worksheet item to simulate a lesson being run
    school_row = db_session.query(School).first()
    student = Student(student_code="S9001", school_id=school_row.id, grade="中1", level="A", active=True)
    db_session.add(student)
    db_session.flush()

    lesson = Lesson(test_id=test["id"], lesson_date=date.today(), class_name="A組", round=1)
    db_session.add(lesson)
    db_session.flush()

    answer_sheet = AnswerSheet(
        student_id=student.id, lesson_id=lesson.id, worksheet_id=worksheet["id"], status="confirmed"
    )
    db_session.add(answer_sheet)
    db_session.flush()

    attempt = Attempt(
        answer_sheet_id=answer_sheet.id,
        worksheet_item_id=worksheet["items"][0]["id"],
        round=1,
        is_correct=True,
        hint_step=0,
    )
    db_session.add(attempt)
    db_session.commit()

    res = client.get(f"/worksheets/{worksheet['id']}")
    assert res.json()["locked"] is True

    res = client.put(
        f"/worksheets/{worksheet['id']}",
        json={"level": "A", "items": [{"problem_id": problem["id"]}]},
    )
    assert res.status_code == 409

    # creating again should bump the version instead
    res = client.post(
        f"/tests/{test['id']}/worksheets",
        json={"level": "A", "items": [{"problem_id": problem["id"]}]},
    )
    assert res.status_code == 201
    assert res.json()["version"] == 2

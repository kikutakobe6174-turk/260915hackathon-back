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


def _setup(client):
    school = client.post("/schools", json={"name": "ひかり中学校"}).json()
    textbook = client.post(
        "/textbooks", json={"publisher": "サンプル出版", "title": "新編数学1", "subject": "数学"}
    ).json()
    unit1 = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "一次方程式", "order_no": 1}).json()
    fmt = client.post("/formats", json={"name": "計算"}).json()
    return school, textbook, unit1, fmt


def test_coverage_required_count_from_past_tests(client, db_session):
    operator = _create_operator(db_session)
    school, textbook, unit1, fmt = _setup(client)

    # two past tests, each with 2 reviewed trend rows at unit1/fmt/difficulty=1
    for _ in range(2):
        past = client.post(
            "/tests",
            json={
                "school_id": school["id"],
                "textbook_id": textbook["id"],
                "year": 2024,
                "grade": "中1",
                "term": "期末",
                "kind": "past",
                "unit_ids": [unit1["id"]],
            },
        ).json()
        client.put(
            f"/tests/{past['id']}/trends",
            json={
                "user_id": operator.id,
                "items": [
                    {
                        "unit_id": unit1["id"],
                        "format_id": fmt["id"],
                        "question_no": "1",
                        "points": 4,
                        "difficulty": 1,
                    },
                    {
                        "unit_id": unit1["id"],
                        "format_id": fmt["id"],
                        "question_no": "2",
                        "points": 4,
                        "difficulty": 1,
                    },
                ],
            },
        )

    target = client.post(
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

    res = client.get(f"/tests/{target['id']}/coverage")
    assert res.status_code == 200
    body = res.json()
    assert body["multiplier"] == 3

    cell = next(
        c for c in body["cells"] if c["unit_id"] == unit1["id"] and c["format_id"] == fmt["id"] and c["difficulty"] == 1
    )
    # avg 2 per past test * multiplier 3 = required 6
    assert cell["required"] == 6
    assert cell["reviewed"] == 0
    assert cell["draft"] == 0


def test_coverage_counts_reviewed_and_draft_problems(client, db_session):
    operator = _create_operator(db_session)
    school, textbook, unit1, fmt = _setup(client)

    target = client.post(
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

    problem_payload = {
        "unit_id": unit1["id"],
        "format_id": fmt["id"],
        "difficulty": 2,
        "body": "x",
        "answer": "y",
        "hints": ["1", "2", "3"],
    }
    p1 = client.post("/problems", json=problem_payload).json()
    client.post("/problems", json=problem_payload)  # stays draft
    client.post(f"/problems/{p1['id']}/review", json={"user_id": operator.id})

    res = client.get(f"/tests/{target['id']}/coverage")
    cell = next(
        c for c in res.json()["cells"] if c["unit_id"] == unit1["id"] and c["difficulty"] == 2
    )
    assert cell["reviewed"] == 1
    assert cell["draft"] == 1


def test_stats_empty_without_attempts(client):
    res = client.get("/problems/stats")
    assert res.status_code == 200
    assert res.json()["items"] == []

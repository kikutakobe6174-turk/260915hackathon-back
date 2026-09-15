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
    unit1 = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "正負の数", "order_no": 1}).json()
    unit2 = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "文字と式", "order_no": 2}).json()
    fmt = client.post("/formats", json={"name": "計算"}).json()
    test = client.post(
        "/tests",
        json={
            "school_id": school["id"],
            "textbook_id": textbook["id"],
            "year": 2025,
            "grade": "中1",
            "term": "1学期期末",
            "kind": "past",
            "unit_ids": [unit1["id"], unit2["id"]],
        },
    ).json()
    return school, textbook, unit1, unit2, fmt, test


def test_trends_empty_initially(client, db_session):
    _create_operator(db_session)
    _, _, _, _, _, test = _setup(client)

    res = client.get(f"/tests/{test['id']}/trends")
    assert res.status_code == 200
    body = res.json()
    assert body["items"] == []
    assert body["summary"] == []


def test_put_trends_creates_updates_and_deletes(client, db_session):
    operator = _create_operator(db_session)
    _, _, unit1, unit2, fmt, test = _setup(client)

    res = client.put(
        f"/tests/{test['id']}/trends",
        json={
            "user_id": operator.id,
            "items": [
                {
                    "unit_id": unit1["id"],
                    "format_id": fmt["id"],
                    "question_no": "1(1)",
                    "points": 4,
                    "difficulty": 1,
                },
                {
                    "unit_id": unit2["id"],
                    "format_id": fmt["id"],
                    "question_no": "1(2)",
                    "points": 6,
                    "difficulty": 2,
                },
            ],
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) == 2
    for item in body["items"]:
        assert item["reviewed"] is True
        assert item["reviewed_by"] == operator.id

    # unit1: 4pt, unit2: 6pt => ratios 0.4 / 0.6
    ratios = {s["unit_id"]: s["point_ratio"] for s in body["summary"]}
    assert round(ratios[unit1["id"]], 2) == 0.4
    assert round(ratios[unit2["id"]], 2) == 0.6

    # test image should be marked discarded
    test_detail = client.get(f"/tests/{test['id']}").json()
    assert test_detail["image_discarded_at"] is not None

    item1_id = body["items"][0]["id"]
    # second PUT: update item1, drop item2, add a new item with unit_id null (要確認)
    res2 = client.put(
        f"/tests/{test['id']}/trends",
        json={
            "user_id": operator.id,
            "items": [
                {
                    "id": item1_id,
                    "unit_id": unit1["id"],
                    "format_id": fmt["id"],
                    "question_no": "1(1)改",
                    "points": 5,
                    "difficulty": 2,
                },
                {
                    "unit_id": None,
                    "format_id": fmt["id"],
                    "question_no": "2",
                    "points": 10,
                    "difficulty": 3,
                    "source": "llm",
                },
            ],
        },
    )
    assert res2.status_code == 200
    body2 = res2.json()
    assert len(body2["items"]) == 2
    qnos = {i["question_no"] for i in body2["items"]}
    assert qnos == {"1(1)改", "2"}
    # null-unit item excluded from summary
    assert len(body2["summary"]) == 1


def test_put_trends_rejects_unit_from_other_textbook(client, db_session):
    operator = _create_operator(db_session)
    _, _, unit1, _, fmt, test = _setup(client)

    other_textbook = client.post(
        "/textbooks", json={"publisher": "他社", "title": "他教科書", "subject": "数学"}
    ).json()
    other_unit = client.post(
        f"/textbooks/{other_textbook['id']}/units", json={"name": "他単元", "order_no": 1}
    ).json()

    res = client.put(
        f"/tests/{test['id']}/trends",
        json={
            "user_id": operator.id,
            "items": [
                {
                    "unit_id": other_unit["id"],
                    "format_id": fmt["id"],
                    "question_no": "1",
                    "points": 4,
                    "difficulty": 1,
                }
            ],
        },
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_put_trends_rejects_invalid_difficulty(client, db_session):
    operator = _create_operator(db_session)
    _, _, unit1, _, fmt, test = _setup(client)

    res = client.put(
        f"/tests/{test['id']}/trends",
        json={
            "user_id": operator.id,
            "items": [
                {
                    "unit_id": unit1["id"],
                    "format_id": fmt["id"],
                    "question_no": "1",
                    "points": 4,
                    "difficulty": 5,
                }
            ],
        },
    )
    assert res.status_code == 422

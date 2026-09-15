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


def _setup_units(client):
    textbook = client.post(
        "/textbooks", json={"publisher": "サンプル出版", "title": "新編数学1", "subject": "数学"}
    ).json()
    unit1 = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "一次方程式", "order_no": 1}).json()
    unit2 = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "文字と式", "order_no": 2}).json()
    fmt = client.post("/formats", json={"name": "計算"}).json()
    return unit1, unit2, fmt


def _problem_payload(unit_id, fmt_id, prereq_ids=None, is_return=False):
    return {
        "unit_id": unit_id,
        "format_id": fmt_id,
        "difficulty": 2,
        "body": r"$3x-5=2x+7$ を解け。",
        "answer": "x=12",
        "explanation": "移項して計算する。",
        "is_return": is_return,
        "hints": ["文字の項を左辺に集める", "数の項を右辺に集める", "計算して答えを出す"],
        "prerequisite_unit_ids": prereq_ids or [],
    }


def test_create_problem_requires_exactly_three_hints(client):
    unit1, _, fmt = _setup_units(client)
    payload = _problem_payload(unit1["id"], fmt["id"])
    payload["hints"] = ["only one hint"]

    res = client.post("/problems", json=payload)
    assert res.status_code == 422


def test_problem_crud_and_review(client, db_session):
    operator = _create_operator(db_session)
    unit1, unit2, fmt = _setup_units(client)

    res = client.post("/problems", json=_problem_payload(unit1["id"], fmt["id"], prereq_ids=[unit2["id"]]))
    assert res.status_code == 201
    problem = res.json()
    assert problem["status"] == "draft"
    assert len(problem["hints"]) == 3
    assert problem["hints"][0]["step"] == 1
    assert problem["prerequisite_unit_ids"] == [unit2["id"]]
    # no reviewed return-problem exists yet for unit2 -> should be flagged
    assert problem["prerequisites_missing_return"] == [unit2["id"]]

    res = client.get(f"/problems/{problem['id']}")
    assert res.status_code == 200

    updated_payload = _problem_payload(unit1["id"], fmt["id"], prereq_ids=[unit2["id"]])
    updated_payload["body"] = "更新後の問題文"
    res = client.put(f"/problems/{problem['id']}", json=updated_payload)
    assert res.status_code == 200
    assert res.json()["body"] == "更新後の問題文"

    res = client.post(f"/problems/{problem['id']}/review", json={"user_id": operator.id})
    assert res.status_code == 200
    reviewed = res.json()
    assert reviewed["status"] == "reviewed"
    assert reviewed["reviewed_by"] == operator.id


def test_missing_return_problem_flag_clears_once_return_problem_reviewed(client, db_session):
    operator = _create_operator(db_session)
    unit1, unit2, fmt = _setup_units(client)

    # create + review a return problem for unit2
    return_problem = client.post(
        "/problems", json=_problem_payload(unit2["id"], fmt["id"], is_return=True)
    ).json()
    client.post(f"/problems/{return_problem['id']}/review", json={"user_id": operator.id})

    res = client.post("/problems", json=_problem_payload(unit1["id"], fmt["id"], prereq_ids=[unit2["id"]]))
    assert res.json()["prerequisites_missing_return"] == []


def test_list_problems_filters(client):
    unit1, unit2, fmt = _setup_units(client)
    client.post("/problems", json=_problem_payload(unit1["id"], fmt["id"]))
    client.post("/problems", json=_problem_payload(unit2["id"], fmt["id"]))

    res = client.get("/problems", params={"unit_id": unit1["id"]})
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["unit_id"] == unit1["id"]

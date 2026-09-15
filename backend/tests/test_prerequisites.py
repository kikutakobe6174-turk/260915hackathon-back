from app.core.security import hash_password
from app.models import User


def _create_users(db_session):
    operator = User(
        login_id="operator1",
        password_hash=hash_password("password123"),
        name="運営 太郎",
        role="operator",
        active=True,
    )
    teacher = User(
        login_id="teacher1",
        password_hash=hash_password("password123"),
        name="先生 花子",
        role="teacher",
        active=True,
    )
    db_session.add_all([operator, teacher])
    db_session.commit()
    db_session.refresh(operator)
    db_session.refresh(teacher)
    return operator, teacher


def _setup(client):
    school = client.post("/schools", json={"name": "ひかり中学校"}).json()
    textbook = client.post(
        "/textbooks", json={"publisher": "サンプル出版", "title": "新編数学1", "subject": "数学"}
    ).json()
    unit1 = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "平方完成", "order_no": 1}).json()
    unit2 = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "二次関数", "order_no": 2}).json()
    test = client.post(
        "/tests",
        json={
            "school_id": school["id"],
            "textbook_id": textbook["id"],
            "year": 2025,
            "grade": "中3",
            "term": "1学期期末",
            "kind": "target",
            "unit_ids": [unit1["id"], unit2["id"]],
        },
    ).json()
    return unit1, unit2, test


def test_prerequisites_empty_initially(client, db_session):
    _create_users(db_session)
    unit1, unit2, test = _setup(client)

    res = client.get(f"/tests/{test['id']}/prerequisites")
    assert res.status_code == 200
    body = res.json()
    assert len(body["units"]) == 2
    for group in body["units"]:
        assert group["confirmed"] is False
        assert group["prerequisites"] == []


def test_put_and_review_prerequisite_flow(client, db_session):
    operator, teacher = _create_users(db_session)
    unit1, unit2, test = _setup(client)

    res = client.put(
        f"/units/{unit2['id']}/prerequisites",
        json={
            "user_id": operator.id,
            "items": [{"prerequisite_unit_id": unit1["id"], "reason": "頂点を求めるのに必要"}],
        },
    )
    assert res.status_code == 200
    prereqs = res.json()
    assert len(prereqs) == 1
    assert prereqs[0]["confirmed"] is False

    res = client.get(f"/tests/{test['id']}/prerequisites")
    group_for_unit2 = next(g for g in res.json()["units"] if g["unit_id"] == unit2["id"])
    assert group_for_unit2["confirmed"] is False
    assert group_for_unit2["prerequisites"][0]["prerequisite_unit_name"] == "平方完成"

    # teacher confirms with a comment
    res = client.post(
        f"/units/{unit2['id']}/prerequisites/{unit1['id']}/review",
        json={"user_id": teacher.id, "confirmed": True, "teacher_note": "生徒はここで詰まりやすい"},
    )
    assert res.status_code == 200
    reviewed = res.json()
    assert reviewed["confirmed"] is True
    assert reviewed["reviewed_by"] == teacher.id
    assert reviewed["teacher_note"] == "生徒はここで詰まりやすい"

    res = client.get(f"/tests/{test['id']}/prerequisites")
    group_for_unit2 = next(g for g in res.json()["units"] if g["unit_id"] == unit2["id"])
    assert group_for_unit2["confirmed"] is True


def test_put_prerequisites_self_reference_rejected(client, db_session):
    operator, _ = _create_users(db_session)
    unit1, unit2, test = _setup(client)

    res = client.put(
        f"/units/{unit2['id']}/prerequisites",
        json={"user_id": operator.id, "items": [{"prerequisite_unit_id": unit2["id"]}]},
    )
    assert res.status_code == 400


def test_put_prerequisites_full_sync_removes_missing(client, db_session):
    operator, _ = _create_users(db_session)
    unit1, unit2, test = _setup(client)

    client.put(
        f"/units/{unit2['id']}/prerequisites",
        json={"user_id": operator.id, "items": [{"prerequisite_unit_id": unit1["id"]}]},
    )
    res = client.put(f"/units/{unit2['id']}/prerequisites", json={"user_id": operator.id, "items": []})
    assert res.status_code == 200
    assert res.json() == []

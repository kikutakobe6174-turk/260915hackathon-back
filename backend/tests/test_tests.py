def _setup_school_textbook_units(client):
    school = client.post("/schools", json={"name": "ひかり中学校"}).json()
    textbook = client.post(
        "/textbooks", json={"publisher": "サンプル出版", "title": "新編数学1", "subject": "数学"}
    ).json()
    unit1 = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "正負の数", "order_no": 1}).json()
    unit2 = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "文字と式", "order_no": 2}).json()
    return school, textbook, unit1, unit2


def test_create_test_with_scope(client):
    school, textbook, unit1, unit2 = _setup_school_textbook_units(client)

    res = client.post(
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
    )
    assert res.status_code == 201
    test = res.json()
    assert test["kind"] == "past"
    assert sorted(test["unit_ids"]) == sorted([unit1["id"], unit2["id"]])
    assert test["image_discarded_at"] is None

    res = client.get(f"/tests/{test['id']}")
    assert res.status_code == 200
    assert res.json()["id"] == test["id"]

    res = client.get("/tests", params={"school_id": school["id"], "kind": "past"})
    assert len(res.json()) == 1


def test_create_test_invalid_kind_rejected(client):
    school, textbook, _, _ = _setup_school_textbook_units(client)
    res = client.post(
        "/tests",
        json={
            "school_id": school["id"],
            "textbook_id": textbook["id"],
            "year": 2025,
            "grade": "中1",
            "term": "1学期期末",
            "kind": "invalid",
        },
    )
    assert res.status_code == 422


def test_create_test_unit_from_other_textbook_rejected(client):
    school, textbook, unit1, _ = _setup_school_textbook_units(client)
    other_textbook = client.post(
        "/textbooks", json={"publisher": "他社", "title": "他教科書", "subject": "数学"}
    ).json()
    other_unit = client.post(
        f"/textbooks/{other_textbook['id']}/units", json={"name": "他単元", "order_no": 1}
    ).json()

    res = client.post(
        "/tests",
        json={
            "school_id": school["id"],
            "textbook_id": textbook["id"],
            "year": 2025,
            "grade": "中1",
            "term": "1学期期末",
            "kind": "past",
            "unit_ids": [unit1["id"], other_unit["id"]],
        },
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_test_missing_school_404(client):
    res = client.post(
        "/tests",
        json={
            "school_id": 999,
            "textbook_id": 1,
            "year": 2025,
            "grade": "中1",
            "term": "1学期期末",
            "kind": "past",
        },
    )
    assert res.status_code == 404

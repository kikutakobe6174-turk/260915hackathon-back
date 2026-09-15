def test_school_crud(client):
    res = client.post("/schools", json={"name": "ひかり中学校"})
    assert res.status_code == 201
    school = res.json()
    assert school["name"] == "ひかり中学校"

    res = client.get("/schools")
    assert res.status_code == 200
    assert len(res.json()) == 1

    res = client.put(f"/schools/{school['id']}", json={"name": "ひかり第二中学校"})
    assert res.status_code == 200
    assert res.json()["name"] == "ひかり第二中学校"

    res = client.delete(f"/schools/{school['id']}")
    assert res.status_code == 204
    assert client.get("/schools").json() == []


def test_school_update_404(client):
    res = client.put("/schools/999", json={"name": "x"})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


def test_textbook_crud(client):
    res = client.post("/textbooks", json={"publisher": "サンプル出版", "title": "新編数学1", "subject": "数学"})
    assert res.status_code == 201
    textbook = res.json()

    res = client.put(
        f"/textbooks/{textbook['id']}",
        json={"publisher": "サンプル出版", "title": "新編数学1改訂版", "subject": "数学"},
    )
    assert res.status_code == 200
    assert res.json()["title"] == "新編数学1改訂版"


def test_format_crud(client):
    res = client.post("/formats", json={"name": "計算"})
    assert res.status_code == 201
    fmt = res.json()
    assert fmt["name"] == "計算"


def _create_textbook(client):
    return client.post(
        "/textbooks", json={"publisher": "サンプル出版", "title": "新編数学1", "subject": "数学"}
    ).json()


def test_unit_crud_and_ordering(client):
    textbook = _create_textbook(client)

    res = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "正負の数", "order_no": 2})
    assert res.status_code == 201
    unit1 = res.json()

    res = client.post(f"/textbooks/{textbook['id']}/units", json={"name": "文字と式", "order_no": 1})
    unit2 = res.json()

    res = client.get(f"/textbooks/{textbook['id']}/units")
    names = [u["name"] for u in res.json()]
    assert names == ["文字と式", "正負の数"]  # ordered by order_no

    res = client.put(f"/units/{unit1['id']}", json={"name": "正負の数（改）", "order_no": 3})
    assert res.status_code == 200
    assert res.json()["name"] == "正負の数（改）"

    res = client.delete(f"/units/{unit2['id']}")
    assert res.status_code == 204


def test_unit_import_preview_confirm_flow(client):
    textbook = _create_textbook(client)

    res = client.post(
        f"/textbooks/{textbook['id']}/units/import",
        json={"rows": [{"name": "一次方程式", "order_no": 1}, {"name": "  ", "order_no": 2}]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["created"] == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row"] == 1

    units = client.get(f"/textbooks/{textbook['id']}/units").json()
    assert len(units) == 1


def test_unit_create_under_missing_textbook_404(client):
    res = client.post("/textbooks/999/units", json={"name": "x", "order_no": 1})
    assert res.status_code == 404


def _create_school(client, name="ひかり中学校"):
    return client.post("/schools", json={"name": name}).json()


def test_student_crud(client):
    school = _create_school(client)

    res = client.post(
        "/students",
        json={"student_code": "S0001", "school_id": school["id"], "grade": "中1", "level": "A"},
    )
    assert res.status_code == 201
    student = res.json()
    assert student["active"] is True

    res = client.post(
        "/students",
        json={"student_code": "S0001", "school_id": school["id"], "grade": "中1", "level": "A"},
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "DUPLICATE"

    res = client.put(
        f"/students/{student['id']}",
        json={
            "student_code": "S0001",
            "school_id": school["id"],
            "grade": "中2",
            "level": "B",
            "active": True,
        },
    )
    assert res.status_code == 200
    assert res.json()["grade"] == "中2"

    res = client.get("/students", params={"school_id": school["id"]})
    assert len(res.json()) == 1

    res = client.delete(f"/students/{student['id']}")
    assert res.status_code == 204


def test_student_invalid_level_rejected(client):
    school = _create_school(client)
    res = client.post(
        "/students",
        json={"student_code": "S0001", "school_id": school["id"], "grade": "中1", "level": "D"},
    )
    assert res.status_code == 422


def test_student_import(client):
    school = _create_school(client, name="ひかり中学校")

    res = client.post(
        "/students/import",
        json={
            "rows": [
                {"student_code": "S0001", "school_name": "ひかり中学校", "grade": "中1", "level": "A"},
                {"student_code": "S0002", "school_name": "存在しない学校", "grade": "中1", "level": "B"},
                {"student_code": "S0001", "school_name": "ひかり中学校", "grade": "中1", "level": "A"},
            ]
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["created"] == 1
    assert len(body["errors"]) == 2

    students = client.get("/students").json()
    assert len(students) == 1

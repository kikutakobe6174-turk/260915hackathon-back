from app.core.security import hash_password
from app.models import User


def _create_user(db_session, login_id="teacher1", password="password123", role="teacher", active=True):
    user = User(
        login_id=login_id,
        password_hash=hash_password(password),
        name="先生 花子",
        role=role,
        active=active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_login_success(client, db_session):
    user = _create_user(db_session)

    res = client.post("/auth/login", json={"login_id": "teacher1", "password": "password123"})

    assert res.status_code == 200
    body = res.json()
    assert body["user"]["id"] == user.id
    assert body["user"]["name"] == "先生 花子"
    assert body["user"]["role"] == "teacher"


def test_login_wrong_password(client, db_session):
    _create_user(db_session)

    res = client.post("/auth/login", json={"login_id": "teacher1", "password": "wrong"})

    assert res.status_code == 401
    assert res.json() == {"error": {"code": "INVALID_CREDENTIALS", "message": "IDまたはパスワードが違います"}}


def test_login_unknown_login_id(client, db_session):
    res = client.post("/auth/login", json={"login_id": "nobody", "password": "password123"})

    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_inactive_user_rejected(client, db_session):
    _create_user(db_session, login_id="inactive1", active=False)

    res = client.post("/auth/login", json={"login_id": "inactive1", "password": "password123"})

    assert res.status_code == 401

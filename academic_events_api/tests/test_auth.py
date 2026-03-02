def test_register_success(client):
    res = client.post("/api/v1/auth/register", json={
        "nombre": "Nuevo Usuario",
        "email": "nuevo@test.com",
        "password": "Password1"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "nuevo@test.com"
    assert data["rol"] == "usuario"
    assert "password_hash" not in data


def test_register_duplicate_email(client, regular_user):
    res = client.post("/api/v1/auth/register", json={
        "nombre": "Duplicado",
        "email": "user@test.com",
        "password": "Password1"
    })
    assert res.status_code == 409


def test_register_weak_password(client):
    res = client.post("/api/v1/auth/register", json={
        "nombre": "Test",
        "email": "test@test.com",
        "password": "weak"
    })
    assert res.status_code == 422


def test_login_success(client, regular_user):
    res = client.post("/api/v1/auth/login", json={
        "email": "user@test.com",
        "password": "User1234!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, regular_user):
    res = client.post("/api/v1/auth/login", json={
        "email": "user@test.com",
        "password": "wrongpassword"
    })
    assert res.status_code == 401


def test_get_profile(client, user_token):
    res = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "user@test.com"


def test_logout(client, user_token):
    res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    # Token revocado — siguiente request debe fallar
    res2 = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {user_token}"})
    assert res2.status_code == 401

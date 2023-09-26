import pytest

from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    client = app.test_client()
    yield client

def test_login_user_not_found(client):
    response = client.post("/login", json={"username": "notaUser", "password": "password"})
    assert response.status_code == 404
    assert response.json == {"msg": "User not found"}

def test_login_incorrect_password(client):
    response = client.post("/login", json={"username": "testuser", "password": "wrongpassword"})
    assert response.status_code == 401
    assert response.json == {"msg": "Incorrect password"}

def test_login_success(client):
    response = client.post("/login", json={"username": "demo", "password": "Demo1234$"})
    assert response.status_code == 200
    assert "access_token" in response.json
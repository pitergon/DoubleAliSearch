import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_register_page():
    response = client.get("/users/register")
    assert response.status_code == 200

def test_create_user():
    response = client.post("/users/register", data={
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpassword",
        "confirm_password": "testpassword"
    })
    assert response.status_code == 201


def test_get_login_page():
    response = client.get("/users/login")
    assert response.status_code == 200

def test_login_endpoint_success():
    form_data = {
        "username": "testuser",
        "password": "testpassword"
    }

    response = client.post("/users/login", data=form_data, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["Location"] == "/search"

    cookies = response.headers.get("set-cookie")
    assert cookies is not None
    assert "access_token=" in cookies
    assert "refresh_token=" in cookies


def test_logout_endpoint():
    response = client.get("/users/logout", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["Location"] == "/users/login"


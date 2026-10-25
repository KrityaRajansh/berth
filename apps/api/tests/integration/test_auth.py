from app.core.security import SESSION_COOKIE
from tests.integration.support import PASSWORD

NEW_USER = {
    "full_name": "Kavya Menon",
    "email": "kavya@example.com",
    "mobile": "9876543210",
    "password": "Secur3pass",
}


def test_it01_register_and_reject_duplicate(guest, network):
    first = guest.post("/auth/register", NEW_USER)
    second = guest.post("/auth/register", {**NEW_USER, "mobile": "9876543211"})

    assert first.status_code == 201
    assert first.json()["role"] == "PASSENGER"
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ACCOUNT_EXISTS"


def test_register_rejects_weak_password_and_bad_mobile(guest, network):
    response = guest.post(
        "/auth/register", {**NEW_USER, "password": "onlyletters", "mobile": "12345"}
    )

    assert response.status_code == 422
    fields = {d["field"] for d in response.json()["error"]["details"]}
    assert fields == {"password", "mobile"}


def test_it02_login_wrong_password_and_logout(guest, network):
    good = guest.post("/auth/login", {"email": "passenger1@example.com", "password": PASSWORD})
    assert good.status_code == 200
    assert SESSION_COOKIE in guest.client.cookies
    assert guest.get("/auth/me").json()["email"] == "passenger1@example.com"

    bad = guest.post("/auth/login", {"email": "passenger1@example.com", "password": "wrong-pass1"})
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "INVALID_CREDENTIALS"

    assert guest.post("/auth/logout").status_code == 204
    assert guest.get("/auth/me").status_code == 401


def test_it03_failed_logins_are_rate_limited(guest, network):
    statuses = [
        guest.post(
            "/auth/login", {"email": "passenger1@example.com", "password": "wrong-pass1"}
        ).status_code
        for _ in range(6)
    ]

    assert statuses == [401] * 5 + [429]


def test_it04_access_control(guest, p1):
    assert guest.get("/bookings").status_code == 401
    assert p1.get("/admin/stations").status_code == 403


def test_profile_update_and_password_change(p1):
    updated = p1.client.patch("/api/v1/users/me", json={"full_name": "Passenger Uno"})
    assert updated.json()["full_name"] == "Passenger Uno"

    wrong = p1.post(
        "/users/me/password", {"current_password": "nope", "new_password": "N3wpassword"}
    )
    assert wrong.status_code == 401
    ok = p1.post(
        "/users/me/password", {"current_password": PASSWORD, "new_password": "N3wpassword"}
    )
    assert ok.status_code == 204

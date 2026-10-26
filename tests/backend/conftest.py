import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app(tmp_path):
    application = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-key",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    })
    yield application
    with application.app_context():
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def authenticate(client, telephone="771234567", pseudo="Awa", quartier="Mermoz"):
    client.post("/api/auth/request-otp", json={"telephone": telephone})
    response = client.post("/api/auth/verify-otp", json={"telephone": telephone, "code": "1234"})
    token = response.get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.patch("/api/auth/profile", json={"pseudo": pseudo, "quartier_defaut": quartier}, headers=headers)
    return headers


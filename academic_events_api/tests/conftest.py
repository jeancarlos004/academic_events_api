import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.user import User
from app.models.event import Event
from main import app

# Base de datos en memoria para tests
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def admin_user(db):
    user = User(
        nombre="Admin Test",
        email="admin@test.com",
        password_hash=hash_password("Admin1234"),
        rol="admin"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def regular_user(db):
    user = User(
        nombre="Usuario Test",
        email="user@test.com",
        password_hash=hash_password("User1234!"),
        rol="usuario"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(client, admin_user):
    res = client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "Admin1234"
    })
    return res.json()["access_token"]


@pytest.fixture
def user_token(client, regular_user):
    res = client.post("/api/v1/auth/login", json={
        "email": "user@test.com",
        "password": "User1234!"
    })
    return res.json()["access_token"]


@pytest.fixture
def sample_event(db):
    from datetime import date
    event = Event(
        titulo="Evento de Prueba",
        descripcion="Descripción de prueba",
        fecha=date(2026, 6, 1),
        hora="10:00",
        lugar="Sala A",
        cupos=50,
        tipo="taller",
        estado="activo"
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

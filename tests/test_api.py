import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from db.database import Base, get_db

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

Base.metadata.create_all(bind=engine)

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    assert "DeployGuard" in response.json()["message"]


def test_get_summary_stats():
    """Test summary statistics endpoint"""
    response = client.get("/api/v1/analysis/stats/summary")
    assert response.status_code == 200
    assert "total_analyses" in response.json()


# Cleanup
@pytest.fixture(scope="session", autouse=True)
def cleanup():
    yield
    import os
    if os.path.exists("test.db"):
        os.remove("test.db")

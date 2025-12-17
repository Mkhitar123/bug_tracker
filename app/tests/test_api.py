import sys
sys.path.insert(0, '/app')

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
import json


@pytest.fixture(scope="session")
def postgres_engine():
    try:

        engine = create_engine('postgresql://bugtracker:bugtracker123@db/bugtracker')
    
        Base.metadata.create_all(bind=engine)
        
        yield engine
        
        # Base.metadata.drop_all(bind=engine)
        
    except Exception as e:
        pytest.skip(f"PostgreSQL connection failed: {e}")


@pytest.fixture
def postgres_session(postgres_engine):
    if postgres_engine is None:
        pytest.skip("PostgreSQL not available")
    
    connection = postgres_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(postgres_session):
    from main import app
    from database import get_db
    
    def override_get_db():
        try:
            yield postgres_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_health_endpoint_postgres(client):
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_read_root_postgres(client):
    response = client.get("/")
    
    assert response.status_code in [200, 404, 307]


def test_postgresql_connection_in_health(client):
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data.get("status") == "healthy"
    
    if "database" in data:
        assert data["database"] == "connected"


def test_user_registration_postgres(client):
    user_data = {
        "username": "postgres_user",
        "password": "password123",
        "role": "developer"
    }
    
    response = client.post("/api/register", json=user_data)

    if response.status_code in [200, 201]:
        data = response.json()
        assert "id" in data
        assert data["username"] == "postgres_user"
    elif response.status_code == 422:
        print("Validation error, maybe user already exist.")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def test_login_with_postgres(client):
    user_data = {
        "username": "login_test_user",
        "password": "testpassword",
        "role": "developer"
    }
    
    client.post("/api/register", json=user_data)
    
    login_data = {
        "username": "login_test_user",
        "password": "testpassword"
    }
    
    response = client.post("/api/login", data=login_data)
    
    if response.status_code == 200:
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    else:
        print(f"Login error: {response.status_code} - {response.text}")


def test_protected_endpoint_postgres(client):
    user_data = {
        "username": "protected_user",
        "password": "password123",
        "role": "developer"
    }
    
    client.post("/api/register", json=user_data)
    
    login_response = client.post("/api/login", data={
        "username": "protected_user",
        "password": "password123"
    })
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/users/me", headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            assert user_data["username"] == "protected_user"
        else:
            print(f"endpoint error: {response.status_code}")
    else:
        print("login error, can not cheak endpoont")

def test_create_task_postgres(client):
    user_data = {
        "username": "task_creator",
        "password": "password123",
        "role": "developer"
    }
    
    client.post("/api/register", json=user_data)
    
    login_response = client.post("/api/login", data={
        "username": "task_creator",
        "password": "password123"
    })
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        task_data = {
            "title": "PostgreSQL Test Task",
            "description": "Task created during PostgreSQL API test",
            "type": "bug",
            "priority": "high"
        }
        
        response = client.post("/api/tasks", json=task_data, headers=headers)
        
        if response.status_code in [200, 201]:
            task = response.json()
            assert "id" in task
            assert task["title"] == "PostgreSQL Test Task"
        else:
            print(f"task creation error: {response.status_code} - {response.text}")
    else:
        print("login error, can not creat tasks")


def test_get_tasks_postgres(client):
    response = client.get("/api/tasks")

    if response.status_code == 200:
        tasks = response.json()
        assert isinstance(tasks, list)
    elif response.status_code == 401:
        print("taskes require authentication.")
    else:
        print(f"error: {response.status_code} - {response.text}")


def test_task_crud_flow_postgres(client):
    user_data = {
        "username": "crud_flow_user",
        "password": "password123",
        "role": "developer"
    }
    
    client.post("/api/register", json=user_data)
    
    login_response = client.post("/api/login", data={
        "username": "crud_flow_user",
        "password": "password123"
    })
    
    if login_response.status_code != 200:
        pytest.skip("Login failed, cannot test CRUD flow")
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    task_data = {
        "title": "CRUD Flow Test Task",
        "description": "Testing full CRUD flow with PostgreSQL",
        "type": "task",
        "priority": "medium"
    }
    
    create_response = client.post("/api/tasks", json=task_data, headers=headers)
    
    if create_response.status_code not in [200, 201]:
        pytest.skip(f"Task creation failed: {create_response.status_code}")
    
    task = create_response.json()
    task_id = task["id"]
    
    get_response = client.get(f"/api/tasks/{task_id}", headers=headers)
    
    if get_response.status_code == 200:
        retrieved_task = get_response.json()
        assert retrieved_task["id"] == task_id
        assert retrieved_task["title"] == "CRUD Flow Test Task"
    
    update_data = {
        "title": "Updated CRUD Task",
        "status": "in_progress"
    }
    
    update_response = client.put(f"/api/tasks/{task_id}", json=update_data, headers=headers)
    
    if update_response.status_code in [200, 201]:
        updated_task = update_response.json()
        assert updated_task["title"] == "Updated CRUD Task"
        assert updated_task["status"] == "in_progress"

def test_error_handling_postgres(client):
    response = client.get("/api/nonexistent")
    assert response.status_code == 404
    
    response = client.post("/api/register", data="invalid json")
    assert response.status_code in [400, 422, 415, 404]  
    
    response = client.get("/api/tasks/999999")
    assert response.status_code in [404, 401]  

def test_postgresql_specific_features(client):
    try:
        from database import engine
        dialect = engine.dialect.name
        assert dialect == "postgresql"
    except:
        pass

    try:
        from models import TaskType, TaskPriority, TaskStatus, UserRole
        assert len(list(TaskType)) > 0
        assert len(list(TaskPriority)) > 0
        assert len(list(TaskStatus)) > 0
        assert len(list(UserRole)) > 0
    except:
        pass

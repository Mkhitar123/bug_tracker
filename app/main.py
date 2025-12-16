from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm 
from sqlalchemy.orm import Session
from typing import List, Optional
from contextlib import asynccontextmanager

# Import our modules
from database import engine, get_db
import models
import schemas
import crud
import auth

# Create tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="Bug Tracker API",
    description="A simplified bug tracking system",
    version="1.0.0",
    lifespan=lifespan
)

# Authentication endpoints
@app.post("/token", response_model=schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(get_db)):
    # This just uses the dependency
    return await auth.login_for_access_token(form_data, db)

@app.post("/register", response_model=schemas.UserInDB)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

@app.post("/change-password")
def change_password(
    old_password: str,
    new_password: str,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    if not auth.verify_password(old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    
    current_user.hashed_password = auth.get_password_hash(new_password)
    db.commit()
    return {"message": "Password updated successfully"}

# User management (Manager only)
@app.get("/users/", response_model=List[schemas.UserInDB])
def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(auth.get_manager_user),
    db: Session = Depends(get_db)
):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@app.put("/users/{user_id}", response_model=schemas.UserInDB)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(auth.get_manager_user),
    db: Session = Depends(get_db)
):
    db_user = crud.update_user(db, user_id=user_id, user_update=user_update)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# Task endpoints
@app.get("/tasks/", response_model=List[schemas.TaskWithRelations])
def read_tasks(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    tasks = crud.get_tasks(db, skip=skip, limit=limit)
    return tasks

@app.get("/tasks/{task_id}", response_model=schemas.TaskWithRelations)
def read_task(
    task_id: int,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    db_task = crud.get_task(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

@app.post("/tasks/", response_model=schemas.TaskInDB)
def create_task(
    task: schemas.TaskCreate,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    return crud.create_task(db=db, task=task, creator_id=current_user.id)

@app.put("/tasks/{task_id}", response_model=schemas.TaskInDB)
def update_task(
    task_id: int,
    task_update: schemas.TaskUpdate,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    db_task = crud.update_task(db, task_id=task_id, task_update=task_update)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

@app.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    current_user: models.User = Depends(auth.get_manager_user),
    db: Session = Depends(get_db)
):
    success = crud.delete_task(db, task_id=task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}

@app.post("/tasks/{task_id}/status")
def update_task_status(
    task_id: int,
    status: schemas.TaskStatus,
    assignee_id: Optional[int] = Query(None),
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    db_task = crud.get_task(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Validate status transition
    if not crud.validate_status_transition(db_task.status, status):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from {db_task.status} to {status}"
        )
    
    # Validate assignee
    is_valid, error_msg = crud.validate_assignee(db, status, assignee_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Update task
    update_data = schemas.TaskUpdate(status=status, assignee_id=assignee_id)
    return crud.update_task(db, task_id=task_id, task_update=update_data)

@app.post("/tasks/{parent_id}/subtasks", response_model=schemas.TaskInDB)
def create_subtask(
    parent_id: int,
    task: schemas.TaskCreate,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    parent_task = crud.get_task(db, parent_id)
    if parent_task is None:
        raise HTTPException(status_code=404, detail="Parent task not found")
    
    return crud.create_subtask(db, parent_id=parent_id, task=task, creator_id=current_user.id)

@app.post("/tasks/search", response_model=List[schemas.TaskWithRelations])
def search_tasks(
    search: schemas.TaskSearch,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    tasks = crud.search_tasks(db, search=search)
    return tasks

# Health check
@app.get("/")
def root():
    return {"message": "Bug Tracker API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Swagger tags for better documentation
app.openapi_tags = [
    {
        "name": "auth",
        "description": "Authentication operations",
    },
    {
        "name": "users",
        "description": "User management operations (Manager only)",
    },
    {
        "name": "tasks",
        "description": "Task operations",
    },
]
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc
import models
import schemas
from datetime import datetime

def get_password_hash(password):
    from auth import get_password_hash as _get_password_hash
    return _get_password_hash(password)

# User CRUD
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate):
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.model_dump(exclude_unset=True)
    
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

# Task CRUD
def generate_task_number(db: Session):
    last_task = db.query(models.Task).order_by(desc(models.Task.id)).first()
    if last_task and last_task.number:
        try:
            last_num = int(last_task.number.split('-')[-1])
            return f"PROJ-{last_num + 1:03d}"
        except:
            pass
    return "PROJ-001"

def get_task(db: Session, task_id: int):
    return db.query(models.Task).filter(models.Task.id == task_id).first()

def get_task_by_number(db: Session, task_number: str):
    return db.query(models.Task).filter(models.Task.number == task_number).first()

def get_tasks(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Task).order_by(desc(models.Task.updated_at)).offset(skip).limit(limit).all()

def create_task(db: Session, task: schemas.TaskCreate, creator_id: int):
    task_number = generate_task_number(db)
    db_task = models.Task(
        number=task_number,
        type=task.type,
        priority=task.priority,
        title=task.title,
        description=task.description,
        creator_id=creator_id,
        assignee_id=task.assignee_id,
        status=models.TaskStatus.TODO
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def update_task(db: Session, task_id: int, task_update: schemas.TaskUpdate):
    db_task = get_task(db, task_id)
    if not db_task:
        return None
    
    update_data = task_update.model_dump(exclude_unset=True)
    
    # Handle blocking relationships
    if "blocks" in update_data:
        blocks = update_data.pop("blocks")
        db_task.blocks = []
        if blocks:
            blocking_tasks = db.query(models.Task).filter(models.Task.id.in_(blocks)).all()
            db_task.blocks = blocking_tasks
    
    for key, value in update_data.items():
        setattr(db_task, key, value)
    
    db_task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_task)
    return db_task

def delete_task(db: Session, task_id: int):
    db_task = get_task(db, task_id)
    if db_task:
        db.delete(db_task)
        db.commit()
        return True
    return False

def search_tasks(db: Session, search: schemas.TaskSearch):
    query = db.query(models.Task)
    
    # Text search
    if search.query:
        query = query.filter(
            or_(
                models.Task.title.ilike(f"%{search.query}%"),
                models.Task.description.ilike(f"%{search.query}%")
            )
        )
    
    # Filter by number
    if search.task_number:
        query = query.filter(models.Task.number == search.task_number)
    
    # Other filters
    if search.type:
        query = query.filter(models.Task.type == search.type)
    if search.status:
        query = query.filter(models.Task.status == search.status)
    if search.creator_id:
        query = query.filter(models.Task.creator_id == search.creator_id)
    if search.assignee_id:
        query = query.filter(models.Task.assignee_id == search.assignee_id)
    
    # Sorting
    sort_column = getattr(models.Task, search.sort_by, models.Task.updated_at)
    if search.sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))
    
    return query.offset(search.skip).limit(search.limit).all()

def create_subtask(db: Session, parent_id: int, task: schemas.TaskCreate, creator_id: int):
    task_number = generate_task_number(db)
    db_task = models.Task(
        number=task_number,
        type=task.type,
        priority=task.priority,
        title=task.title,
        description=task.description,
        creator_id=creator_id,
        assignee_id=task.assignee_id,
        parent_id=parent_id,
        status=models.TaskStatus.TODO
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

# Status validation
def validate_status_transition(old_status: models.TaskStatus, new_status: models.TaskStatus):
    """Validate task status transition according to rules"""
    
    # Always allowed transitions
    if new_status in [models.TaskStatus.TODO, models.TaskStatus.WONTFIX]:
        return True
    
    # Normal flow
    status_order = [
        models.TaskStatus.TODO,
        models.TaskStatus.IN_PROGRESS,
        models.TaskStatus.CODE_REVIEW,
        models.TaskStatus.DEV_TEST,
        models.TaskStatus.TESTING,
        models.TaskStatus.DONE
    ]
    
    try:
        old_index = status_order.index(old_status)
        new_index = status_order.index(new_status)
        return new_index >= old_index
    except ValueError:
        return False

def validate_assignee(db: Session, status: models.TaskStatus, assignee_id: int = None):
    """Validate assignee based on status and role"""
    
    if assignee_id is None:
        # No assignee allowed for all statuses except IN_PROGRESS
        if status == models.TaskStatus.IN_PROGRESS:
            return False, "Assignee is required for IN_PROGRESS status"
        return True, ""
    
    assignee = get_user(db, assignee_id)
    if not assignee:
        return False, "Assignee not found"
    
    # 1. Manager can never be assignee
    if assignee.role == models.UserRole.MANAGER:
        return False, "Manager cannot be assigned to tasks"
    
    # 2. Team lead can be assignee for any status
    if assignee.role == models.UserRole.TEAM_LEAD:
        return True, ""
    
    # 3. Tester restrictions
    if assignee.role == models.UserRole.TESTER:
        if status in [models.TaskStatus.IN_PROGRESS, 
                     models.TaskStatus.CODE_REVIEW, 
                     models.TaskStatus.DEV_TEST]:
            return False, "Tester cannot be assignee for IN_PROGRESS, CODE_REVIEW, or DEV_TEST"
    
    # 4. Developer restrictions
    if assignee.role == models.UserRole.DEVELOPER:
        if status == models.TaskStatus.TESTING:
            return False, "Developer cannot be assignee for TESTING"
    
    return True, ""
import sys
import os
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, '/app')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../app')

try:
    from app.models import Base, User, Task
except ImportError:
    from models import Base, User, Task

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://bugtracker:bugtracker123@db/bugtracker"
)

def get_clean_db():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    
    with engine.begin() as conn:
        conn.execute(text("SET session_replication_role = 'replica';"))
        result = conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """))
        tables = [row[0] for row in result]
        
        if tables:
            tables_str = ', '.join(tables)
            conn.execute(text(f"TRUNCATE TABLE {tables_str} CASCADE;"))
        
        conn.execute(text("SET session_replication_role = 'origin';"))
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def generate_unique_username(prefix="user"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def test_create_user():
    db = get_clean_db()
    
    try:
        unique_username = generate_unique_username("testuser")
        user = User(
            username=unique_username,
            hashed_password="hashed_password123",
            role="developer"
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        assert user.id is not None
        assert user.username == unique_username
        assert user.role.value == "developer"
        assert user.is_active == True
        
    except Exception as e:
        raise
    finally:
        db.close()

def test_get_user():
    db = get_clean_db()
    
    try:
        unique_username = generate_unique_username("getuser")
        user = User(
            username=unique_username,
            hashed_password="hashed_password123",
            role="developer"
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        retrieved_user = db.query(User).filter(User.id == user.id).first()
        
        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.username == user.username
        assert retrieved_user.role == user.role
        
    finally:
        db.close()

def test_update_user():
    db = get_clean_db()
    
    try:
        unique_username = generate_unique_username("updateuser")
        user = User(
            username=unique_username,
            hashed_password="hashed_password123",
            role="developer"
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        user.role = "manager"
        user.is_active = False
        db.commit()
        db.refresh(user)
        
        assert user.role.value == "manager"
        assert user.is_active == False
        assert user.username == unique_username
        
    except Exception as e:
        raise
    finally:
        db.close()

def test_delete_user():
    db = get_clean_db()
    
    try:
        unique_username = generate_unique_username("deleteuser")
        user = User(
            username=unique_username,
            hashed_password="hashed_password123",
            role="developer"
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        user_id = user.id
        db.delete(user)
        db.commit()
        
        deleted_user = db.query(User).filter(User.id == user_id).first()
        assert deleted_user is None
        
    finally:
        db.close()

def test_create_task():
    db = get_clean_db()
    
    try:
        creator_username = generate_unique_username("creator")
        creator = User(
            username=creator_username,
            hashed_password="hashed_password123",
            role="developer"
        )
        
        db.add(creator)
        db.commit()
        db.refresh(creator)
        
        task = Task(
            title="Test Task Title",
            description="Test task description",
            type="bug",
            priority="high",
            creator_id=creator.id
        )
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        assert task.id is not None
        assert task.title == "Test Task Title"
        assert task.description == "Test task description"
        assert task.type.value == "bug"
        assert task.priority.value == "high"
        assert task.creator_id == creator.id
        
    except Exception as e:
        raise
    finally:
        db.close()

def test_get_task():
    db = get_clean_db()
    
    try:
        creator_username = generate_unique_username("taskcreator")
        creator = User(
            username=creator_username,
            hashed_password="hashed_password123",
            role="developer"
        )
        
        db.add(creator)
        db.commit()
        db.refresh(creator)
        
        task = Task(
            title="Get Task Test",
            description="Task for get testing",
            type="task",
            priority="medium",
            creator_id=creator.id
        )
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        retrieved_task = db.query(Task).filter(Task.id == task.id).first()
        
        assert retrieved_task is not None
        assert retrieved_task.id == task.id
        assert retrieved_task.title == task.title
        assert retrieved_task.creator_id == creator.id
        
    except Exception as e:
        raise
    finally:
        db.close()

def test_update_task():
    db = get_clean_db()
    
    try:
        creator_username = generate_unique_username("updatetask")
        creator = User(
            username=creator_username,
            hashed_password="hashed_password123",
            role="developer"
        )
        
        assignee_username = generate_unique_username("assignee")
        assignee = User(
            username=assignee_username,
            hashed_password="hashed_password123",
            role="developer"
        )
        
        db.add_all([creator, assignee])
        db.commit()
        db.refresh(creator)
        db.refresh(assignee)
        
        task = Task(
            title="Original Task Title",
            description="Original description",
            type="bug",
            priority="low",
            creator_id=creator.id
        )
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        task.title = "Updated Task Title"
        task.description = "Updated description"
        task.status = "in_progress"
        task.priority = "high"
        task.assignee_id = assignee.id
        
        db.commit()
        db.refresh(task)
        
        assert task.title == "Updated Task Title"
        assert task.description == "Updated description"
        assert task.status.value == "in_progress"
        assert task.priority.value == "high"
        assert task.assignee_id == assignee.id
        
    except Exception as e:
        raise
    finally:
        db.close()

def test_delete_task():
    db = get_clean_db()
    
    try:
        creator_username = generate_unique_username("deletetask")
        creator = User(
            username=creator_username,
            hashed_password="hashed_password123",
            role="developer"
        )
        
        db.add(creator)
        db.commit()
        db.refresh(creator)
        
        task = Task(
            title="Task to Delete",
            description="This task will be deleted",
            type="task",
            priority="medium",
            creator_id=creator.id
        )
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        task_id = task.id
        db.delete(task)
        db.commit()
        
        deleted_task = db.query(Task).filter(Task.id == task_id).first()
        assert deleted_task is None
        
    finally:
        db.close()

def test_task_blocking_relationship():
    db = get_clean_db()
    
    try:
        creator_username = generate_unique_username("blockcreator")
        creator = User(
            username=creator_username,
            hashed_password="hashed_password123",
            role="developer"
        )
        
        db.add(creator)
        db.commit()
        db.refresh(creator)
        
        task1 = Task(
            title="Blocking Task",
            description="Task that blocks others",
            type="bug",
            priority="high",
            creator_id=creator.id
        )
        
        task2 = Task(
            title="Blocked Task",
            description="Task that is blocked",
            type="task",
            priority="medium",
            creator_id=creator.id
        )
        
        db.add_all([task1, task2])
        db.commit()
        db.refresh(task1)
        db.refresh(task2)
        
        task1.blocks.append(task2)
        db.commit()
        
        assert task2 in task1.blocks
        assert task1 in task2.blocked_by
        
    except Exception as e:
        raise
    finally:
        db.close()

def test_task_subtasks_relationship():
    db = get_clean_db()
    
    try:
        creator_username = generate_unique_username("subtaskcreator")
        creator = User(
            username=creator_username,
            hashed_password="hashed_password123",
            role="developer"
        )
        
        db.add(creator)
        db.commit()
        db.refresh(creator)
        
        parent_task = Task(
            title="Parent Task",
            description="Parent task with subtasks",
            type="task",
            priority="medium",
            creator_id=creator.id
        )
        
        subtask = Task(
            title="Subtask",
            description="Child task of parent",
            type="task",
            priority="low",
            creator_id=creator.id
        )
        
        db.add_all([parent_task, subtask])
        db.commit()
        db.refresh(parent_task)
        db.refresh(subtask)
        
        subtask.parent_id = parent_task.id
        db.commit()
        db.refresh(parent_task)
        db.refresh(subtask)
        
        assert subtask in parent_task.subtasks
        assert subtask.parent_id == parent_task.id
        assert subtask.parent == parent_task
        
    except Exception as e:
        raise
    finally:
        db.close()

def test_query_users():
    db = get_clean_db()
    
    try:
        users = []
        for i in range(3):
            username = generate_unique_username(f"queryuser{i}")
            user = User(
                username=username,
                hashed_password="hashed_password123",
                role="developer"
            )
            users.append(user)
            db.add(user)
        
        db.commit()
        
        all_users = db.query(User).all()
        assert len(all_users) >= 3
        
        dev_users = db.query(User).filter(User.role == "developer").all()
        assert len(dev_users) >= 3
        
    except Exception as e:
        raise
    finally:
        db.close()

def test_query_tasks():
    db = get_clean_db()
    
    try:
        creator_username = generate_unique_username("querytaskuser")
        creator = User(
            username=creator_username,
            hashed_password="hashed_password123",
            role="developer"
        )
        
        db.add(creator)
        db.commit()
        db.refresh(creator)
        
        tasks = []
        task_types = ["bug", "task"]
        priorities = ["low", "medium", "high"]
        
        for i in range(5):
            task = Task(
                title=f"Query Task {i}",
                description=f"Task description {i}",
                type=task_types[i % 2],
                priority=priorities[i % 3],
                creator_id=creator.id
            )
            tasks.append(task)
            db.add(task)
        
        db.commit()
        
        all_tasks = db.query(Task).all()
        assert len(all_tasks) >= 5
        
    except Exception as e:
        raise
    finally:
        db.close()
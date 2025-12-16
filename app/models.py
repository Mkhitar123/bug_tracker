from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, Boolean, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

# Association table for task blocking relationships
task_blocking = Table(
    'task_blocking',
    Base.metadata,
    Column('blocking_task_id', Integer, ForeignKey('tasks.id'), primary_key=True),
    Column('blocked_task_id', Integer, ForeignKey('tasks.id'), primary_key=True)
)

class UserRole(str, enum.Enum):
    MANAGER = "manager"
    TEAM_LEAD = "team_lead"
    DEVELOPER = "developer"
    TESTER = "tester"

class TaskType(str, enum.Enum):
    BUG = "bug"
    TASK = "task"

class TaskPriority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TaskStatus(str, enum.Enum):
    TODO = "to_do"
    IN_PROGRESS = "in_progress"
    CODE_REVIEW = "code_review"
    DEV_TEST = "dev_test"
    TESTING = "testing"
    DONE = "done"
    WONTFIX = "wontfix"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.DEVELOPER)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    created_tasks = relationship("Task", foreign_keys="Task.creator_id", back_populates="creator")
    assigned_tasks = relationship("Task", foreign_keys="Task.assignee_id", back_populates="assignee")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, unique=True, index=True)  # Format: PROJ-001
    type = Column(Enum(TaskType), nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.TODO)
    title = Column(String, nullable=False)
    description = Column(Text)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"))
    parent_id = Column(Integer, ForeignKey("tasks.id"))  # For subtasks
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_tasks")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tasks")
    parent = relationship("Task", remote_side=[id], back_populates="subtasks")
    subtasks = relationship("Task", back_populates="parent")
    
    # Many-to-many for blocking relationships
    blocks = relationship(
        "Task",
        secondary=task_blocking,
        primaryjoin=id==task_blocking.c.blocking_task_id,
        secondaryjoin=id==task_blocking.c.blocked_task_id,
        backref="blocked_by"
    )
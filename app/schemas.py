from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List
from enum import Enum

class UserRole(str, Enum):
    MANAGER = "manager"
    TEAM_LEAD = "team_lead"
    DEVELOPER = "developer"
    TESTER = "tester"

class TaskType(str, Enum):
    BUG = "bug"
    TASK = "task"

class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TaskStatus(str, Enum):
    TODO = "to_do"
    IN_PROGRESS = "in_progress"
    CODE_REVIEW = "code_review"
    DEV_TEST = "dev_test"
    TESTING = "testing"
    DONE = "done"
    WONTFIX = "wontfix"

# User schemas
class UserBase(BaseModel):
    username: str
    role: UserRole

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None
    password: Optional[str] = None

class UserInDB(UserBase):
    id: int
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)

# Task schemas
class TaskBase(BaseModel):
    type: TaskType
    priority: Optional[TaskPriority] = TaskPriority.MEDIUM
    title: str
    description: Optional[str] = None
    assignee_id: Optional[int] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    type: Optional[TaskType] = None
    priority: Optional[TaskPriority] = None
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    status: Optional[TaskStatus] = None
    blocks: Optional[List[int]] = None  # IDs of tasks this task blocks

class TaskInDB(TaskBase):
    id: int
    number: str
    status: TaskStatus
    creator_id: int
    assignee_id: Optional[int] = None
    parent_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class TaskWithRelations(TaskInDB):
    creator: Optional[UserInDB] = None
    assignee: Optional[UserInDB] = None
    subtasks: List["TaskInDB"] = []
    blocks: List["TaskInDB"] = []
    blocked_by: List["TaskInDB"] = []

# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Search schemas
class TaskSearch(BaseModel):
    query: Optional[str] = None
    task_number: Optional[str] = None
    type: Optional[TaskType] = None
    status: Optional[TaskStatus] = None
    creator_id: Optional[int] = None
    assignee_id: Optional[int] = None
    sort_by: Optional[str] = "updated_at"
    sort_order: Optional[str] = "desc"
    skip: int = 0
    limit: int = 100
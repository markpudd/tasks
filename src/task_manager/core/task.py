from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field
import uuid

class ProjectFolder(BaseModel):
    """Represents a project folder in the hierarchical structure"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: 'TaskCategory'  # Work or Personal
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectFolder":
        folder_data = data.copy()
        folder_data["category"] = TaskCategory(folder_data["category"])
        folder_data["created_at"] = datetime.fromisoformat(folder_data["created_at"])
        return cls(**folder_data)

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskCategory(Enum):
    PERSONAL = "personal"
    WORK = "work"

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    category: TaskCategory = TaskCategory.PERSONAL
    project: Optional[str] = None  # Now stores project folder name for backward compatibility
    project_id: Optional[str] = None  # New field for project folder ID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    due_date: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def update_status(self, status: TaskStatus):
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
    
    def add_tag(self, tag: str):
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now(timezone.utc)
    
    def remove_tag(self, tag: str):
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "category": self.category.value,
            "project": self.project,
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        task_data = data.copy()
        task_data["status"] = TaskStatus(task_data["status"])
        task_data["priority"] = TaskPriority(task_data["priority"])
        # Handle backward compatibility for category field
        if "category" in task_data:
            task_data["category"] = TaskCategory(task_data["category"])
        else:
            task_data["category"] = TaskCategory.PERSONAL  # Default for old tasks
        task_data["created_at"] = datetime.fromisoformat(task_data["created_at"])
        task_data["updated_at"] = datetime.fromisoformat(task_data["updated_at"])
        if task_data["due_date"]:
            task_data["due_date"] = datetime.fromisoformat(task_data["due_date"])
        return cls(**task_data)
    
    def format_for_print(self) -> str:
        lines = []
        lines.append("=" * 40)
        lines.append(f"TASK: {self.title}")
        lines.append("=" * 40)
        if self.description:
            lines.append(f"Description: {self.description}")
        lines.append(f"Status: {self.status.value.title()}")
        lines.append(f"Priority: {self.priority.value.title()}")
        lines.append(f"Category: {self.category.value.title()}")
        if self.project:
            lines.append(f"Project: {self.project}")
        lines.append(f"Created: {self.created_at.strftime('%Y-%m-%d %H:%M')}")
        if self.due_date:
            lines.append(f"Due: {self.due_date.strftime('%Y-%m-%d %H:%M')}")
        if self.tags:
            lines.append(f"Tags: {', '.join(self.tags)}")
        lines.append("-" * 40)
        lines.append(f"ID: {self.id}")
        lines.append("=" * 40)
        return "\n".join(lines)
import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from .task import Task, TaskStatus, TaskPriority, TaskCategory

class TaskManager:
    def __init__(self, storage_file: str = "tasks.json"):
        self.storage_file = storage_file
        self.tasks: Dict[str, Task] = {}
        self.load_tasks()
    
    def load_tasks(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    tasks_data = json.load(f)
                    for task_data in tasks_data:
                        task = Task.from_dict(task_data)
                        self.tasks[task.id] = task
            except Exception as e:
                print(f"Error loading tasks: {e}")
    
    def save_tasks(self):
        try:
            tasks_data = [task.to_dict() for task in self.tasks.values()]
            with open(self.storage_file, 'w') as f:
                json.dump(tasks_data, f, indent=2)
        except Exception as e:
            print(f"Error saving tasks: {e}")
    
    def create_task(
        self, 
        title: str, 
        description: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        category: TaskCategory = TaskCategory.PERSONAL,
        project: Optional[str] = None,
        due_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None
    ) -> Task:
        task = Task(
            title=title,
            description=description,
            priority=priority,
            category=category,
            project=project,
            due_date=due_date,
            tags=tags or []
        )
        self.tasks[task.id] = task
        self.save_tasks()
        return task
    
    def delete_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            del self.tasks[task_id]
            self.save_tasks()
            return True
        return False
    
    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        return list(self.tasks.values())
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        return [task for task in self.tasks.values() if task.status == status]
    
    def get_tasks_by_priority(self, priority: TaskPriority) -> List[Task]:
        return [task for task in self.tasks.values() if task.priority == priority]
    
    def get_tasks_by_tag(self, tag: str) -> List[Task]:
        return [task for task in self.tasks.values() if tag in task.tags]
    
    def get_tasks_by_category(self, category: TaskCategory) -> List[Task]:
        return [task for task in self.tasks.values() if task.category == category]
    
    def get_tasks_by_project(self, project: str) -> List[Task]:
        return [task for task in self.tasks.values() if task.project and task.project.lower() == project.lower()]
    
    def get_all_projects(self) -> List[str]:
        projects = set()
        for task in self.tasks.values():
            if task.project:
                projects.add(task.project)
        return sorted(list(projects))
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        if task_id in self.tasks:
            self.tasks[task_id].update_status(status)
            self.save_tasks()
            return True
        return False
    
    def search_tasks(self, query: str) -> List[Task]:
        query = query.lower()
        matching_tasks = []
        for task in self.tasks.values():
            if (query in task.title.lower() or 
                (task.description and query in task.description.lower()) or
                any(query in tag.lower() for tag in task.tags)):
                matching_tasks.append(task)
        return matching_tasks
    
    def get_overdue_tasks(self) -> List[Task]:
        now = datetime.now()
        return [
            task for task in self.tasks.values()
            if task.due_date and task.due_date < now and task.status != TaskStatus.COMPLETED
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        total_tasks = len(self.tasks)
        if total_tasks == 0:
            return {"total": 0, "by_status": {}, "by_priority": {}, "by_category": {}, "by_project": {}}
        
        status_counts = {}
        priority_counts = {}
        category_counts = {}
        project_counts = {}
        
        for task in self.tasks.values():
            status_counts[task.status.value] = status_counts.get(task.status.value, 0) + 1
            priority_counts[task.priority.value] = priority_counts.get(task.priority.value, 0) + 1
            category_counts[task.category.value] = category_counts.get(task.category.value, 0) + 1
            if task.project:
                project_counts[task.project] = project_counts.get(task.project, 0) + 1
        
        return {
            "total": total_tasks,
            "by_status": status_counts,
            "by_priority": priority_counts,
            "by_category": category_counts,
            "by_project": project_counts,
            "overdue": len(self.get_overdue_tasks()),
            "total_projects": len(self.get_all_projects())
        }
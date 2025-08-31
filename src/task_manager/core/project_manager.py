import json
import os
from typing import List, Dict, Optional
from .task import ProjectFolder, TaskCategory

class ProjectManager:
    def __init__(self, storage_file: str = "projects.json"):
        self.storage_file = storage_file
        self.projects: Dict[str, ProjectFolder] = {}
        self.load_projects()
        
        # Create default projects if none exist
        if not self.projects:
            self._create_default_projects()
    
    def load_projects(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    projects_data = json.load(f)
                    for project_data in projects_data:
                        project = ProjectFolder.from_dict(project_data)
                        self.projects[project.id] = project
            except Exception as e:
                print(f"Error loading projects: {e}")
    
    def save_projects(self):
        try:
            projects_data = [project.to_dict() for project in self.projects.values()]
            with open(self.storage_file, 'w') as f:
                json.dump(projects_data, f, indent=2)
        except Exception as e:
            print(f"Error saving projects: {e}")
    
    def _create_default_projects(self):
        """Create default project structure"""
        default_projects = [
            # Work Projects
            {"name": "General", "category": TaskCategory.WORK, "description": "General work tasks"},
            {"name": "Development", "category": TaskCategory.WORK, "description": "Software development projects"},
            {"name": "Meetings", "category": TaskCategory.WORK, "description": "Meeting-related tasks"},
            {"name": "Administration", "category": TaskCategory.WORK, "description": "Administrative tasks"},
            
            # Personal Projects
            {"name": "Home", "category": TaskCategory.PERSONAL, "description": "Home and household tasks"},
            {"name": "Health", "category": TaskCategory.PERSONAL, "description": "Health and fitness related tasks"},
            {"name": "Learning", "category": TaskCategory.PERSONAL, "description": "Personal learning and education"},
            {"name": "Hobbies", "category": TaskCategory.PERSONAL, "description": "Hobby and recreational activities"},
        ]
        
        for project_data in default_projects:
            project = ProjectFolder(**project_data)
            self.projects[project.id] = project
        
        self.save_projects()
        print("Created default project structure")
    
    def create_project(self, name: str, category: TaskCategory, description: str = None) -> ProjectFolder:
        """Create a new project folder"""
        project = ProjectFolder(name=name, category=category, description=description)
        self.projects[project.id] = project
        self.save_projects()
        return project
    
    def get_project(self, project_id: str) -> Optional[ProjectFolder]:
        """Get a project by ID"""
        return self.projects.get(project_id)
    
    def get_project_by_name(self, name: str, category: TaskCategory = None) -> Optional[ProjectFolder]:
        """Get a project by name, optionally filtered by category"""
        for project in self.projects.values():
            if project.name == name and (category is None or project.category == category):
                return project
        return None
    
    def get_projects_by_category(self, category: TaskCategory) -> List[ProjectFolder]:
        """Get all projects in a specific category"""
        return [p for p in self.projects.values() if p.category == category]
    
    def get_all_projects(self) -> List[ProjectFolder]:
        """Get all projects"""
        return list(self.projects.values())
    
    def get_hierarchical_structure(self) -> Dict[str, List[ProjectFolder]]:
        """Get projects organized by category"""
        structure = {
            "work": self.get_projects_by_category(TaskCategory.WORK),
            "personal": self.get_projects_by_category(TaskCategory.PERSONAL)
        }
        return structure
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project folder"""
        if project_id in self.projects:
            del self.projects[project_id]
            self.save_projects()
            return True
        return False
    
    def update_project(self, project_id: str, **kwargs) -> Optional[ProjectFolder]:
        """Update a project folder"""
        project = self.projects.get(project_id)
        if not project:
            return None
        
        for key, value in kwargs.items():
            if hasattr(project, key):
                setattr(project, key, value)
        
        self.save_projects()
        return project
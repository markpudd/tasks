#!/usr/bin/env python3
"""
Google Tasks Import Script for Task Management Application

This script imports tasks from a Google Tasks export file into the task management application.
It handles project creation, task assignment, and user-specific storage.

Usage:
    python import_google_tasks.py --input EXPORT_FILE --user USER_ID [--dry-run]

Example:
    python import_google_tasks.py --input google_tasks_export.json --user 283ea866-19fb-4921-af3c-1e64ccf943ec
"""

import argparse
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from task_manager.core.task_manager import TaskManager
    from task_manager.core.task import Task, TaskStatus, TaskPriority, TaskCategory
except ImportError as e:
    print(f"Error importing task manager modules: {e}")
    print("Make sure you're running this script from the task management application directory.")
    sys.exit(1)

class GoogleTasksImporter:
    def __init__(self, user_id: str):
        self.user_id = user_id
        storage_file = f"tasks_{user_id}.json"
        self.task_manager = TaskManager(storage_file)
        self.imported_count = 0
        self.skipped_count = 0
        self.projects_created = 0
        self.project_mapping = {}  # Google task list name -> project ID
        
    def load_export_file(self, filename: str) -> Dict[str, Any]:
        """Load the Google Tasks export file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'tasks' in data:
                return data
            else:
                # Assume it's a direct task list
                return {'tasks': data}
                
        except FileNotFoundError:
            print(f"❌ Export file not found: {filename}")
            return {}
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in export file: {e}")
            return {}
        except Exception as e:
            print(f"❌ Error reading export file: {e}")
            return {}
    
    def create_or_get_project(self, project_name: str, category: str) -> str:
        """Create a new project or get existing project ID"""
        
        # Check if project already exists
        category_enum = TaskCategory.WORK if category == 'work' else TaskCategory.PERSONAL
        existing_project = self.task_manager.project_manager.get_project_by_name(
            project_name, category_enum
        )
        
        if existing_project:
            print(f"  📁 Using existing project: {project_name}")
            return existing_project.id
        
        # Create new project
        try:
            new_project = self.task_manager.project_manager.create_project(
                name=project_name,
                category=category_enum,
                description=f"Imported from Google Tasks"
            )
            self.projects_created += 1
            print(f"  📁 Created project: {project_name} ({category})")
            return new_project.id
            
        except Exception as e:
            print(f"  ❌ Error creating project {project_name}: {e}")
            return None
    
    def task_exists(self, task_id: str, title: str) -> bool:
        """Check if a task already exists (by ID or similar title)"""
        
        # Check by ID (for re-imports)
        if self.task_manager.get_task(task_id):
            return True
        
        # Check by similar title in the same timeframe
        for existing_task in self.task_manager.get_all_tasks():
            if (existing_task.title.lower().strip() == title.lower().strip() and 
                'google_tasks' in existing_task.metadata.get('source', '')):
                return True
        
        return False
    
    def convert_priority(self, priority_str: str) -> TaskPriority:
        """Convert string priority to TaskPriority enum"""
        priority_map = {
            'low': TaskPriority.LOW,
            'medium': TaskPriority.MEDIUM,
            'high': TaskPriority.HIGH,
            'urgent': TaskPriority.URGENT
        }
        return priority_map.get(priority_str.lower(), TaskPriority.MEDIUM)
    
    def convert_status(self, status_str: str) -> TaskStatus:
        """Convert string status to TaskStatus enum"""
        status_map = {
            'pending': TaskStatus.PENDING,
            'in_progress': TaskStatus.IN_PROGRESS,
            'completed': TaskStatus.COMPLETED,
            'cancelled': TaskStatus.CANCELLED
        }
        return status_map.get(status_str.lower(), TaskStatus.PENDING)
    
    def convert_category(self, category_str: str) -> TaskCategory:
        """Convert string category to TaskCategory enum"""
        return TaskCategory.WORK if category_str.lower() == 'work' else TaskCategory.PERSONAL
    
    def import_task(self, task_data: Dict[str, Any], dry_run: bool = False) -> bool:
        """Import a single task"""
        
        try:
            title = task_data.get('title', 'Untitled Task')
            task_id = task_data.get('id', f"gtask_{hash(title)}")
            
            # Skip if task already exists
            if self.task_exists(task_id, title):
                print(f"  ⏩ Skipping existing task: {title}")
                self.skipped_count += 1
                return False
            
            # Get or create project
            project_name = task_data.get('project', 'Imported Tasks')
            category = task_data.get('category', 'personal')
            
            project_key = f"{project_name}:{category}"
            if project_key not in self.project_mapping:
                if not dry_run:
                    project_id = self.create_or_get_project(project_name, category)
                    self.project_mapping[project_key] = project_id
                else:
                    self.project_mapping[project_key] = f"dry_run_project_{len(self.project_mapping)}"
            
            project_id = self.project_mapping[project_key]
            
            # Parse due date
            due_date = None
            if task_data.get('due_date'):
                try:
                    due_date = datetime.fromisoformat(task_data['due_date'].replace('Z', '+00:00'))
                except:
                    pass
            
            # Create task
            if not dry_run:
                task = self.task_manager.create_task(
                    title=title,
                    description=task_data.get('description', ''),
                    priority=self.convert_priority(task_data.get('priority', 'medium')),
                    category=self.convert_category(category),
                    project_id=project_id,
                    due_date=due_date,
                    tags=task_data.get('tags', [])
                )
                
                # Update status if completed
                if task_data.get('status') == 'completed':
                    self.task_manager.update_task_status(task.id, TaskStatus.COMPLETED)
                
                print(f"  ✅ Imported: {title}")
            else:
                print(f"  [DRY RUN] Would import: {title} -> {project_name}")
            
            self.imported_count += 1
            return True
            
        except Exception as e:
            print(f"  ❌ Error importing task '{task_data.get('title', 'Unknown')}': {e}")
            return False
    
    def import_tasks(self, export_data: Dict[str, Any], dry_run: bool = False) -> bool:
        """Import all tasks from export data"""
        
        tasks = export_data.get('tasks', [])
        if not tasks:
            print("❌ No tasks found in export file")
            return False
        
        export_info = export_data.get('export_info', {})
        if export_info:
            print(f"📋 Export Info:")
            print(f"  Source: {export_info.get('source', 'Unknown')}")
            print(f"  Export Date: {export_info.get('export_date', 'Unknown')}")
            print(f"  Total Tasks: {export_info.get('total_tasks', len(tasks))}")
            print(f"  Total Lists: {export_info.get('total_lists', 'Unknown')}")
        
        print(f"\\n🚀 {'[DRY RUN] ' if dry_run else ''}Starting import...")
        print(f"📥 Processing {len(tasks)} tasks...")
        
        # Group tasks by project for better organization
        tasks_by_project = {}
        for task in tasks:
            project_key = f"{task.get('project', 'Imported Tasks')}:{task.get('category', 'personal')}"
            if project_key not in tasks_by_project:
                tasks_by_project[project_key] = []
            tasks_by_project[project_key].append(task)
        
        print(f"📁 Found {len(tasks_by_project)} unique projects/categories")
        
        # Import tasks project by project
        for project_key, project_tasks in tasks_by_project.items():
            project_name, category = project_key.split(':', 1)
            print(f"\\n📁 Processing project: {project_name} ({category}) - {len(project_tasks)} tasks")
            
            for task in project_tasks:
                self.import_task(task, dry_run)
        
        return True
    
    def print_summary(self, dry_run: bool = False):
        """Print import summary"""
        print("\\n" + "="*50)
        print(f"🎉 {'[DRY RUN] ' if dry_run else ''}Import Summary")
        print("="*50)
        print(f"✅ Tasks imported: {self.imported_count}")
        print(f"⏩ Tasks skipped: {self.skipped_count}")
        print(f"📁 Projects created: {self.projects_created}")
        
        if not dry_run and self.imported_count > 0:
            print(f"\\n📍 Tasks saved to: tasks_{self.user_id}.json")
            print(f"📍 Projects saved to: projects_{self.user_id}.json")
            print("\\n🌐 You can now view the imported tasks in the web interface!")

def main():
    parser = argparse.ArgumentParser(description='Import Google Tasks export into task management app')
    parser.add_argument('--input', '-i', required=True,
                       help='Input file (Google Tasks export JSON)')
    parser.add_argument('--user', '-u', required=True,
                       help='User ID to import tasks for')
    parser.add_argument('--dry-run', '-d', action='store_true',
                       help='Show what would be imported without actually importing')
    
    args = parser.parse_args()
    
    print("Google Tasks Importer")
    print("=" * 50)
    print(f"📁 Input file: {args.input}")
    print(f"👤 User ID: {args.user}")
    
    if args.dry_run:
        print("🧪 DRY RUN MODE - No changes will be made")
    
    # Initialize importer
    importer = GoogleTasksImporter(args.user)
    
    # Load export file
    export_data = importer.load_export_file(args.input)
    if not export_data:
        sys.exit(1)
    
    # Import tasks
    success = importer.import_tasks(export_data, dry_run=args.dry_run)
    
    # Print summary
    importer.print_summary(dry_run=args.dry_run)
    
    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main()
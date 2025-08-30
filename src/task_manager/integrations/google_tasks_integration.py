import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import os
from ..core.task import Task, TaskStatus, TaskPriority
from dateutil.parser import parse as parse_date

logger = logging.getLogger(__name__)

class GoogleTasksIntegration:
    SCOPES = ['https://www.googleapis.com/auth/tasks']
    
    def __init__(self, credentials_file: str = "gtasks_credentials.json", token_file: str = "gtasks_token.json"):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.creds = None
        self._authenticate()
    
    def _authenticate(self):
        if os.path.exists(self.token_file):
            self.creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    logger.error(f"Google Tasks credentials file not found: {self.credentials_file}")
                    return
                
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open(self.token_file, 'w') as token:
                token.write(self.creds.to_json())
        
        try:
            self.service = build('tasks', 'v1', credentials=self.creds)
            logger.info("Successfully authenticated with Google Tasks")
        except Exception as e:
            logger.error(f"Failed to build Google Tasks service: {e}")
    
    def is_authenticated(self) -> bool:
        return self.service is not None
    
    def get_task_lists(self) -> List[Dict[str, Any]]:
        if not self.is_authenticated():
            logger.error("Google Tasks not authenticated")
            return []
        
        try:
            results = self.service.tasklists().list().execute()
            task_lists = results.get('items', [])
            return task_lists
        except Exception as e:
            logger.error(f"Error fetching task lists: {e}")
            return []
    
    def get_tasks_from_list(self, tasklist_id: str) -> List[Dict[str, Any]]:
        if not self.is_authenticated():
            return []
        
        try:
            results = self.service.tasks().list(tasklist=tasklist_id).execute()
            tasks = results.get('items', [])
            return tasks
        except Exception as e:
            logger.error(f"Error fetching tasks from list {tasklist_id}: {e}")
            return []
    
    def import_tasks_from_google(self, task_manager, tasklist_id: Optional[str] = None) -> List[Task]:
        if not tasklist_id:
            # Use the default task list
            task_lists = self.get_task_lists()
            if not task_lists:
                logger.error("No task lists found")
                return []
            tasklist_id = task_lists[0]['id']  # Use first list
        
        google_tasks = self.get_tasks_from_list(tasklist_id)
        imported_tasks = []
        
        for gtask in google_tasks:
            task = self._convert_google_task_to_task(gtask, task_manager)
            if task:
                imported_tasks.append(task)
        
        return imported_tasks
    
    def _convert_google_task_to_task(self, google_task: Dict[str, Any], task_manager) -> Optional[Task]:
        try:
            title = google_task.get('title', 'Untitled Task')
            description = google_task.get('notes', '')
            
            # Convert status
            status = TaskStatus.PENDING
            if google_task.get('status') == 'completed':
                status = TaskStatus.COMPLETED
            
            # Parse due date
            due_date = None
            if 'due' in google_task:
                try:
                    due_date = parse_date(google_task['due'])
                except Exception as e:
                    logger.warning(f"Error parsing due date: {e}")
            
            # Create task
            task = task_manager.create_task(
                title=title,
                description=description,
                due_date=due_date,
                tags=["google-tasks"]
            )
            
            # Update status after creation
            task.update_status(status)
            
            # Store Google Tasks metadata
            task.metadata.update({
                'google_task_id': google_task.get('id'),
                'google_tasklist_id': google_task.get('parent'),
                'google_updated': google_task.get('updated'),
                'google_position': google_task.get('position')
            })
            
            return task
            
        except Exception as e:
            logger.error(f"Error converting Google Task: {e}")
            return None
    
    def export_task_to_google(self, task: Task, tasklist_id: Optional[str] = None) -> bool:
        if not self.is_authenticated():
            return False
        
        if not tasklist_id:
            # Use the default task list
            task_lists = self.get_task_lists()
            if not task_lists:
                logger.error("No task lists found for export")
                return False
            tasklist_id = task_lists[0]['id']
        
        try:
            google_task = {
                'title': task.title,
                'notes': task.description or '',
                'status': 'completed' if task.status == TaskStatus.COMPLETED else 'needsAction'
            }
            
            if task.due_date:
                google_task['due'] = task.due_date.isoformat()
            
            # Check if task already exists in Google Tasks
            if 'google_task_id' in task.metadata:
                # Update existing task
                result = self.service.tasks().update(
                    tasklist=tasklist_id,
                    task=task.metadata['google_task_id'],
                    body=google_task
                ).execute()
            else:
                # Create new task
                result = self.service.tasks().insert(
                    tasklist=tasklist_id,
                    body=google_task
                ).execute()
                
                # Update task metadata with Google Task ID
                task.metadata['google_task_id'] = result['id']
                task.metadata['google_tasklist_id'] = tasklist_id
            
            logger.info(f"Successfully exported task '{task.title}' to Google Tasks")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting task to Google Tasks: {e}")
            return False
    
    def sync_tasks_bidirectional(self, task_manager, tasklist_id: Optional[str] = None) -> Dict[str, int]:
        if not self.is_authenticated():
            return {"imported": 0, "exported": 0, "updated": 0}
        
        stats = {"imported": 0, "exported": 0, "updated": 0}
        
        # Import tasks from Google Tasks
        imported_tasks = self.import_tasks_from_google(task_manager, tasklist_id)
        stats["imported"] = len(imported_tasks)
        
        # Export local tasks to Google Tasks
        local_tasks = task_manager.get_all_tasks()
        for task in local_tasks:
            if 'google-tasks' not in task.tags:
                # This is a new local task, export it
                if self.export_task_to_google(task, tasklist_id):
                    task.add_tag('google-tasks')
                    stats["exported"] += 1
            else:
                # This task might need updating
                if self._should_update_google_task(task):
                    if self.export_task_to_google(task, tasklist_id):
                        stats["updated"] += 1
        
        return stats
    
    def _should_update_google_task(self, task: Task) -> bool:
        # Simple heuristic: if task was updated after last Google sync
        google_updated = task.metadata.get('google_updated')
        if not google_updated:
            return True
        
        try:
            google_update_time = parse_date(google_updated)
            return task.updated_at > google_update_time
        except Exception:
            return True
    
    def create_task_list(self, title: str) -> Optional[str]:
        if not self.is_authenticated():
            return None
        
        try:
            task_list = {
                'title': title
            }
            
            result = self.service.tasklists().insert(body=task_list).execute()
            logger.info(f"Created Google Tasks list: {title}")
            return result['id']
            
        except Exception as e:
            logger.error(f"Error creating task list: {e}")
            return None
    
    def delete_google_task(self, google_task_id: str, tasklist_id: str) -> bool:
        if not self.is_authenticated():
            return False
        
        try:
            self.service.tasks().delete(
                tasklist=tasklist_id,
                task=google_task_id
            ).execute()
            
            logger.info(f"Deleted Google Task: {google_task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting Google Task: {e}")
            return False
    
    def get_task_list_info(self, tasklist_id: str) -> Optional[Dict[str, Any]]:
        if not self.is_authenticated():
            return None
        
        try:
            task_list = self.service.tasklists().get(tasklist=tasklist_id).execute()
            return task_list
        except Exception as e:
            logger.error(f"Error fetching task list info: {e}")
            return None
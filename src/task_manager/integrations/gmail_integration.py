import base64
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import os
from ..core.task import Task, TaskPriority

logger = logging.getLogger(__name__)

class GmailIntegration:
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 
              'https://www.googleapis.com/auth/gmail.send']
    
    def __init__(self, credentials_file: str = "gmail_credentials.json", token_file: str = "gmail_token.json"):
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
                    logger.error(f"Gmail credentials file not found: {self.credentials_file}")
                    return
                
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open(self.token_file, 'w') as token:
                token.write(self.creds.to_json())
        
        try:
            self.service = build('gmail', 'v1', credentials=self.creds)
            logger.info("Successfully authenticated with Gmail")
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
    
    def is_authenticated(self) -> bool:
        return self.service is not None
    
    def search_emails_for_tasks(self, query: str = "is:unread", max_results: int = 10) -> List[Dict[str, Any]]:
        if not self.is_authenticated():
            logger.error("Gmail not authenticated")
            return []
        
        try:
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            email_tasks = []
            
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me', id=message['id'], format='full'
                ).execute()
                
                email_info = self._parse_email_for_task(msg)
                if email_info:
                    email_tasks.append(email_info)
            
            return email_tasks
            
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []
    
    def _parse_email_for_task(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            headers = message['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), None)
            
            # Extract body
            body = self._extract_email_body(message['payload'])
            
            # Determine priority based on keywords
            priority = self._determine_priority_from_email(subject, body)
            
            # Generate task title
            task_title = f"Email: {subject[:50]}..."
            
            # Create task description
            description = f"From: {sender}\n"
            if date:
                description += f"Date: {date}\n"
            description += f"Subject: {subject}\n\n"
            if body:
                description += f"Content:\n{body[:500]}..."
            
            return {
                "title": task_title,
                "description": description,
                "priority": priority,
                "tags": ["email", "gmail"],
                "metadata": {
                    "gmail_id": message['id'],
                    "gmail_thread_id": message['threadId'],
                    "sender": sender,
                    "subject": subject
                }
            }
            
        except Exception as e:
            logger.error(f"Error parsing email for task: {e}")
            return None
    
    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
        else:
            if payload['mimeType'] == 'text/plain' and 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        return body
    
    def _determine_priority_from_email(self, subject: str, body: str) -> TaskPriority:
        urgent_keywords = ['urgent', 'asap', 'emergency', 'critical', 'immediate']
        high_keywords = ['important', 'priority', 'deadline', 'due']
        
        text = (subject + " " + (body or "")).lower()
        
        if any(keyword in text for keyword in urgent_keywords):
            return TaskPriority.URGENT
        elif any(keyword in text for keyword in high_keywords):
            return TaskPriority.HIGH
        else:
            return TaskPriority.MEDIUM
    
    def create_tasks_from_emails(self, task_manager, query: str = "is:unread", max_results: int = 10) -> List[Task]:
        email_tasks = self.search_emails_for_tasks(query, max_results)
        created_tasks = []
        
        for email_info in email_tasks:
            task = task_manager.create_task(
                title=email_info["title"],
                description=email_info["description"],
                priority=email_info["priority"],
                tags=email_info["tags"]
            )
            task.metadata.update(email_info["metadata"])
            created_tasks.append(task)
        
        return created_tasks
    
    def send_task_summary_email(self, to_email: str, tasks: List[Task], subject: str = "Task Summary") -> bool:
        if not self.is_authenticated():
            logger.error("Gmail not authenticated")
            return False
        
        try:
            # Create email content
            body = self._create_task_summary_body(tasks)
            
            message = {
                'raw': base64.urlsafe_b64encode(
                    f"To: {to_email}\r\n"
                    f"Subject: {subject}\r\n"
                    f"Content-Type: text/plain; charset=utf-8\r\n\r\n"
                    f"{body}".encode('utf-8')
                ).decode('utf-8')
            }
            
            sent_message = self.service.users().messages().send(
                userId='me', body=message
            ).execute()
            
            logger.info(f"Task summary email sent successfully: {sent_message['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending task summary email: {e}")
            return False
    
    def _create_task_summary_body(self, tasks: List[Task]) -> str:
        if not tasks:
            return "No tasks to report."
        
        body = "Task Summary Report\n"
        body += "=" * 50 + "\n\n"
        
        # Group tasks by status
        status_groups = {}
        for task in tasks:
            status = task.status.value
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(task)
        
        for status, task_list in status_groups.items():
            body += f"{status.title()} Tasks ({len(task_list)}):\n"
            body += "-" * 30 + "\n"
            
            for i, task in enumerate(task_list, 1):
                body += f"{i}. {task.title}\n"
                if task.description and len(task.description) < 100:
                    body += f"   Description: {task.description}\n"
                body += f"   Priority: {task.priority.value.title()}\n"
                if task.due_date:
                    body += f"   Due: {task.due_date.strftime('%Y-%m-%d %H:%M')}\n"
                body += "\n"
            
            body += "\n"
        
        body += f"Total Tasks: {len(tasks)}\n"
        body += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        return body
    
    def mark_email_as_read(self, gmail_id: str) -> bool:
        if not self.is_authenticated():
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=gmail_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            return False
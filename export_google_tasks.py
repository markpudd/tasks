#!/usr/bin/env python3
"""
Google Tasks Export Script

This script exports Google Tasks to a JSON file that can be imported into the task management application.
It fetches all task lists and their tasks from Google Tasks API and formats them appropriately.

Requirements:
- Google Tasks API enabled in Google Cloud Console
- OAuth2 credentials (credentials.json)
- google-api-python-client library

Usage:
    python export_google_tasks.py [--output OUTPUT_FILE] [--format FORMAT]

Formats:
    - json: Export as JSON file (default)
    - csv: Export as CSV file
"""

import argparse
import json
import csv
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
import pickle

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Error: Google API client library not installed.")
    print("Please install it with: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
    sys.exit(1)

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/tasks.readonly']

class GoogleTasksExporter:
    def __init__(self, credentials_file='credentials.json', token_file='token.pickle'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        
    def authenticate(self):
        """Authenticate with Google Tasks API"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    print(f"Error: {self.credentials_file} not found.")
                    print("Please download your OAuth2 credentials from Google Cloud Console.")
                    print("Go to: https://console.cloud.google.com/apis/credentials")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('tasks', 'v1', credentials=creds)
        return True
    
    def get_task_lists(self) -> List[Dict[str, Any]]:
        """Get all task lists from Google Tasks"""
        try:
            results = self.service.tasklists().list().execute()
            items = results.get('items', [])
            
            print(f"Found {len(items)} task lists:")
            for item in items:
                print(f"  - {item['title']} (ID: {item['id']})")
            
            return items
        except HttpError as error:
            print(f"An error occurred while fetching task lists: {error}")
            return []
    
    def get_tasks_from_list(self, tasklist_id: str) -> List[Dict[str, Any]]:
        """Get all tasks from a specific task list"""
        try:
            results = self.service.tasks().list(
                tasklist=tasklist_id,
                showCompleted=True,
                showHidden=True
            ).execute()
            return results.get('items', [])
        except HttpError as error:
            print(f"An error occurred while fetching tasks: {error}")
            return []
    
    def convert_google_task_to_app_format(self, gtask: Dict[str, Any], project_name: str) -> Dict[str, Any]:
        """Convert a Google Task to the application's task format"""
        
        # Map Google Tasks status to application status
        status_mapping = {
            'needsAction': 'pending',
            'completed': 'completed'
        }
        
        # Parse due date if present
        due_date = None
        if 'due' in gtask:
            try:
                # Google Tasks due date format: "2023-12-25T00:00:00.000Z"
                due_date = datetime.fromisoformat(gtask['due'].replace('Z', '+00:00')).isoformat()
            except:
                pass
        
        # Parse completed date
        completed_date = None
        if 'completed' in gtask:
            try:
                completed_date = datetime.fromisoformat(gtask['completed'].replace('Z', '+00:00')).isoformat()
            except:
                pass
        
        # Determine category (default to personal, could be enhanced with AI or keywords)
        category = 'personal'
        title_lower = gtask.get('title', '').lower()
        work_keywords = ['work', 'meeting', 'project', 'client', 'business', 'office', 'task', 'deadline']
        if any(keyword in title_lower for keyword in work_keywords):
            category = 'work'
        
        # Determine priority based on title/notes content
        priority = 'medium'
        title_notes = (gtask.get('title', '') + ' ' + gtask.get('notes', '')).lower()
        if any(word in title_notes for word in ['urgent', 'asap', 'critical', 'emergency', '!!!', 'high priority']):
            priority = 'urgent'
        elif any(word in title_notes for word in ['important', 'priority', 'soon', '!!']):
            priority = 'high'
        elif any(word in title_notes for word in ['later', 'someday', 'maybe', 'low priority']):
            priority = 'low'
        
        # Extract tags from title/notes (look for #hashtags)
        tags = []
        import re
        text_content = (gtask.get('title', '') + ' ' + gtask.get('notes', ''))
        hashtags = re.findall(r'#(\w+)', text_content)
        tags.extend(hashtags)
        
        # Clean title (remove hashtags)
        clean_title = re.sub(r'#\w+', '', gtask.get('title', '')).strip()
        
        return {
            'id': f"gtask_{gtask['id']}",  # Prefix to avoid ID conflicts
            'title': clean_title or 'Untitled Task',
            'description': gtask.get('notes', ''),
            'status': status_mapping.get(gtask.get('status', 'needsAction'), 'pending'),
            'priority': priority,
            'category': category,
            'project': project_name,
            'project_id': None,  # Will be assigned during import
            'due_date': due_date,
            'tags': tags,
            'created_at': gtask.get('updated', datetime.now().isoformat()),  # Use updated as created_at
            'updated_at': gtask.get('updated', datetime.now().isoformat()),
            'metadata': {
                'source': 'google_tasks',
                'original_id': gtask['id'],
                'original_list': project_name,
                'completed_date': completed_date,
                'parent': gtask.get('parent'),  # For subtasks
                'position': gtask.get('position')
            }
        }
    
    def export_to_json(self, output_file: str) -> bool:
        """Export all Google Tasks to JSON format"""
        if not self.authenticate():
            return False
        
        task_lists = self.get_task_lists()
        if not task_lists:
            print("No task lists found.")
            return False
        
        all_tasks = []
        
        for task_list in task_lists:
            list_title = task_list['title']
            list_id = task_list['id']
            
            print(f"\\nProcessing task list: {list_title}")
            tasks = self.get_tasks_from_list(list_id)
            
            print(f"  Found {len(tasks)} tasks")
            
            for gtask in tasks:
                app_task = self.convert_google_task_to_app_format(gtask, list_title)
                all_tasks.append(app_task)
        
        # Write to JSON file
        export_data = {
            'export_info': {
                'source': 'google_tasks',
                'export_date': datetime.now().isoformat(),
                'total_tasks': len(all_tasks),
                'total_lists': len(task_lists)
            },
            'tasks': all_tasks
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"\\n✅ Successfully exported {len(all_tasks)} tasks to {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error writing to file: {e}")
            return False
    
    def export_to_csv(self, output_file: str) -> bool:
        """Export all Google Tasks to CSV format"""
        if not self.authenticate():
            return False
        
        task_lists = self.get_task_lists()
        if not task_lists:
            print("No task lists found.")
            return False
        
        all_tasks = []
        
        for task_list in task_lists:
            list_title = task_list['title']
            list_id = task_list['id']
            
            print(f"\\nProcessing task list: {list_title}")
            tasks = self.get_tasks_from_list(list_id)
            
            for gtask in tasks:
                app_task = self.convert_google_task_to_app_format(gtask, list_title)
                all_tasks.append(app_task)
        
        # Write to CSV file
        if all_tasks:
            fieldnames = ['title', 'description', 'status', 'priority', 'category', 'project', 
                         'due_date', 'tags', 'created_at', 'updated_at']
            
            try:
                with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for task in all_tasks:
                        # Flatten the task for CSV
                        csv_task = {key: task.get(key, '') for key in fieldnames}
                        csv_task['tags'] = ','.join(task.get('tags', []))
                        writer.writerow(csv_task)
                
                print(f"\\n✅ Successfully exported {len(all_tasks)} tasks to {output_file}")
                return True
                
            except Exception as e:
                print(f"❌ Error writing to CSV file: {e}")
                return False
        else:
            print("No tasks found to export.")
            return False

def main():
    parser = argparse.ArgumentParser(description='Export Google Tasks to file for import into task management app')
    parser.add_argument('--output', '-o', default='google_tasks_export.json', 
                       help='Output filename (default: google_tasks_export.json)')
    parser.add_argument('--format', '-f', choices=['json', 'csv'], default='json',
                       help='Export format: json or csv (default: json)')
    parser.add_argument('--credentials', '-c', default='credentials.json',
                       help='Google OAuth2 credentials file (default: credentials.json)')
    
    args = parser.parse_args()
    
    print("Google Tasks Exporter")
    print("=" * 50)
    
    exporter = GoogleTasksExporter(credentials_file=args.credentials)
    
    if args.format == 'json':
        success = exporter.export_to_json(args.output)
    else:
        success = exporter.export_to_csv(args.output)
    
    if success:
        print(f"\\n🎉 Export completed successfully!")
        print(f"📁 File: {args.output}")
        print(f"\\nTo import into the task management app:")
        print(f"1. Copy {args.output} to your task manager directory")
        print(f"2. Use the import feature in the web interface")
        print(f"3. Or manually merge the tasks into your tasks_[user_id].json file")
    else:
        print("\\n❌ Export failed. Please check the errors above.")
        sys.exit(1)

if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
Google Tasks Import Script for Task Management Application (API Version)

This script imports tasks from a Google Tasks export file into a remote task management 
application using the REST API endpoint. It supports authentication and remote server import.

Usage:
    python import_google_tasks_api.py --input EXPORT_FILE --server SERVER_URL --username USERNAME --password PASSWORD [--dry-run]

Example:
    python import_google_tasks_api.py --input google_tasks_export.json --server http://localhost:5000 --username admin --password mypass
"""

import argparse
import json
import sys
import requests
from datetime import datetime
from typing import Dict, List, Any
import urllib3

# Disable SSL warnings for local development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class GoogleTasksAPIImporter:
    def __init__(self, server_url: str, username: str, password: str, verify_ssl: bool = True):
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.imported_count = 0
        self.skipped_count = 0
        self.projects_created = 0
        self.errors = []
        
    def authenticate(self) -> bool:
        """Authenticate with the remote server"""
        try:
            # First try to access login page to get any CSRF tokens
            login_url = f"{self.server_url}/login"
            response = self.session.get(login_url, verify=self.verify_ssl)
            
            if response.status_code != 200:
                print(f"❌ Failed to access login page: {response.status_code}")
                return False
            
            # Attempt login
            login_data = {
                'username': self.username,
                'password': self.password
            }
            
            response = self.session.post(
                login_url, 
                data=login_data, 
                verify=self.verify_ssl,
                allow_redirects=False
            )
            
            # Check if login was successful (redirect or 200 status)
            if response.status_code in [200, 302, 303]:
                print("✅ Successfully authenticated with server")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                if response.text:
                    print(f"Response: {response.text[:200]}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ Error connecting to server: {e}")
            return False
    
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
    
    def import_tasks_via_api(self, export_data: Dict[str, Any], dry_run: bool = False) -> bool:
        """Import all tasks via the REST API"""
        
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
        
        print(f"\\n🚀 {'[DRY RUN] ' if dry_run else ''}Starting API import...")
        print(f"📥 Processing {len(tasks)} tasks...")
        
        if dry_run:
            print("\\n[DRY RUN] Would send the following data to the API:")
            # Group tasks by project for preview
            tasks_by_project = {}
            for task in tasks:
                project_key = f"{task.get('project', 'Imported Tasks')}:{task.get('category', 'personal')}"
                if project_key not in tasks_by_project:
                    tasks_by_project[project_key] = []
                tasks_by_project[project_key].append(task)
            
            print(f"📁 Would create {len(tasks_by_project)} unique projects/categories")
            for project_key, project_tasks in tasks_by_project.items():
                project_name, category = project_key.split(':', 1)
                print(f"  📁 {project_name} ({category}) - {len(project_tasks)} tasks")
                for task in project_tasks[:3]:  # Show first 3 tasks
                    print(f"    - {task.get('title', 'Untitled')}")
                if len(project_tasks) > 3:
                    print(f"    ... and {len(project_tasks) - 3} more tasks")
            
            self.imported_count = len(tasks)
            return True
        
        # Make API call to import
        try:
            import_url = f"{self.server_url}/api/import/google-tasks"
            headers = {
                'Content-Type': 'application/json'
            }
            
            print(f"📡 Sending import request to: {import_url}")
            response = self.session.post(
                import_url,
                json=export_data,
                headers=headers,
                verify=self.verify_ssl,
                timeout=120  # 2 minute timeout for large imports
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.imported_count = result.get('imported_count', 0)
                    self.skipped_count = result.get('skipped_count', 0)
                    self.projects_created = result.get('projects_created', 0)
                    self.errors = result.get('errors', [])
                    
                    print("✅ Import completed successfully!")
                    return True
                else:
                    print(f"❌ Import failed: {result.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ API request failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.Timeout:
            print("❌ Import request timed out. The import may still be processing on the server.")
            return False
        except requests.RequestException as e:
            print(f"❌ Error making API request: {e}")
            return False
    
    def print_summary(self, dry_run: bool = False):
        """Print import summary"""
        print("\\n" + "="*50)
        print(f"🎉 {'[DRY RUN] ' if dry_run else ''}Import Summary")
        print("="*50)
        print(f"✅ Tasks imported: {self.imported_count}")
        print(f"⏩ Tasks skipped: {self.skipped_count}")
        print(f"📁 Projects created: {self.projects_created}")
        
        if self.errors:
            print(f"\\n⚠️  Errors encountered:")
            for error in self.errors:
                print(f"  - {error}")
        
        if not dry_run and self.imported_count > 0:
            print(f"\\n🌐 Tasks successfully imported to: {self.server_url}")
            print("🌐 You can now view the imported tasks in the web interface!")

def main():
    parser = argparse.ArgumentParser(description='Import Google Tasks export into remote task management app via API')
    parser.add_argument('--input', '-i', required=True,
                       help='Input file (Google Tasks export JSON)')
    parser.add_argument('--server', '-s', required=True,
                       help='Server URL (e.g., http://localhost:5000 or https://mytasks.example.com)')
    parser.add_argument('--username', '-u', required=True,
                       help='Username for authentication')
    parser.add_argument('--password', '-p', required=True,
                       help='Password for authentication')
    parser.add_argument('--dry-run', '-d', action='store_true',
                       help='Show what would be imported without actually importing')
    parser.add_argument('--no-ssl-verify', action='store_true',
                       help='Disable SSL certificate verification (for local development only)')
    
    args = parser.parse_args()
    
    print("Google Tasks API Importer")
    print("=" * 50)
    print(f"📁 Input file: {args.input}")
    print(f"🌐 Server: {args.server}")
    print(f"👤 Username: {args.username}")
    
    if args.dry_run:
        print("🧪 DRY RUN MODE - No changes will be made")
    
    if args.no_ssl_verify:
        print("⚠️  SSL verification disabled")
    
    # Initialize importer
    importer = GoogleTasksAPIImporter(
        server_url=args.server,
        username=args.username,
        password=args.password,
        verify_ssl=not args.no_ssl_verify
    )
    
    # Authenticate
    if not args.dry_run:
        if not importer.authenticate():
            print("❌ Authentication failed. Please check your credentials and server URL.")
            sys.exit(1)
    
    # Load export file
    export_data = importer.load_export_file(args.input)
    if not export_data:
        sys.exit(1)
    
    # Import tasks
    success = importer.import_tasks_via_api(export_data, dry_run=args.dry_run)
    
    # Print summary
    importer.print_summary(dry_run=args.dry_run)
    
    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main()
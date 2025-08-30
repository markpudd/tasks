import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional, List
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init()

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..core import Task, TaskManager, TaskStatus, TaskPriority, TaskCategory
from ..printer import ReceiptPrinter
from ..llm import OpenAILLM, GeminiLLM
from ..integrations import GmailIntegration, GoogleTasksIntegration

logger = logging.getLogger(__name__)

class TaskManagerCLI:
    def __init__(self):
        self.task_manager = TaskManager()
        self.printer = None
        self.llm = None
        self.gmail = None
        self.google_tasks = None
        self.config = self._load_config()
        self._setup_integrations()
    
    def _load_config(self) -> dict:
        config_file = "config.json"
        default_config = {
            "printer": {
                "type": "usb",
                "vendor_id": "0x04b8",
                "product_id": "0x0202"
            },
            "llm": {
                "provider": "openai",
                "model": "gpt-3.5-turbo"
            },
            "integrations": {
                "gmail_enabled": False,
                "google_tasks_enabled": False
            }
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        
        return default_config
    
    def _setup_integrations(self):
        # Setup printer
        try:
            printer_config = self.config.get("printer", {})
            if printer_config.get("type") == "usb":
                vendor_id = int(printer_config.get("vendor_id", "0x04b8"), 16)
                product_id = int(printer_config.get("product_id", "0x0202"), 16)
                self.printer = ReceiptPrinter("usb", vendor_id=vendor_id, product_id=product_id)
            elif printer_config.get("type") == "network":
                self.printer = ReceiptPrinter("network", 
                                            host=printer_config.get("host", "192.168.1.100"),
                                            port=printer_config.get("port", 9100))
        except Exception as e:
            logger.warning(f"Printer setup failed: {e}")
        
        # Setup LLM
        llm_config = self.config.get("llm", {})
        api_key = os.getenv("OPENAI_API_KEY") if llm_config.get("provider") == "openai" else os.getenv("GEMINI_API_KEY")
        
        if api_key:
            try:
                if llm_config.get("provider") == "openai":
                    self.llm = OpenAILLM(api_key, llm_config.get("model", "gpt-3.5-turbo"))
                elif llm_config.get("provider") == "gemini":
                    self.llm = GeminiLLM(api_key, llm_config.get("model", "gemini-pro"))
            except Exception as e:
                logger.warning(f"LLM setup failed: {e}")
        
        # Setup Gmail
        if self.config.get("integrations", {}).get("gmail_enabled"):
            try:
                self.gmail = GmailIntegration()
            except Exception as e:
                logger.warning(f"Gmail integration setup failed: {e}")
        
        # Setup Google Tasks
        if self.config.get("integrations", {}).get("google_tasks_enabled"):
            try:
                self.google_tasks = GoogleTasksIntegration()
            except Exception as e:
                logger.warning(f"Google Tasks integration setup failed: {e}")
    
    def run(self):
        parser = argparse.ArgumentParser(description="Task Management System")
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Task management commands
        self._add_task_commands(subparsers)
        
        # Printer commands
        self._add_printer_commands(subparsers)
        
        # LLM commands
        self._add_llm_commands(subparsers)
        
        # Integration commands
        self._add_integration_commands(subparsers)
        
        # Configuration commands
        self._add_config_commands(subparsers)
        
        args = parser.parse_args()
        
        if not args.command:
            self._interactive_mode()
        else:
            self._handle_command(args)
    
    def _add_task_commands(self, subparsers):
        # Create task
        create_parser = subparsers.add_parser('create', help='Create a new task')
        create_parser.add_argument('title', help='Task title')
        create_parser.add_argument('--description', '-d', help='Task description')
        create_parser.add_argument('--priority', '-p', choices=['low', 'medium', 'high', 'urgent'], 
                                 default='medium', help='Task priority')
        create_parser.add_argument('--category', '-c', choices=['personal', 'work'],
                                 default='personal', help='Task category')
        create_parser.add_argument('--project', help='Project name')
        create_parser.add_argument('--due-date', help='Due date (YYYY-MM-DD HH:MM)')
        create_parser.add_argument('--tags', nargs='+', help='Task tags')
        
        # List tasks
        list_parser = subparsers.add_parser('list', help='List tasks')
        list_parser.add_argument('--status', choices=['pending', 'in_progress', 'completed', 'cancelled'])
        list_parser.add_argument('--priority', choices=['low', 'medium', 'high', 'urgent'])
        list_parser.add_argument('--category', choices=['personal', 'work'])
        list_parser.add_argument('--project', help='Filter by project')
        list_parser.add_argument('--tag', help='Filter by tag')
        
        # Update task
        update_parser = subparsers.add_parser('update', help='Update task status')
        update_parser.add_argument('task_id', help='Task ID')
        update_parser.add_argument('status', choices=['pending', 'in_progress', 'completed', 'cancelled'])
        
        # Delete task
        delete_parser = subparsers.add_parser('delete', help='Delete a task')
        delete_parser.add_argument('task_id', help='Task ID')
        
        # Search tasks
        search_parser = subparsers.add_parser('search', help='Search tasks')
        search_parser.add_argument('query', help='Search query')
        
        # Show task details
        show_parser = subparsers.add_parser('show', help='Show task details')
        show_parser.add_argument('task_id', help='Task ID')
        
        # Statistics
        subparsers.add_parser('stats', help='Show task statistics')
    
    def _add_printer_commands(self, subparsers):
        # Print task
        print_parser = subparsers.add_parser('print', help='Print task to receipt printer')
        print_parser.add_argument('task_id', help='Task ID')
        
        # Print task list
        print_list_parser = subparsers.add_parser('print-list', help='Print task list')
        print_list_parser.add_argument('--status', choices=['pending', 'in_progress', 'completed', 'cancelled'])
        
        # Test printer
        subparsers.add_parser('test-printer', help='Test receipt printer')
    
    def _add_llm_commands(self, subparsers):
        # AI suggestions
        ai_parser = subparsers.add_parser('ai', help='AI assistance commands')
        ai_subparsers = ai_parser.add_subparsers(dest='ai_command')
        
        # Prioritize tasks
        ai_subparsers.add_parser('prioritize', help='Get AI task prioritization suggestions')
        
        # Break down task
        breakdown_parser = ai_subparsers.add_parser('breakdown', help='Break down a task into subtasks')
        breakdown_parser.add_argument('task_id', help='Task ID')
        
        # Find similar tasks
        similar_parser = ai_subparsers.add_parser('similar', help='Find similar tasks')
        similar_parser.add_argument('task_id', help='Task ID')
        
        # Generate task suggestions
        suggest_parser = ai_subparsers.add_parser('suggest', help='Generate new task suggestions')
        suggest_parser.add_argument('context', help='Context for suggestions')
    
    def _add_integration_commands(self, subparsers):
        # Gmail integration
        gmail_parser = subparsers.add_parser('gmail', help='Gmail integration commands')
        gmail_subparsers = gmail_parser.add_subparsers(dest='gmail_command')
        
        gmail_subparsers.add_parser('import', help='Import tasks from Gmail')
        
        send_parser = gmail_subparsers.add_parser('send-summary', help='Send task summary via email')
        send_parser.add_argument('email', help='Recipient email address')
        
        # Google Tasks integration
        gtasks_parser = subparsers.add_parser('gtasks', help='Google Tasks integration commands')
        gtasks_subparsers = gtasks_parser.add_subparsers(dest='gtasks_command')
        
        gtasks_subparsers.add_parser('import', help='Import from Google Tasks')
        gtasks_subparsers.add_parser('export', help='Export to Google Tasks')
        gtasks_subparsers.add_parser('sync', help='Bidirectional sync with Google Tasks')
        gtasks_subparsers.add_parser('lists', help='List Google Task lists')
    
    def _add_config_commands(self, subparsers):
        # Configuration
        config_parser = subparsers.add_parser('config', help='Configuration commands')
        config_subparsers = config_parser.add_subparsers(dest='config_command')
        
        config_subparsers.add_parser('show', help='Show current configuration')
        
        set_parser = config_subparsers.add_parser('set', help='Set configuration value')
        set_parser.add_argument('key', help='Configuration key')
        set_parser.add_argument('value', help='Configuration value')
    
    def _handle_command(self, args):
        try:
            if args.command == 'create':
                self._create_task(args)
            elif args.command == 'list':
                self._list_tasks(args)
            elif args.command == 'update':
                self._update_task(args)
            elif args.command == 'delete':
                self._delete_task(args)
            elif args.command == 'search':
                self._search_tasks(args)
            elif args.command == 'show':
                self._show_task(args)
            elif args.command == 'stats':
                self._show_statistics()
            elif args.command == 'print':
                self._print_task(args)
            elif args.command == 'print-list':
                self._print_task_list(args)
            elif args.command == 'test-printer':
                self._test_printer()
            elif args.command == 'ai':
                self._handle_ai_command(args)
            elif args.command == 'gmail':
                self._handle_gmail_command(args)
            elif args.command == 'gtasks':
                self._handle_gtasks_command(args)
            elif args.command == 'config':
                self._handle_config_command(args)
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
            logger.error(f"Command error: {e}")
    
    def _create_task(self, args):
        priority = TaskPriority[args.priority.upper()]
        category = TaskCategory[args.category.upper()]
        due_date = None
        if args.due_date:
            due_date = datetime.strptime(args.due_date, "%Y-%m-%d %H:%M")
        
        task = self.task_manager.create_task(
            title=args.title,
            description=args.description,
            priority=priority,
            category=category,
            project=args.project,
            due_date=due_date,
            tags=args.tags or []
        )
        
        print(f"{Fore.GREEN}Task created successfully!{Style.RESET_ALL}")
        print(f"ID: {task.id}")
        print(f"Title: {task.title}")
    
    def _list_tasks(self, args):
        if args.status:
            tasks = self.task_manager.get_tasks_by_status(TaskStatus[args.status.upper()])
        elif args.priority:
            tasks = self.task_manager.get_tasks_by_priority(TaskPriority[args.priority.upper()])
        elif args.category:
            tasks = self.task_manager.get_tasks_by_category(TaskCategory[args.category.upper()])
        elif args.project:
            tasks = self.task_manager.get_tasks_by_project(args.project)
        elif args.tag:
            tasks = self.task_manager.get_tasks_by_tag(args.tag)
        else:
            tasks = self.task_manager.get_all_tasks()
        
        if not tasks:
            print("No tasks found.")
            return
        
        print(f"\n{Fore.CYAN}Tasks ({len(tasks)}){Style.RESET_ALL}")
        print("-" * 50)
        
        for task in sorted(tasks, key=lambda t: t.created_at):
            status_color = {
                TaskStatus.PENDING: Fore.YELLOW,
                TaskStatus.IN_PROGRESS: Fore.BLUE,
                TaskStatus.COMPLETED: Fore.GREEN,
                TaskStatus.CANCELLED: Fore.RED
            }.get(task.status, Fore.WHITE)
            
            print(f"{status_color}{task.status.value:<12}{Style.RESET_ALL} | {task.title[:50]}")
            print(f"{'ID: ' + task.id[:8]:<12} | Priority: {task.priority.value} | Category: {task.category.value}")
            if task.project:
                print(f"{'Project:':<12} | {task.project}")
            if task.due_date:
                print(f"{'Due:':<12} | {task.due_date.strftime('%Y-%m-%d %H:%M')}")
            print()
    
    def _update_task(self, args):
        if self.task_manager.update_task_status(args.task_id, TaskStatus[args.status.upper()]):
            print(f"{Fore.GREEN}Task status updated successfully!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Task not found.{Style.RESET_ALL}")
    
    def _delete_task(self, args):
        if self.task_manager.delete_task(args.task_id):
            print(f"{Fore.GREEN}Task deleted successfully!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Task not found.{Style.RESET_ALL}")
    
    def _search_tasks(self, args):
        tasks = self.task_manager.search_tasks(args.query)
        
        if not tasks:
            print("No matching tasks found.")
            return
        
        print(f"\n{Fore.CYAN}Search Results ({len(tasks)}){Style.RESET_ALL}")
        print("-" * 50)
        
        for task in tasks:
            print(f"{task.title}")
            print(f"ID: {task.id[:8]} | Status: {task.status.value} | Priority: {task.priority.value}")
            if task.description:
                print(f"Description: {task.description[:100]}...")
            print()
    
    def _show_task(self, args):
        task = self.task_manager.get_task(args.task_id)
        if not task:
            print(f"{Fore.RED}Task not found.{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}Task Details{Style.RESET_ALL}")
        print("=" * 50)
        print(f"ID: {task.id}")
        print(f"Title: {task.title}")
        print(f"Description: {task.description or 'None'}")
        print(f"Status: {task.status.value}")
        print(f"Priority: {task.priority.value}")
        print(f"Category: {task.category.value}")
        if task.project:
            print(f"Project: {task.project}")
        print(f"Created: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Updated: {task.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if task.due_date:
            print(f"Due: {task.due_date.strftime('%Y-%m-%d %H:%M:%S')}")
        if task.tags:
            print(f"Tags: {', '.join(task.tags)}")
    
    def _show_statistics(self):
        stats = self.task_manager.get_statistics()
        
        print(f"\n{Fore.CYAN}Task Statistics{Style.RESET_ALL}")
        print("=" * 30)
        print(f"Total Tasks: {stats['total']}")
        print(f"Overdue Tasks: {stats['overdue']}")
        print()
        
        print("By Status:")
        for status, count in stats['by_status'].items():
            print(f"  {status.title()}: {count}")
        
        print("\nBy Priority:")
        for priority, count in stats['by_priority'].items():
            print(f"  {priority.title()}: {count}")
        
        print("\nBy Category:")
        for category, count in stats['by_category'].items():
            print(f"  {category.title()}: {count}")
        
        if stats['by_project']:
            print("\nBy Project:")
            for project, count in stats['by_project'].items():
                print(f"  {project}: {count}")
        
        print(f"\nTotal Projects: {stats['total_projects']}")
    
    def _print_task(self, args):
        if not self.printer or not self.printer.is_connected():
            print(f"{Fore.RED}Printer not connected.{Style.RESET_ALL}")
            return
        
        task = self.task_manager.get_task(args.task_id)
        if not task:
            print(f"{Fore.RED}Task not found.{Style.RESET_ALL}")
            return
        
        if self.printer.print_task(task):
            print(f"{Fore.GREEN}Task printed successfully!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed to print task.{Style.RESET_ALL}")
    
    def _print_task_list(self, args):
        if not self.printer or not self.printer.is_connected():
            print(f"{Fore.RED}Printer not connected.{Style.RESET_ALL}")
            return
        
        if args.status:
            tasks = self.task_manager.get_tasks_by_status(TaskStatus[args.status.upper()])
            title = f"{args.status.upper()} TASKS"
        else:
            tasks = self.task_manager.get_all_tasks()
            title = "ALL TASKS"
        
        if self.printer.print_task_list(tasks, title):
            print(f"{Fore.GREEN}Task list printed successfully!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed to print task list.{Style.RESET_ALL}")
    
    def _test_printer(self):
        if not self.printer:
            print(f"{Fore.RED}Printer not configured.{Style.RESET_ALL}")
            return
        
        if not self.printer.is_connected():
            print(f"{Fore.RED}Printer not connected.{Style.RESET_ALL}")
            return
        
        if self.printer.test_print():
            print(f"{Fore.GREEN}Printer test successful!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Printer test failed.{Style.RESET_ALL}")
    
    def _handle_ai_command(self, args):
        if not self.llm:
            print(f"{Fore.RED}LLM not configured. Set OPENAI_API_KEY or GEMINI_API_KEY.{Style.RESET_ALL}")
            return
        
        if args.ai_command == 'prioritize':
            self._ai_prioritize()
        elif args.ai_command == 'breakdown':
            self._ai_breakdown(args.task_id)
        elif args.ai_command == 'similar':
            self._ai_similar(args.task_id)
        elif args.ai_command == 'suggest':
            self._ai_suggest(args.context)
    
    def _ai_prioritize(self):
        tasks = self.task_manager.get_all_tasks()
        if not tasks:
            print("No tasks to prioritize.")
            return
        
        print("Getting AI prioritization suggestions...")
        suggestions = self.llm.suggest_task_prioritization(tasks)
        
        print(f"\n{Fore.CYAN}AI Prioritization Suggestions{Style.RESET_ALL}")
        print("=" * 50)
        
        for i, suggestion in enumerate(suggestions, 1):
            task = suggestion['task']
            print(f"{i}. {task.title}")
            print(f"   Reasoning: {suggestion['reasoning']}")
            print()
    
    def _ai_breakdown(self, task_id):
        task = self.task_manager.get_task(task_id)
        if not task:
            print(f"{Fore.RED}Task not found.{Style.RESET_ALL}")
            return
        
        print("Getting AI task breakdown suggestions...")
        subtasks = self.llm.suggest_task_breakdown(task)
        
        print(f"\n{Fore.CYAN}Task Breakdown for: {task.title}{Style.RESET_ALL}")
        print("=" * 50)
        
        for i, subtask in enumerate(subtasks, 1):
            print(f"{i}. {subtask}")
    
    def _ai_similar(self, task_id):
        task = self.task_manager.get_task(task_id)
        if not task:
            print(f"{Fore.RED}Task not found.{Style.RESET_ALL}")
            return
        
        all_tasks = self.task_manager.get_all_tasks()
        similar_tasks = self.llm.suggest_similar_tasks(task, all_tasks)
        
        print(f"\n{Fore.CYAN}Similar Tasks to: {task.title}{Style.RESET_ALL}")
        print("=" * 50)
        
        for similar_task in similar_tasks:
            print(f"• {similar_task.title}")
            print(f"  Status: {similar_task.status.value} | Priority: {similar_task.priority.value}")
            print()
    
    def _ai_suggest(self, context):
        existing_tasks = self.task_manager.get_all_tasks()
        suggestions = self.llm.generate_task_suggestions(context, existing_tasks)
        
        print(f"\n{Fore.CYAN}AI Task Suggestions for: {context}{Style.RESET_ALL}")
        print("=" * 50)
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")
    
    def _handle_gmail_command(self, args):
        if not self.gmail or not self.gmail.is_authenticated():
            print(f"{Fore.RED}Gmail not configured or not authenticated.{Style.RESET_ALL}")
            return
        
        if args.gmail_command == 'import':
            print("Importing tasks from Gmail...")
            tasks = self.gmail.create_tasks_from_emails(self.task_manager)
            print(f"{Fore.GREEN}Imported {len(tasks)} tasks from Gmail.{Style.RESET_ALL}")
        
        elif args.gmail_command == 'send-summary':
            tasks = self.task_manager.get_all_tasks()
            if self.gmail.send_task_summary_email(args.email, tasks):
                print(f"{Fore.GREEN}Task summary sent to {args.email}.{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Failed to send task summary.{Style.RESET_ALL}")
    
    def _handle_gtasks_command(self, args):
        if not self.google_tasks or not self.google_tasks.is_authenticated():
            print(f"{Fore.RED}Google Tasks not configured or not authenticated.{Style.RESET_ALL}")
            return
        
        if args.gtasks_command == 'import':
            print("Importing tasks from Google Tasks...")
            tasks = self.google_tasks.import_tasks_from_google(self.task_manager)
            print(f"{Fore.GREEN}Imported {len(tasks)} tasks from Google Tasks.{Style.RESET_ALL}")
        
        elif args.gtasks_command == 'export':
            tasks = self.task_manager.get_all_tasks()
            count = 0
            for task in tasks:
                if self.google_tasks.export_task_to_google(task):
                    count += 1
            print(f"{Fore.GREEN}Exported {count} tasks to Google Tasks.{Style.RESET_ALL}")
        
        elif args.gtasks_command == 'sync':
            print("Syncing with Google Tasks...")
            stats = self.google_tasks.sync_tasks_bidirectional(self.task_manager)
            print(f"{Fore.GREEN}Sync complete:{Style.RESET_ALL}")
            print(f"  Imported: {stats['imported']}")
            print(f"  Exported: {stats['exported']}")
            print(f"  Updated: {stats['updated']}")
        
        elif args.gtasks_command == 'lists':
            task_lists = self.google_tasks.get_task_lists()
            print(f"\n{Fore.CYAN}Google Task Lists{Style.RESET_ALL}")
            print("-" * 30)
            for task_list in task_lists:
                print(f"• {task_list['title']} (ID: {task_list['id']})")
    
    def _handle_config_command(self, args):
        if args.config_command == 'show':
            print(f"\n{Fore.CYAN}Current Configuration{Style.RESET_ALL}")
            print("=" * 30)
            print(json.dumps(self.config, indent=2))
        
        elif args.config_command == 'set':
            # Simple key-value setting (would need more sophisticated parsing for nested values)
            print(f"Configuration setting not implemented yet.")
    
    def _interactive_mode(self):
        print(f"{Fore.CYAN}Task Manager - Interactive Mode{Style.RESET_ALL}")
        print("Type 'help' for available commands or 'exit' to quit.")
        
        while True:
            try:
                command = input(f"\n{Fore.GREEN}> {Style.RESET_ALL}").strip()
                
                if command.lower() in ['exit', 'quit']:
                    break
                elif command.lower() == 'help':
                    self._show_help()
                elif command:
                    # Parse and execute command
                    sys.argv = ['task_manager'] + command.split()
                    self.run()
                    
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Goodbye!{Style.RESET_ALL}")
                break
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
    
    def _show_help(self):
        help_text = f"""
{Fore.CYAN}Task Manager Commands{Style.RESET_ALL}

{Fore.YELLOW}Task Management:{Style.RESET_ALL}
  create <title> [options]     Create a new task
  list [filters]               List tasks
  update <id> <status>         Update task status
  delete <id>                  Delete a task
  search <query>               Search tasks
  show <id>                    Show task details
  stats                        Show statistics

{Fore.YELLOW}Printer:{Style.RESET_ALL}
  print <id>                   Print task to receipt printer
  print-list [filters]         Print task list
  test-printer                 Test printer connection

{Fore.YELLOW}AI Assistance:{Style.RESET_ALL}
  ai prioritize                Get prioritization suggestions
  ai breakdown <id>            Break down task into subtasks
  ai similar <id>              Find similar tasks
  ai suggest <context>         Generate task suggestions

{Fore.YELLOW}Integrations:{Style.RESET_ALL}
  gmail import                 Import tasks from Gmail
  gmail send-summary <email>   Send task summary via email
  gtasks import/export/sync    Google Tasks integration
  gtasks lists                 List Google Task lists

{Fore.YELLOW}General:{Style.RESET_ALL}
  config show                  Show configuration
  help                         Show this help
  exit                         Exit program
        """
        print(help_text)

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        cli = TaskManagerCLI()
        cli.run()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Goodbye!{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {e}{Style.RESET_ALL}")
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
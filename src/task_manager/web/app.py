from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List
from functools import wraps

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..core import TaskManager, Task, TaskStatus, TaskPriority, TaskCategory
from ..core.auth import UserManager, User
from ..core.project_manager import ProjectManager
from ..printer import ReceiptPrinter
from ..llm import OpenAILLM, GeminiLLM
from ..integrations import GmailIntegration, GoogleTasksIntegration

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global instances
user_manager = UserManager()
task_managers = {}  # Dictionary to store user-specific task managers
printer = None
llm = None
gmail = None
google_tasks = None
config = {}

def get_task_manager(user_id: str) -> TaskManager:
    """Get or create a task manager for a specific user"""
    if user_id not in task_managers:
        storage_file = f"tasks_{user_id}.json"
        task_managers[user_id] = TaskManager(storage_file)
    return task_managers[user_id]

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get the current logged-in user"""
    if 'user_id' in session:
        return user_manager.get_user_by_id(session['user_id'])
    return None

def load_config():
    global config, printer, llm, gmail, google_tasks
    
    config_file = "config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
    
    # Setup integrations
    try:
        # Setup printer
        printer_config = config.get("printer", {})
        if printer_config.get("type") == "usb":
            vendor_id = int(printer_config.get("vendor_id", "0x04b8"), 16)
            product_id = int(printer_config.get("product_id", "0x0202"), 16)
            printer = ReceiptPrinter("usb", vendor_id=vendor_id, product_id=product_id)
        elif printer_config.get("type") == "network":
            printer = ReceiptPrinter("network", 
                                    host=printer_config.get("host", "192.168.1.100"),
                                    port=printer_config.get("port", 9100))
    except Exception as e:
        logging.warning(f"Printer setup failed: {e}")
    
    # Setup LLM
    llm_config = config.get("llm", {})
    api_key = os.getenv("OPENAI_API_KEY") if llm_config.get("provider") == "openai" else os.getenv("GEMINI_API_KEY")
    
    if api_key:
        try:
            if llm_config.get("provider") == "openai":
                llm = OpenAILLM(api_key, llm_config.get("model", "gpt-3.5-turbo"))
            elif llm_config.get("provider") == "gemini":
                llm = GeminiLLM(api_key, llm_config.get("model", "gemini-pro"))
        except Exception as e:
            logging.warning(f"LLM setup failed: {e}")
    
    # Setup integrations
    if config.get("integrations", {}).get("gmail_enabled"):
        try:
            gmail = GmailIntegration()
        except Exception as e:
            logging.warning(f"Gmail integration setup failed: {e}")
    
    if config.get("integrations", {}).get("google_tasks_enabled"):
        try:
            google_tasks = GoogleTasksIntegration()
        except Exception as e:
            logging.warning(f"Google Tasks integration setup failed: {e}")

# Authentication routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            error = 'Username and password are required'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            flash(error, 'error')
            return render_template('login.html')
        
        user = user_manager.authenticate_user(username, password)
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            
            if request.is_json:
                return jsonify({
                    'success': True, 
                    'user': user.to_safe_dict(),
                    'redirect': url_for('index')
                })
            return redirect(url_for('index'))
        else:
            error = 'Invalid username or password'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 401
            flash(error, 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')
        
        if not username or not email or not password:
            error = 'Username, email, and password are required'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            flash(error, 'error')
            return render_template('register.html')
        
        user = user_manager.create_user(username, email, password, full_name)
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'user': user.to_safe_dict(),
                    'redirect': url_for('index')
                })
            return redirect(url_for('index'))
        else:
            error = 'Username or email already exists'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            flash(error, 'error')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/user')
@login_required
def get_current_user_info():
    user = get_current_user()
    if user:
        return jsonify({
            'success': True,
            'user': user.to_safe_dict()
        })
    return jsonify({'success': False, 'error': 'User not found'}), 404

@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    try:
        user_id = session['user_id']
        task_manager = get_task_manager(user_id)
        
        status_filter = request.args.get('status')
        priority_filter = request.args.get('priority')
        category_filter = request.args.get('category')
        project_filter = request.args.get('project')
        tag_filter = request.args.get('tag')
        
        if status_filter:
            tasks = task_manager.get_tasks_by_status(TaskStatus[status_filter.upper()])
        elif priority_filter:
            tasks = task_manager.get_tasks_by_priority(TaskPriority[priority_filter.upper()])
        elif category_filter:
            tasks = task_manager.get_tasks_by_category(TaskCategory[category_filter.upper()])
        elif project_filter:
            tasks = task_manager.get_tasks_by_project(project_filter)
        elif tag_filter:
            tasks = task_manager.get_tasks_by_tag(tag_filter)
        else:
            tasks = task_manager.get_all_tasks()
        
        tasks_data = []
        for task in tasks:
            task_dict = task.to_dict()
            # Format dates for frontend
            task_dict['created_at_formatted'] = task.created_at.strftime('%Y-%m-%d %H:%M')
            task_dict['updated_at_formatted'] = task.updated_at.strftime('%Y-%m-%d %H:%M')
            if task.due_date:
                task_dict['due_date_formatted'] = task.due_date.strftime('%Y-%m-%d %H:%M')
            tasks_data.append(task_dict)
        
        return jsonify({
            'success': True,
            'tasks': tasks_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task():
    try:
        user_id = session['user_id']
        task_manager = get_task_manager(user_id)
        data = request.get_json()
        
        # Parse due date if provided
        due_date = None
        if data.get('due_date'):
            due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
        
        task = task_manager.create_task(
            title=data['title'],
            description=data.get('description'),
            priority=TaskPriority[data.get('priority', 'MEDIUM').upper()],
            category=TaskCategory[data.get('category', 'PERSONAL').upper()],
            project=data.get('project'),
            project_id=data.get('project_id'),
            due_date=due_date,
            tags=data.get('tags', [])
        )
        
        # Emit real-time update
        socketio.emit('task_created', {
            'task': task.to_dict()
        })
        
        return jsonify({
            'success': True,
            'task': task.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/<task_id>', methods=['PUT'])
@login_required
def update_task_status(task_id):
    try:
        user_id = session['user_id']
        task_manager = get_task_manager(user_id)
        data = request.get_json()
        new_status = TaskStatus[data['status'].upper()]
        
        if task_manager.update_task_status(task_id, new_status):
            task = task_manager.get_task(task_id)
            
            # Emit real-time update
            socketio.emit('task_updated', {
                'task': task.to_dict()
            })
            
            return jsonify({
                'success': True,
                'task': task.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    try:
        user_id = session['user_id']
        task_manager = get_task_manager(user_id)
        if task_manager.delete_task(task_id):
            # Emit real-time update
            socketio.emit('task_deleted', {
                'task_id': task_id
            })
            
            return jsonify({
                'success': True
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/<task_id>/print', methods=['POST'])
@login_required
def print_task_route(task_id):
    try:
        user_id = session['user_id']
        task_manager = get_task_manager(user_id)
        
        if not printer or not printer.is_connected():
            return jsonify({
                'success': False,
                'error': 'Printer not connected'
            }), 400
        
        task = task_manager.get_task(task_id)
        if not task:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        if printer.print_task(task):
            return jsonify({
                'success': True,
                'message': 'Task printed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to print task'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/printer/status')
def printer_status():
    try:
        return jsonify({
            'success': True,
            'connected': printer is not None and printer.is_connected(),
            'type': config.get('printer', {}).get('type', 'Not configured')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/printer/test', methods=['POST'])
def test_printer():
    try:
        if not printer or not printer.is_connected():
            return jsonify({
                'success': False,
                'error': 'Printer not connected'
            }), 400
        
        if printer.test_print():
            return jsonify({
                'success': True,
                'message': 'Test print successful'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Test print failed'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ai/prioritize', methods=['POST'])
def ai_prioritize():
    try:
        if not llm:
            return jsonify({
                'success': False,
                'error': 'LLM not configured'
            }), 400
        
        tasks = task_manager.get_all_tasks()
        if not tasks:
            return jsonify({
                'success': False,
                'error': 'No tasks to prioritize'
            }), 400
        
        suggestions = llm.suggest_task_prioritization(tasks)
        
        return jsonify({
            'success': True,
            'suggestions': [
                {
                    'task': suggestion['task'].to_dict(),
                    'reasoning': suggestion['reasoning']
                }
                for suggestion in suggestions
            ]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ai/breakdown/<task_id>', methods=['POST'])
def ai_breakdown(task_id):
    try:
        if not llm:
            return jsonify({
                'success': False,
                'error': 'LLM not configured'
            }), 400
        
        task = task_manager.get_task(task_id)
        if not task:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        subtasks = llm.suggest_task_breakdown(task)
        
        return jsonify({
            'success': True,
            'task': task.to_dict(),
            'subtasks': subtasks
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ai/suggest', methods=['POST'])
def ai_suggest():
    try:
        if not llm:
            return jsonify({
                'success': False,
                'error': 'LLM not configured'
            }), 400
        
        data = request.get_json()
        context = data.get('context', '')
        
        if not context:
            return jsonify({
                'success': False,
                'error': 'Context is required'
            }), 400
        
        existing_tasks = task_manager.get_all_tasks()
        suggestions = llm.generate_task_suggestions(context, existing_tasks)
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/search')
@login_required
def search_tasks():
    try:
        user_id = session['user_id']
        task_manager = get_task_manager(user_id)
        
        query = request.args.get('q', '')
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query is required'
            }), 400
        
        tasks = task_manager.search_tasks(query)
        
        tasks_data = []
        for task in tasks:
            task_dict = task.to_dict()
            task_dict['created_at_formatted'] = task.created_at.strftime('%Y-%m-%d %H:%M')
            tasks_data.append(task_dict)
        
        return jsonify({
            'success': True,
            'tasks': tasks_data,
            'query': query
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/statistics')
@login_required
def get_statistics():
    try:
        user_id = session['user_id']
        task_manager = get_task_manager(user_id)
        stats = task_manager.get_statistics()
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/categories')
def get_categories():
    try:
        categories = [category.value for category in TaskCategory]
        return jsonify({
            'success': True,
            'categories': categories
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/gmail/import', methods=['POST'])
def gmail_import():
    try:
        if not gmail or not gmail.is_authenticated():
            return jsonify({
                'success': False,
                'error': 'Gmail not configured or authenticated'
            }), 400
        
        tasks = gmail.create_tasks_from_emails(task_manager)
        
        # Emit real-time updates for each imported task
        for task in tasks:
            socketio.emit('task_created', {
                'task': task.to_dict()
            })
        
        return jsonify({
            'success': True,
            'imported_count': len(tasks),
            'tasks': [task.to_dict() for task in tasks]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/gtasks/sync', methods=['POST'])
def gtasks_sync():
    try:
        if not google_tasks or not google_tasks.is_authenticated():
            return jsonify({
                'success': False,
                'error': 'Google Tasks not configured or authenticated'
            }), 400
        
        stats = google_tasks.sync_tasks_bidirectional(task_manager)
        
        # Emit real-time update to refresh task list
        socketio.emit('tasks_synced', {
            'stats': stats
        })
        
        return jsonify({
            'success': True,
            'sync_stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# WebSocket events
# Project management routes
@app.route('/api/projects', methods=['GET'])
@login_required
def get_projects():
    try:
        user_id = session['user_id']
        task_manager = get_task_manager(user_id)
        
        # Get projects organized by category
        project_options = task_manager.get_project_options()
        
        return jsonify({
            'success': True,
            'projects': project_options
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/hierarchical', methods=['GET'])
@login_required
def get_hierarchical_tasks():
    try:
        user_id = session['user_id']
        task_manager = get_task_manager(user_id)
        
        # Get tasks organized hierarchically
        hierarchical_tasks = task_manager.get_hierarchical_tasks()
        
        # Format for frontend - hierarchical_tasks now has structure {project_name: {project: {...}, tasks: [...]}}
        formatted_structure = {}
        for category, projects in hierarchical_tasks.items():
            formatted_structure[category] = {}
            for project_name, project_data in projects.items():
                # Extract project info and tasks from new structure
                project_info = project_data['project']
                tasks = project_data['tasks']
                
                formatted_structure[category][project_name] = {
                    'project': project_info,
                    'tasks': []
                }
                
                for task in tasks:
                    task_dict = task.to_dict()
                    task_dict['created_at_formatted'] = task.created_at.strftime('%Y-%m-%d %H:%M')
                    task_dict['updated_at_formatted'] = task.updated_at.strftime('%Y-%m-%d %H:%M')
                    if task.due_date:
                        task_dict['due_date_formatted'] = task.due_date.strftime('%Y-%m-%d %H:%M')
                    formatted_structure[category][project_name]['tasks'].append(task_dict)
        
        return jsonify({
            'success': True,
            'structure': formatted_structure
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/projects', methods=['POST'])
@login_required
def create_project():
    try:
        user_id = session['user_id']
        task_manager = get_task_manager(user_id)
        data = request.get_json()
        
        category = TaskCategory[data['category'].upper()]
        project = task_manager.project_manager.create_project(
            name=data['name'],
            category=category,
            description=data.get('description')
        )
        
        # Emit real-time update
        socketio.emit('project_created', {
            'project': {
                'id': project.id,
                'name': project.name,
                'category': project.category.value,
                'description': project.description
            }
        })

        return jsonify({
            'success': True,
            'project': {
                'id': project.id,
                'name': project.name,
                'category': project.category.value,
                'description': project.description
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/projects/<project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    try:
        user_id = session['user_id']
        task_manager = get_task_manager(user_id)
        
        # Get the project before deleting to send in event
        project = task_manager.project_manager.get_project(project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404
        
        # Handle tasks assigned to this project - reassign to General or unassign
        tasks_with_project = task_manager.get_tasks_by_project_id(project_id)
        for task in tasks_with_project:
            task.project_id = None
            task.project = None
        
        if tasks_with_project:
            task_manager.save_tasks()
        
        # Delete the project
        success = task_manager.project_manager.delete_project(project_id)
        
        if success:
            # Emit real-time update
            socketio.emit('project_deleted', {
                'project_id': project_id,
                'project_name': project.name,
                'tasks_affected': len(tasks_with_project)
            })
            
            return jsonify({
                'success': True,
                'message': f'Project "{project.name}" deleted successfully',
                'tasks_affected': len(tasks_with_project)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete project'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'message': 'Connected to Task Manager'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    load_config()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
# Task Manager

A comprehensive task management application in Python with receipt printer integration, LLM assistance, and external application integrations.

## Features

### Core Task Management
- ✅ Create and delete task cards
- ✅ Task status tracking (pending, in-progress, completed, cancelled)
- ✅ Priority levels (low, medium, high, urgent)
- ✅ Due date management
- ✅ Tagging system
- ✅ Search and filtering
- ✅ JSON-based persistent storage

### Receipt Printer Integration
- ✅ Print individual task cards to receipt printers
- ✅ Print task lists and summaries
- ✅ Support for USB, Network, and Serial printers
- ✅ Built with python-escpos library
- ✅ Configurable printer settings

### LLM Integration
- ✅ OpenAI GPT integration for task assistance
- ✅ Google Gemini integration as alternative
- ✅ Task prioritization suggestions
- ✅ Task breakdown into subtasks
- ✅ Find similar tasks
- ✅ Generate new task suggestions based on context
- ✅ Task analysis and workflow optimization

### Application Integrations
- ✅ **Gmail Integration**
  - Import emails as tasks
  - Send task summaries via email
  - Priority detection from email content
  - Mark emails as read when processed
- ✅ **Google Tasks Integration**
  - Bidirectional sync with Google Tasks
  - Import/export tasks
  - Multiple task lists support
  - Maintains metadata for sync

### User Interface
- ✅ **Web-based UI** with responsive design
  - Modern Bootstrap-based interface
  - Real-time updates with WebSockets
  - Task cards with drag-and-drop functionality
  - Interactive dashboards and statistics
- ✅ **Command-line interface (CLI)** with colored output
  - Interactive mode for continuous use
  - Comprehensive help system
  - Configuration management

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd task_manager
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install the package:
```bash
pip install -e .
```

## Configuration

### Basic Configuration
Edit `config.json` to configure your settings:

```json
{
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
    "gmail_enabled": false,
    "google_tasks_enabled": false
  }
}
```

### Environment Variables
Set up your API keys:
```bash
export OPENAI_API_KEY="your-openai-api-key"
export GEMINI_API_KEY="your-gemini-api-key"
```

### Google Integrations Setup

#### Gmail Integration
1. Go to Google Cloud Console
2. Create a new project or select existing one
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Download credentials file as `gmail_credentials.json`
6. Set `gmail_enabled: true` in config.json

#### Google Tasks Integration
1. Enable Google Tasks API in Google Cloud Console
2. Create OAuth 2.0 credentials (can use same as Gmail)
3. Download credentials file as `gtasks_credentials.json`
4. Set `google_tasks_enabled: true` in config.json

### Printer Setup

#### USB Printer
1. Connect your receipt printer via USB
2. Find vendor ID and product ID using `lsusb` (Linux) or Device Manager (Windows)
3. Update config.json with correct IDs

#### Network Printer
```json
{
  "printer": {
    "type": "network",
    "host": "192.168.1.100",
    "port": 9100
  }
}
```

#### Serial Printer
```json
{
  "printer": {
    "type": "serial",
    "device": "/dev/ttyUSB0",
    "baudrate": 9600
  }
}
```

## Usage

### Web User Interface

Start the web interface:
```bash
python run_web_ui.py
```

Then open your browser to `http://localhost:5001`

**Features:**
- 📊 **Dashboard** - Overview with statistics and task summaries
- 📋 **Task Management** - Create, edit, delete, and organize tasks
- 🤖 **AI Assistant** - Get intelligent suggestions for task prioritization and breakdown
- 🖨️ **Printer Integration** - Print tasks directly from the web interface
- 🔗 **Integrations** - Connect with Gmail and Google Tasks
- 🔍 **Search & Filter** - Find tasks quickly with advanced filtering
- ⚡ **Real-time Updates** - See changes instantly across all connected devices

### Command Line Interface

#### Basic Task Management
```bash
# Create a task
task-manager create "Complete project documentation" --description "Write comprehensive docs" --priority high

# List all tasks
task-manager list

# List tasks by status
task-manager list --status pending

# Update task status
task-manager update <task-id> completed

# Delete a task
task-manager delete <task-id>

# Search tasks
task-manager search "documentation"

# Show task details
task-manager show <task-id>

# Show statistics
task-manager stats
```

#### Printer Commands
```bash
# Print a specific task
task-manager print <task-id>

# Print task list
task-manager print-list --status pending

# Test printer connection
task-manager test-printer
```

#### AI Assistance
```bash
# Get task prioritization suggestions
task-manager ai prioritize

# Break down a complex task
task-manager ai breakdown <task-id>

# Find similar tasks
task-manager ai similar <task-id>

# Generate task suggestions
task-manager ai suggest "Website redesign project"
```

#### Gmail Integration
```bash
# Import tasks from unread emails
task-manager gmail import

# Send task summary via email
task-manager gmail send-summary user@example.com
```

#### Google Tasks Integration
```bash
# Import tasks from Google Tasks
task-manager gtasks import

# Export local tasks to Google Tasks
task-manager gtasks export

# Bidirectional sync
task-manager gtasks sync

# List Google Task lists
task-manager gtasks lists
```

### Interactive Mode
```bash
# Start interactive mode
task-manager

# Then use commands without the "task-manager" prefix
> create "New task" --priority high
> list --status pending
> help
> exit
```

## Project Structure

```
task_manager/
├── src/
│   └── task_manager/
│       ├── core/                 # Core task management
│       │   ├── task.py          # Task model
│       │   └── task_manager.py  # Task manager class
│       ├── printer/             # Receipt printer integration
│       │   └── receipt_printer.py
│       ├── llm/                 # LLM integrations
│       │   ├── base_llm.py      # Base LLM interface
│       │   ├── openai_llm.py    # OpenAI integration
│       │   └── gemini_llm.py    # Google Gemini integration
│       ├── integrations/        # External app integrations
│       │   ├── gmail_integration.py
│       │   └── google_tasks_integration.py
│       └── cli/                 # Command line interface
│           └── main_cli.py
├── config.json                 # Configuration file
├── requirements.txt            # Python dependencies
├── setup.py                   # Package setup
└── README.md                  # This file
```

## API Reference

### Core Classes

#### Task
- `Task(title, description, priority, due_date, tags)`
- `update_status(status)`
- `add_tag(tag)` / `remove_tag(tag)`
- `format_for_print()` - Returns formatted string for printing

#### TaskManager
- `create_task(...)` - Create new task
- `delete_task(task_id)` - Delete task
- `get_task(task_id)` - Get single task
- `get_all_tasks()` - Get all tasks
- `search_tasks(query)` - Search tasks
- `get_statistics()` - Get task statistics

#### ReceiptPrinter
- `print_task(task)` - Print single task
- `print_task_list(tasks, title)` - Print task list
- `test_print()` - Test printer connection

## Development

### Running Tests
```bash
pip install -e ".[dev]"
pytest
```

### Code Formatting
```bash
black src/
flake8 src/
```

### Type Checking
```bash
mypy src/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run code formatting and tests
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting

### Common Issues

#### Printer Not Found
- Check USB connection and permissions
- Verify vendor/product IDs in config
- For Linux: add user to `lp` group

#### Google API Authentication
- Ensure credentials files are in the correct location
- Check that APIs are enabled in Google Cloud Console
- Verify OAuth consent screen is configured

#### LLM Integration Issues
- Confirm API keys are set correctly
- Check API quotas and billing
- Verify model names in configuration

### Support

For issues and feature requests, please create an issue in the GitHub repository.
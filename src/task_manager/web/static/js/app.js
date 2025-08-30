// Task Manager Web Application JavaScript

class TaskManagerApp {
    constructor() {
        this.socket = null;
        this.tasks = [];
        this.currentTask = null;
        this.currentFilter = { status: '', priority: '', category: '', project: '', tag: '' };
        this.projects = [];
        this.currentUser = null;
        
        this.initializeSocketIO();
        this.bindEventListeners();
        this.loadCurrentUser();
    }

    initializeSocketIO() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.updateConnectionStatus(true);
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.updateConnectionStatus(false);
        });

        this.socket.on('task_created', (data) => {
            this.showToast('Task Created', `Task "${data.task.title}" was created`, 'success');
            this.loadTasks();
            this.loadStatistics();
        });

        this.socket.on('task_updated', (data) => {
            this.showToast('Task Updated', `Task "${data.task.title}" was updated`, 'info');
            this.loadTasks();
            this.loadStatistics();
        });

        this.socket.on('task_deleted', (data) => {
            this.showToast('Task Deleted', 'A task was deleted', 'warning');
            this.loadTasks();
            this.loadStatistics();
        });

        this.socket.on('tasks_synced', (data) => {
            const stats = data.stats;
            this.showToast('Sync Complete', 
                `Imported: ${stats.imported}, Exported: ${stats.exported}, Updated: ${stats.updated}`, 
                'success');
            this.loadTasks();
            this.loadStatistics();
        });
    }

    bindEventListeners() {
        // Create Task Modal
        document.getElementById('createTaskBtn').addEventListener('click', () => this.createTask());
        document.getElementById('createTaskForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.createTask();
        });

        // Search and Filter
        document.getElementById('searchInput').addEventListener('input', (e) => this.searchTasks(e.target.value));
        document.getElementById('statusFilter').addEventListener('change', (e) => this.filterTasks());
        document.getElementById('priorityFilter').addEventListener('change', (e) => this.filterTasks());
        document.getElementById('categoryFilter').addEventListener('change', (e) => this.filterTasks());
        document.getElementById('projectFilter').addEventListener('change', (e) => this.filterTasks());
        document.getElementById('refreshTasksBtn').addEventListener('click', () => this.loadTasks());

        // AI Assistant
        document.getElementById('aiPrioritizeBtn').addEventListener('click', () => this.aiPrioritizeTasks());
        document.getElementById('generateSuggestionsBtn').addEventListener('click', () => this.generateAISuggestions());

        // Printer
        document.getElementById('testPrintBtn').addEventListener('click', () => this.testPrinter());
        document.getElementById('printTaskListBtn').addEventListener('click', () => this.printTaskList());

        // Integrations
        document.getElementById('gmailImportBtn').addEventListener('click', () => this.importFromGmail());
        document.getElementById('gmailSendBtn').addEventListener('click', () => this.sendGmailSummary());
        document.getElementById('gtasksSyncBtn').addEventListener('click', () => this.syncGoogleTasks());
        document.getElementById('gtasksImportBtn').addEventListener('click', () => this.importFromGoogleTasks());

        // Task Details Modal
        document.getElementById('deleteTaskBtn').addEventListener('click', () => this.deleteCurrentTask());
        document.getElementById('printTaskBtn').addEventListener('click', () => this.printCurrentTask());
    }

    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connectionStatus');
        if (connected) {
            statusElement.innerHTML = '<i class="bi bi-circle-fill text-success"></i> Connected';
        } else {
            statusElement.innerHTML = '<i class="bi bi-circle-fill text-danger"></i> Disconnected';
        }
    }

    async loadTasks() {
        try {
            this.showLoading('tasksLoading');
            
            let url = '/api/tasks';
            const params = new URLSearchParams();
            
            if (this.currentFilter.status) params.append('status', this.currentFilter.status);
            if (this.currentFilter.priority) params.append('priority', this.currentFilter.priority);
            if (this.currentFilter.category) params.append('category', this.currentFilter.category);
            if (this.currentFilter.project) params.append('project', this.currentFilter.project);
            if (this.currentFilter.tag) params.append('tag', this.currentFilter.tag);
            
            if (params.toString()) url += '?' + params.toString();
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.success) {
                this.tasks = data.tasks;
                this.renderTasks();
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error loading tasks:', error);
            this.showToast('Error', 'Failed to load tasks', 'danger');
        } finally {
            this.hideLoading('tasksLoading');
        }
    }

    renderTasks() {
        const container = document.getElementById('tasksContainer');
        const noTasksMessage = document.getElementById('noTasksMessage');
        
        if (this.tasks.length === 0) {
            container.innerHTML = '';
            noTasksMessage.classList.remove('d-none');
            return;
        }
        
        noTasksMessage.classList.add('d-none');
        
        const tasksHTML = this.tasks.map(task => this.renderTaskCard(task)).join('');
        container.innerHTML = tasksHTML;
        
        // Bind task-specific event listeners
        this.tasks.forEach(task => {
            document.getElementById(`task-${task.id}`).addEventListener('click', () => this.showTaskDetails(task));
            
            // Prevent status dropdown from triggering task details
            const statusSelect = document.getElementById(`status-${task.id}`);
            statusSelect.addEventListener('click', (e) => e.stopPropagation());
            statusSelect.addEventListener('change', (e) => 
                this.updateTaskStatus(task.id, e.target.value));
            
            // Prevent print button from triggering task details
            document.getElementById(`print-${task.id}`).addEventListener('click', (e) => {
                e.stopPropagation();
                this.printTask(task.id);
            });
        });
    }

    renderTaskCard(task) {
        const priorityClass = `priority-${task.priority}`;
        const statusClass = `status-${task.status}`;
        const categoryClass = `category-${task.category}`;
        
        const dueDateHTML = task.due_date ? 
            `<small class="text-muted due-date">
                <i class="bi bi-calendar"></i> ${task.due_date_formatted}
            </small>` : '';
        
        const projectHTML = task.project ?
            `<small class="text-muted project-info">
                <i class="bi bi-folder"></i> ${task.project}
            </small>` : '';
        
        const tagsHTML = task.tags && task.tags.length > 0 ?
            `<div class="task-tags">
                ${task.tags.map(tag => `<span class="task-tag">${tag}</span>`).join('')}
            </div>` : '';
        
        return `
            <div class="col-md-6 col-lg-4">
                <div class="card task-card" id="task-${task.id}" style="cursor: pointer;">
                    <div class="card-header d-flex justify-content-between align-items-start">
                        <div class="d-flex flex-wrap gap-1">
                            <span class="badge ${priorityClass}">${task.priority.toUpperCase()}</span>
                            <span class="badge ${categoryClass}">${task.category.toUpperCase()}</span>
                        </div>
                        <div class="dropdown">
                            <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="dropdown">
                                <i class="bi bi-three-dots-vertical"></i>
                            </button>
                            <ul class="dropdown-menu">
                                <li><a class="dropdown-item" href="#" id="print-${task.id}">
                                    <i class="bi bi-printer"></i> Print
                                </a></li>
                            </ul>
                        </div>
                    </div>
                    <div class="card-body">
                        <h6 class="card-title">${task.title}</h6>
                        ${task.description ? `<p class="card-text text-muted small">${task.description.substring(0, 100)}${task.description.length > 100 ? '...' : ''}</p>` : ''}
                        ${projectHTML}
                        ${dueDateHTML}
                        ${tagsHTML}
                        <div class="mt-3">
                            <select class="form-select form-select-sm ${statusClass}" id="status-${task.id}">
                                <option value="pending" ${task.status === 'pending' ? 'selected' : ''}>Pending</option>
                                <option value="in_progress" ${task.status === 'in_progress' ? 'selected' : ''}>In Progress</option>
                                <option value="completed" ${task.status === 'completed' ? 'selected' : ''}>Completed</option>
                                <option value="cancelled" ${task.status === 'cancelled' ? 'selected' : ''}>Cancelled</option>
                            </select>
                        </div>
                        <small class="text-muted">
                            <i class="bi bi-clock"></i> ${task.created_at_formatted}
                        </small>
                    </div>
                </div>
            </div>
        `;
    }

    async createTask() {
        const title = document.getElementById('taskTitle').value.trim();
        const description = document.getElementById('taskDescription').value.trim();
        const priority = document.getElementById('taskPriority').value;
        const category = document.getElementById('taskCategory').value;
        const project = document.getElementById('taskProject').value.trim();
        const dueDate = document.getElementById('taskDueDate').value;
        const tags = document.getElementById('taskTags').value.trim().split(',')
            .map(tag => tag.trim()).filter(tag => tag.length > 0);

        if (!title) {
            this.showToast('Error', 'Task title is required', 'danger');
            return;
        }

        try {
            const taskData = {
                title,
                description: description || null,
                priority,
                category,
                project: project || null,
                due_date: dueDate || null,
                tags
            };

            const response = await fetch('/api/tasks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(taskData)
            });

            const data = await response.json();

            if (data.success) {
                // Clear form
                document.getElementById('createTaskForm').reset();
                
                // Hide modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('createTaskModal'));
                modal.hide();
                
                this.showToast('Success', 'Task created successfully', 'success');
                
                // Reload tasks (will be handled by socket event)
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error creating task:', error);
            this.showToast('Error', 'Failed to create task', 'danger');
        }
    }

    async updateTaskStatus(taskId, newStatus) {
        try {
            const response = await fetch(`/api/tasks/${taskId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ status: newStatus })
            });

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error);
            }
            
            // Success will be handled by socket event
        } catch (error) {
            console.error('Error updating task:', error);
            this.showToast('Error', 'Failed to update task status', 'danger');
            // Reload tasks to revert changes
            this.loadTasks();
        }
    }

    showTaskDetails(task) {
        this.currentTask = task;
        
        const modalBody = document.getElementById('taskDetailsBody');
        
        const dueDateHTML = task.due_date ? 
            `<p><strong>Due Date:</strong> ${task.due_date_formatted}</p>` : '';
        
        const projectHTML = task.project ?
            `<p><strong>Project:</strong> ${task.project}</p>` : '';
        
        const tagsHTML = task.tags && task.tags.length > 0 ?
            `<p><strong>Tags:</strong> ${task.tags.join(', ')}</p>` : '';
        
        modalBody.innerHTML = `
            <h4>${task.title}</h4>
            ${task.description ? `<p><strong>Description:</strong></p><p class="text-muted">${task.description}</p>` : ''}
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Status:</strong> <span class="badge status-${task.status}">${task.status.replace('_', ' ').toUpperCase()}</span></p>
                    <p><strong>Priority:</strong> <span class="badge priority-${task.priority}">${task.priority.toUpperCase()}</span></p>
                    <p><strong>Category:</strong> <span class="badge category-${task.category}">${task.category.toUpperCase()}</span></p>
                </div>
                <div class="col-md-6">
                    <p><strong>Created:</strong> ${task.created_at_formatted}</p>
                    <p><strong>Updated:</strong> ${task.updated_at_formatted}</p>
                </div>
            </div>
            ${dueDateHTML}
            ${projectHTML}
            ${tagsHTML}
            <div class="mt-3">
                <small class="text-muted">Task ID: ${task.id}</small>
            </div>
        `;
        
        const modal = new bootstrap.Modal(document.getElementById('taskDetailsModal'));
        modal.show();
    }

    async deleteCurrentTask() {
        if (!this.currentTask || !confirm('Are you sure you want to delete this task?')) {
            return;
        }

        try {
            const response = await fetch(`/api/tasks/${this.currentTask.id}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (data.success) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('taskDetailsModal'));
                modal.hide();
                
                // Success will be handled by socket event
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error deleting task:', error);
            this.showToast('Error', 'Failed to delete task', 'danger');
        }
    }

    async printTask(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}/print`, {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                this.showToast('Success', 'Task sent to printer', 'success');
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error printing task:', error);
            this.showToast('Error', 'Failed to print task', 'danger');
        }
    }

    async printCurrentTask() {
        if (this.currentTask) {
            await this.printTask(this.currentTask.id);
        }
    }

    async loadStatistics() {
        try {
            const response = await fetch('/api/statistics');
            const data = await response.json();

            if (data.success) {
                this.renderStatistics(data.statistics);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error loading statistics:', error);
        }
    }

    renderStatistics(stats) {
        const container = document.getElementById('statisticsCards');
        
        const statusStats = stats.by_status;
        const priorityStats = stats.by_priority;
        
        container.innerHTML = `
            <div class="col-md-3">
                <div class="card stat-card bg-primary text-white">
                    <div class="card-body">
                        <div class="stat-number">${stats.total}</div>
                        <div class="stat-label">Total Tasks</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stat-card bg-warning text-dark">
                    <div class="card-body">
                        <div class="stat-number">${statusStats.pending || 0}</div>
                        <div class="stat-label">Pending</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stat-card bg-info text-white">
                    <div class="card-body">
                        <div class="stat-number">${statusStats.in_progress || 0}</div>
                        <div class="stat-label">In Progress</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stat-card bg-success text-white">
                    <div class="card-body">
                        <div class="stat-number">${statusStats.completed || 0}</div>
                        <div class="stat-label">Completed</div>
                    </div>
                </div>
            </div>
        `;
        
        if (stats.overdue > 0) {
            container.innerHTML += `
                <div class="col-md-3 mt-3">
                    <div class="card stat-card bg-danger text-white">
                        <div class="card-body">
                            <div class="stat-number">${stats.overdue}</div>
                            <div class="stat-label">Overdue</div>
                        </div>
                    </div>
                </div>
            `;
        }
    }

    async searchTasks(query) {
        if (!query.trim()) {
            this.loadTasks();
            return;
        }

        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            if (data.success) {
                this.tasks = data.tasks;
                this.renderTasks();
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error searching tasks:', error);
            this.showToast('Error', 'Search failed', 'danger');
        }
    }

    filterTasks() {
        this.currentFilter.status = document.getElementById('statusFilter').value;
        this.currentFilter.priority = document.getElementById('priorityFilter').value;
        this.currentFilter.category = document.getElementById('categoryFilter').value;
        this.currentFilter.project = document.getElementById('projectFilter').value;
        this.loadTasks();
    }

    async checkPrinterStatus() {
        try {
            const response = await fetch('/api/printer/status');
            const data = await response.json();

            const statusCard = document.getElementById('printerStatusCard');
            
            if (data.success) {
                const status = data.connected ? 'Connected' : 'Disconnected';
                const statusClass = data.connected ? 'text-success' : 'text-danger';
                const icon = data.connected ? 'bi-printer-fill' : 'bi-printer';
                
                statusCard.innerHTML = `
                    <div class="text-center">
                        <i class="bi ${icon} display-4 ${statusClass}"></i>
                        <h5 class="mt-3">${status}</h5>
                        <p class="text-muted">Type: ${data.type}</p>
                    </div>
                `;
            } else {
                statusCard.innerHTML = `
                    <div class="text-center">
                        <i class="bi bi-exclamation-triangle display-4 text-warning"></i>
                        <h5 class="mt-3">Error</h5>
                        <p class="text-muted">${data.error}</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error checking printer status:', error);
            const statusCard = document.getElementById('printerStatusCard');
            statusCard.innerHTML = `
                <div class="text-center">
                    <i class="bi bi-exclamation-triangle display-4 text-warning"></i>
                    <h5 class="mt-3">Connection Error</h5>
                    <p class="text-muted">Could not check printer status</p>
                </div>
            `;
        }
    }

    async testPrinter() {
        try {
            const button = document.getElementById('testPrintBtn');
            const originalText = button.innerHTML;
            button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Testing...';
            button.disabled = true;

            const response = await fetch('/api/printer/test', {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                this.showToast('Success', data.message, 'success');
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error testing printer:', error);
            this.showToast('Error', 'Printer test failed', 'danger');
        } finally {
            const button = document.getElementById('testPrintBtn');
            button.innerHTML = 'Test Print';
            button.disabled = false;
        }
    }

    async printTaskList() {
        this.showToast('Info', 'Task list printing functionality coming soon!', 'info');
    }

    async aiPrioritizeTasks() {
        try {
            const button = document.getElementById('aiPrioritizeBtn');
            const originalText = button.innerHTML;
            button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Analyzing...';
            button.disabled = true;

            const response = await fetch('/api/ai/prioritize', {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                this.displayAIResults('Task Prioritization', data.suggestions);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error getting AI prioritization:', error);
            this.showToast('Error', 'AI prioritization failed', 'danger');
        } finally {
            const button = document.getElementById('aiPrioritizeBtn');
            button.innerHTML = 'Analyze Priorities';
            button.disabled = false;
        }
    }

    async generateAISuggestions() {
        const context = document.getElementById('aiContext').value.trim();
        
        if (!context) {
            this.showToast('Error', 'Please provide context for suggestions', 'danger');
            return;
        }

        try {
            const button = document.getElementById('generateSuggestionsBtn');
            const originalText = button.innerHTML;
            button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Generating...';
            button.disabled = true;

            const response = await fetch('/api/ai/suggest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ context })
            });

            const data = await response.json();

            if (data.success) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('aiSuggestModal'));
                modal.hide();
                
                this.displayAISuggestions('Task Suggestions', data.suggestions);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error generating AI suggestions:', error);
            this.showToast('Error', 'Failed to generate suggestions', 'danger');
        } finally {
            const button = document.getElementById('generateSuggestionsBtn');
            button.innerHTML = '<i class="bi bi-lightbulb"></i> Generate Suggestions';
            button.disabled = false;
        }
    }

    displayAIResults(title, results) {
        const container = document.getElementById('aiResultsContainer');
        const resultsDiv = document.getElementById('aiResults');
        
        let html = `<h6>${title}</h6>`;
        
        if (results.length === 0) {
            html += '<p class="text-muted">No results available.</p>';
        } else {
            results.forEach((result, index) => {
                html += `
                    <div class="ai-result-item">
                        <h6>${index + 1}. ${result.task.title}</h6>
                        <p>${result.reasoning}</p>
                    </div>
                `;
            });
        }
        
        resultsDiv.innerHTML = html;
        container.classList.remove('d-none');
    }

    displayAISuggestions(title, suggestions) {
        const container = document.getElementById('aiResultsContainer');
        const resultsDiv = document.getElementById('aiResults');
        
        let html = `<h6>${title}</h6>`;
        
        if (suggestions.length === 0) {
            html += '<p class="text-muted">No suggestions available.</p>';
        } else {
            suggestions.forEach((suggestion, index) => {
                html += `
                    <div class="ai-result-item">
                        <h6>${index + 1}. ${suggestion}</h6>
                        <button class="btn btn-sm btn-outline-primary mt-2" onclick="app.createTaskFromSuggestion('${suggestion.replace(/'/g, "\\'")}')">
                            <i class="bi bi-plus"></i> Create Task
                        </button>
                    </div>
                `;
            });
        }
        
        resultsDiv.innerHTML = html;
        container.classList.remove('d-none');
    }

    createTaskFromSuggestion(suggestion) {
        document.getElementById('taskTitle').value = suggestion;
        const modal = new bootstrap.Modal(document.getElementById('createTaskModal'));
        modal.show();
    }

    async importFromGmail() {
        try {
            const button = document.getElementById('gmailImportBtn');
            button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Importing...';
            button.disabled = true;

            const response = await fetch('/api/integrations/gmail/import', {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                this.showToast('Success', `Imported ${data.imported_count} tasks from Gmail`, 'success');
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error importing from Gmail:', error);
            this.showToast('Error', 'Gmail import failed', 'danger');
        } finally {
            const button = document.getElementById('gmailImportBtn');
            button.innerHTML = '<i class="bi bi-download"></i> Import from Gmail';
            button.disabled = false;
        }
    }

    sendGmailSummary() {
        const email = prompt('Enter recipient email address:');
        if (email && email.includes('@')) {
            this.showToast('Info', 'Gmail summary functionality coming soon!', 'info');
        } else if (email) {
            this.showToast('Error', 'Please enter a valid email address', 'danger');
        }
    }

    async syncGoogleTasks() {
        try {
            const button = document.getElementById('gtasksSyncBtn');
            button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Syncing...';
            button.disabled = true;

            const response = await fetch('/api/integrations/gtasks/sync', {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                const stats = data.sync_stats;
                this.showToast('Success', 
                    `Sync complete: ${stats.imported} imported, ${stats.exported} exported, ${stats.updated} updated`, 
                    'success');
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error syncing Google Tasks:', error);
            this.showToast('Error', 'Google Tasks sync failed', 'danger');
        } finally {
            const button = document.getElementById('gtasksSyncBtn');
            button.innerHTML = '<i class="bi bi-arrow-repeat"></i> Sync Tasks';
            button.disabled = false;
        }
    }

    importFromGoogleTasks() {
        this.showToast('Info', 'Google Tasks import functionality coming soon!', 'info');
    }

    showLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.remove('d-none');
        }
    }

    hideLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.add('d-none');
        }
    }

    async loadProjects() {
        try {
            const response = await fetch('/api/projects');
            const data = await response.json();
            
            if (data.success) {
                this.projects = data.projects;
                this.updateProjectFilter();
            }
        } catch (error) {
            console.error('Error loading projects:', error);
        }
    }
    
    updateProjectFilter() {
        const projectFilter = document.getElementById('projectFilter');
        
        // Clear existing options except the first one
        while (projectFilter.children.length > 1) {
            projectFilter.removeChild(projectFilter.lastChild);
        }
        
        // Add project options
        this.projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project;
            option.textContent = project;
            projectFilter.appendChild(option);
        });
    }

    async loadCurrentUser() {
        try {
            const response = await fetch('/api/user');
            const data = await response.json();
            
            if (data.success) {
                this.currentUser = data.user;
                this.updateUserDisplay();
            } else {
                // User not authenticated, redirect to login
                if (data.error === 'Authentication required') {
                    window.location.href = '/login';
                }
            }
        } catch (error) {
            console.error('Error loading user:', error);
            // Redirect to login on error
            window.location.href = '/login';
        }
    }
    
    updateUserDisplay() {
        if (this.currentUser) {
            const currentUserSpan = document.getElementById('currentUser');
            const userInfo = document.getElementById('userInfo');
            
            if (currentUserSpan) {
                currentUserSpan.textContent = this.currentUser.username;
            }
            
            if (userInfo) {
                userInfo.textContent = this.currentUser.full_name || this.currentUser.username;
            }
        }
    }

    showToast(title, message, type = 'info') {
        const toastId = `toast-${Date.now()}`;
        const bgClass = `bg-${type}`;
        const textClass = type === 'warning' ? 'text-dark' : 'text-white';
        
        const toastHTML = `
            <div id="${toastId}" class="toast ${bgClass} ${textClass}" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header ${bgClass} ${textClass} border-0">
                    <strong class="me-auto">${title}</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        document.getElementById('toastContainer').insertAdjacentHTML('beforeend', toastHTML);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: 5000
        });
        
        toast.show();
        
        // Remove toast element after it's hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
}

// Global functions for HTML event handlers
function setupTabNavigation() {
    const tabLinks = ['tasksTab', 'aiTab', 'printerTab', 'integrationsTab'];
    const tabContents = ['tasksContent', 'aiContent', 'printerContent', 'integrationsContent'];
    
    tabLinks.forEach((linkId, index) => {
        document.getElementById(linkId).addEventListener('click', (e) => {
            e.preventDefault();
            
            // Update active tab
            tabLinks.forEach(id => document.getElementById(id).classList.remove('active'));
            e.target.classList.add('active');
            
            // Show corresponding content
            tabContents.forEach(id => {
                const element = document.getElementById(id);
                if (element) {
                    element.classList.remove('show', 'active');
                }
            });
            
            const targetContent = document.getElementById(tabContents[index]);
            if (targetContent) {
                targetContent.classList.add('show', 'active');
            }
        });
    });
    
    // Set initial active tab
    document.getElementById('tasksTab').classList.add('active');
}

function loadStatistics() {
    if (window.app) {
        window.app.loadStatistics();
    }
}

function loadTasks() {
    if (window.app) {
        window.app.loadTasks();
    }
}

function loadProjects() {
    if (window.app) {
        window.app.loadProjects();
    }
}

function checkPrinterStatus() {
    if (window.app) {
        window.app.checkPrinterStatus();
    }
}

function initializeEventListeners() {
    // This function is called from the HTML template
    // Any additional initialization can go here
}

// Initialize the application when the page loads
document.addEventListener('DOMContentLoaded', function() {
    window.app = new TaskManagerApp();
});
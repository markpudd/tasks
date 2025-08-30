from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..core.task import Task

class BaseLLM(ABC):
    def __init__(self, api_key: str, model: str = None):
        self.api_key = api_key
        self.model = model
    
    @abstractmethod
    def generate_response(self, prompt: str) -> str:
        pass
    
    def suggest_task_prioritization(self, tasks: List[Task]) -> List[Dict[str, Any]]:
        if not tasks:
            return []
        
        task_info = []
        for task in tasks:
            task_info.append({
                "id": task.id,
                "title": task.title,
                "description": task.description or "",
                "status": task.status.value,
                "priority": task.priority.value,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "tags": task.tags
            })
        
        prompt = f"""
        As a productivity assistant, analyze these tasks and suggest the optimal order to work on them.
        Consider factors like priority, due dates, dependencies, and effort required.
        
        Tasks:
        {task_info}
        
        Please provide:
        1. Recommended order (list task IDs in order)
        2. Brief reasoning for each task's position
        3. Any suggestions for breaking down complex tasks
        
        Format your response as a structured analysis.
        """
        
        response = self.generate_response(prompt)
        return self._parse_prioritization_response(response, tasks)
    
    def suggest_task_breakdown(self, task: Task) -> List[str]:
        prompt = f"""
        Break down this task into smaller, actionable subtasks:
        
        Title: {task.title}
        Description: {task.description or "No description provided"}
        Priority: {task.priority.value}
        Tags: {', '.join(task.tags) if task.tags else "None"}
        
        Please provide 3-7 specific, actionable subtasks that would help complete this main task.
        Each subtask should be clear and measurable.
        """
        
        response = self.generate_response(prompt)
        return self._parse_subtasks(response)
    
    def suggest_similar_tasks(self, task: Task, all_tasks: List[Task]) -> List[Task]:
        if not all_tasks:
            return []
        
        task_descriptions = []
        for t in all_tasks:
            if t.id != task.id:
                task_descriptions.append({
                    "id": t.id,
                    "title": t.title,
                    "description": t.description or "",
                    "tags": t.tags
                })
        
        prompt = f"""
        Find tasks similar to this target task:
        
        Target Task:
        Title: {task.title}
        Description: {task.description or "No description"}
        Tags: {', '.join(task.tags) if task.tags else "None"}
        
        Available Tasks:
        {task_descriptions}
        
        Please identify the IDs of the 3 most similar tasks and briefly explain why they are similar.
        """
        
        response = self.generate_response(prompt)
        similar_task_ids = self._parse_similar_tasks(response)
        return [t for t in all_tasks if t.id in similar_task_ids]
    
    def generate_task_suggestions(self, context: str, existing_tasks: List[Task]) -> List[str]:
        existing_titles = [task.title for task in existing_tasks]
        
        prompt = f"""
        Based on this context: "{context}"
        
        And considering existing tasks: {existing_titles}
        
        Suggest 3-5 new tasks that would be helpful. Make them specific and actionable.
        Avoid duplicating existing tasks.
        """
        
        response = self.generate_response(prompt)
        return self._parse_task_suggestions(response)
    
    def _parse_prioritization_response(self, response: str, tasks: List[Task]) -> List[Dict[str, Any]]:
        task_dict = {task.id: task for task in tasks}
        suggestions = []
        
        lines = response.split('\n')
        for line in lines:
            for task_id in task_dict.keys():
                if task_id in line:
                    suggestions.append({
                        "task": task_dict[task_id],
                        "reasoning": line.strip()
                    })
                    break
        
        return suggestions
    
    def _parse_subtasks(self, response: str) -> List[str]:
        subtasks = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or 
                        line.startswith('1.') or line.startswith('2.') or
                        line[0].isdigit()):
                subtask = line.lstrip('-•0123456789. ').strip()
                if subtask:
                    subtasks.append(subtask)
        
        return subtasks[:7]  # Limit to 7 subtasks
    
    def _parse_similar_tasks(self, response: str) -> List[str]:
        task_ids = []
        lines = response.split('\n')
        
        for line in lines:
            # Look for UUID patterns
            import re
            uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
            matches = re.findall(uuid_pattern, line, re.IGNORECASE)
            task_ids.extend(matches)
        
        return list(set(task_ids))  # Remove duplicates
    
    def _parse_task_suggestions(self, response: str) -> List[str]:
        suggestions = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or 
                        line.startswith('1.') or line.startswith('2.') or
                        line[0].isdigit()):
                suggestion = line.lstrip('-•0123456789. ').strip()
                if suggestion and len(suggestion) > 10:  # Filter out too short suggestions
                    suggestions.append(suggestion)
        
        return suggestions[:5]  # Limit to 5 suggestions
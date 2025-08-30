import requests
import json
import logging
from typing import Optional
from .base_llm import BaseLLM

logger = logging.getLogger(__name__)

class GeminiLLM(BaseLLM):
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        super().__init__(api_key, model)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = model
    
    def generate_response(self, prompt: str) -> str:
        try:
            url = f"{self.base_url}/{self.model}:generateContent"
            
            headers = {
                "Content-Type": "application/json",
            }
            
            data = {
                "contents": [{
                    "parts": [{
                        "text": f"You are a helpful task management assistant. Provide clear, actionable advice for organizing and prioritizing tasks.\n\n{prompt}"
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 1000,
                }
            }
            
            params = {"key": self.api_key}
            
            response = requests.post(url, headers=headers, json=data, params=params)
            response.raise_for_status()
            
            result = response.json()
            
            if "candidates" in result and len(result["candidates"]) > 0:
                if "content" in result["candidates"][0]:
                    if "parts" in result["candidates"][0]["content"]:
                        return result["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            logger.warning("Unexpected response format from Gemini API")
            return "Sorry, I couldn't generate a response at this time. Please try again later."
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to Gemini API: {e}")
            return "Sorry, I couldn't connect to the AI service. Please check your connection and try again."
        except Exception as e:
            logger.error(f"Error generating Gemini response: {e}")
            return "Sorry, I couldn't generate a response at this time. Please try again later."
    
    def analyze_task_workflow(self, tasks: list) -> str:
        if not tasks:
            return "No tasks to analyze workflow."
        
        task_info = []
        for task in tasks:
            task_info.append({
                "title": task.title,
                "status": task.status.value,
                "priority": task.priority.value,
                "tags": task.tags
            })
        
        prompt = f"""
        Analyze the workflow and dependencies in this task list:
        
        Tasks: {json.dumps(task_info, indent=2)}
        
        Please provide:
        1. Suggested workflow order
        2. Potential bottlenecks
        3. Tasks that could be done in parallel
        4. Dependencies you identify
        5. Optimization suggestions
        """
        
        return self.generate_response(prompt)
    
    def suggest_automation_opportunities(self, tasks: list) -> str:
        if not tasks:
            return "No tasks to analyze for automation."
        
        task_titles = [task.title for task in tasks]
        
        prompt = f"""
        Identify automation opportunities in these tasks:
        
        Tasks:
        {chr(10).join(f"- {title}" for title in task_titles)}
        
        Suggest:
        1. Which tasks could be automated
        2. What tools or methods could be used
        3. Time savings potential
        4. Implementation complexity
        """
        
        return self.generate_response(prompt)
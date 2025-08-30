import openai
from typing import Optional
import logging
from .base_llm import BaseLLM

logger = logging.getLogger(__name__)

class OpenAILLM(BaseLLM):
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        super().__init__(api_key, model)
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
    
    def generate_response(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful task management assistant. Provide clear, actionable advice for organizing and prioritizing tasks."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            return "Sorry, I couldn't generate a response at this time. Please try again later."
    
    def analyze_task_sentiment(self, task_title: str, task_description: str = "") -> dict:
        prompt = f"""
        Analyze the sentiment and complexity of this task:
        
        Title: {task_title}
        Description: {task_description}
        
        Please provide:
        1. Sentiment (positive/neutral/negative)
        2. Complexity level (low/medium/high)
        3. Estimated time to complete (in hours)
        4. Suggested approach or tips
        
        Format as JSON-like structure.
        """
        
        try:
            response = self.generate_response(prompt)
            return {"analysis": response, "model": self.model}
        except Exception as e:
            logger.error(f"Error analyzing task sentiment: {e}")
            return {"analysis": "Unable to analyze", "model": self.model}
    
    def generate_task_summary(self, tasks: list) -> str:
        if not tasks:
            return "No tasks to summarize."
        
        task_info = []
        for task in tasks:
            task_info.append(f"- {task.title} ({task.status.value}, {task.priority.value} priority)")
        
        prompt = f"""
        Provide a brief summary and insights about this task list:
        
        Tasks:
        {chr(10).join(task_info)}
        
        Include:
        1. Overall progress assessment
        2. Priority distribution
        3. Recommendations for focus areas
        4. Any patterns you notice
        """
        
        return self.generate_response(prompt)
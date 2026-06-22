import google.generativeai as genai
from app.core.config import get_settings

class LLMService:
    """Service to handle interactions with the Google Gemini LLM API."""
    
    def __init__(self):
        self.settings = get_settings()
        if not self.settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        
        # Initialize Google GenAI configuration
        genai.configure(api_key=self.settings.GEMINI_API_KEY)
        self.model_name = self.settings.GEMINI_MODEL
        self.model = genai.GenerativeModel(self.model_name)

    def generate_text(self, prompt: str, temperature: float = 0.2) -> str:
        """
        Generates text content using the configured Gemini model.
        
        Args:
            prompt (str): Input text prompt for the model.
            temperature (float): Controls response randomness (lower is more deterministic).
            
        Returns:
            str: Generated text response from the model.
        """
        config = genai.types.GenerationConfig(
            temperature=temperature,
        )
        response = self.model.generate_content(prompt, generation_config=config)
        return response.text

    def analyze_document(self, document_text: str, task_description: str, temperature: float = 0.1) -> str:
        """
        Analyzes a legal document based on a custom task description.
        
        Args:
            document_text (str): The raw text of the legal document.
            task_description (str): Action instructions (e.g. "flag risks", "extract indemnity").
            temperature (float): Controls creativity.
            
        Returns:
            str: Analysis output.
        """
        prompt = f"""
You are an expert AI Legal Assistant. Your task is to analyze the following legal document and perform the requested task.

TASK DESCRIPTION:
{task_description}

LEGAL DOCUMENT TEXT:
---
{document_text}
---

Please provide a detailed, precise, and professional analysis.
"""
        return self.generate_text(prompt, temperature=temperature)

    def extract_clauses_as_json(self, document_text: str) -> str:
        """
        Specifically extracts critical legal clauses from a contract.
        
        Args:
            document_text (str): Raw contract text.
            
        Returns:
            str: Extracted clauses in a structured report.
        """
        task = """
Extract all key clauses from the contract.
Focus specifically on:
1. Termination conditions
2. Limitation of Liability
3. Indemnification
4. Governing Law / Jurisdiction
5. Confidentiality obligations

Summarize each clause, cite the context/sentence, and label the risk level as (Low / Medium / High).
"""
        return self.analyze_document(document_text, task, temperature=0.1)


# Singleton pattern initialization
_llm_service = None

def get_llm_service() -> LLMService:
    """Returns a cached singleton instance of the LLMService."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

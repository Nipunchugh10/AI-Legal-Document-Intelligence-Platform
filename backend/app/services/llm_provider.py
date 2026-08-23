import logging
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_configured = False

def _ensure_configured():
    global _configured
    if not _configured:
        settings = get_settings()
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _configured = True

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=10),
    reraise=True,
    retry=retry_if_exception_type(Exception),
)
def _call_gemini_with_retry(prompt: str, temperature: float = 0.0) -> str:
    """Helper function to call Gemini with tenacity retries."""
    _ensure_configured()
    settings = get_settings()
    model = genai.GenerativeModel(settings.GEMINI_MODEL)
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(temperature=temperature)
    )
    if response and response.text:
        return response.text.strip()
    return ""

def get_llm_response(prompt: str, temperature: float = 0.0, contract_id: int | None = None) -> str:
    """
    Calls the primary Google Gemini model with exponential backoff retry logic.

    Args:
        prompt (str): Text prompt to pass to the LLM.
        temperature (float): Sampling temperature (0.0 for deterministic legal analysis).
        contract_id (int | None): Optional contract ID to log and trace.

    Returns:
        str: Model response text.
    """
    provider_name = "Gemini"
    cid_str = str(contract_id) if contract_id is not None else "None"
    
    logger.info("Starting LLM request for contract_id=%s", cid_str)
    
    try:
        response = _call_gemini_with_retry(prompt, temperature)
        logger.info("LLM call served by provider=%s for contract_id=%s", provider_name, cid_str)
        return response
    except Exception as e:
        logger.error(f"Primary LLM API call (Gemini) failed: {str(e)}")
        raise e

def get_langchain_llm(temperature: float = 0.0):
    """
    Returns a LangChain ChatGoogleGenerativeAI instance for use in LangGraph nodes.

    Args:
        temperature (float): Sampling temperature.

    Returns:
        ChatGoogleGenerativeAI: Configured LangChain model instance.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=temperature,
        max_retries=3,
    )

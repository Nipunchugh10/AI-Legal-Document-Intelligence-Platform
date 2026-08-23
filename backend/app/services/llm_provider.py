import logging
import re
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_configured = False

FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
]

def _ensure_configured():
    global _configured
    if not _configured:
        settings = get_settings()
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _configured = True

def _clean_error_message(err_str: str) -> str:
    """Sanitizes raw API exception strings into clean, user-facing error messages."""
    if "429" in err_str or "quota" in err_str.lower() or "ResourceExhausted" in err_str:
        # Extract retry delay if present
        match = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", err_str)
        if match:
            seconds = match.group(1)
            return f"Google AI rate limit reached. Please retry in {seconds} seconds."
        return "AI rate limit reached. Please wait a moment and try again."
    
    if "503" in err_str or "overloaded" in err_str.lower():
        return "AI service is currently busy. Please try again in a few moments."

    return "An error occurred during AI processing. Please try again."

def _generate_with_model_cascade(prompt: str, temperature: float = 0.0) -> str:
    """
    Attempts generation with primary configured model, automatically falling over to
    backup models if a 429 quota limit or transient failure is encountered.
    """
    _ensure_configured()
    settings = get_settings()
    
    candidate_models = [settings.GEMINI_MODEL]
    for fb in FALLBACK_MODELS:
        if fb not in candidate_models:
            candidate_models.append(fb)

    last_exception = None
    for model_name in candidate_models:
        try:
            logger.info("Attempting generation with Gemini model: %s", model_name)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(temperature=temperature)
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            err_str = str(e)
            last_exception = e
            logger.warning("Model %s failed with error: %s. Attempting fallback...", model_name, err_str[:120])
            continue

    if last_exception:
        clean_msg = _clean_error_message(str(last_exception))
        raise RuntimeError(clean_msg)

    return ""

def get_llm_response(prompt: str, temperature: float = 0.0, contract_id: int | None = None) -> str:
    """
    Calls Google Gemini with automatic multi-model failover and clean error handling.
    """
    cid_str = str(contract_id) if contract_id is not None else "None"
    logger.info("Starting LLM request for contract_id=%s", cid_str)
    
    try:
        response = _generate_with_model_cascade(prompt, temperature)
        return response
    except Exception as e:
        logger.error("All Gemini LLM models failed for contract_id=%s: %s", cid_str, str(e))
        raise e

def get_langchain_llm(temperature: float = 0.0):
    """
    Returns a LangChain ChatGoogleGenerativeAI instance for use in LangGraph nodes.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    settings = get_settings()
    model_to_use = "gemini-2.5-flash" if "latest" in settings.GEMINI_MODEL else settings.GEMINI_MODEL
    return ChatGoogleGenerativeAI(
        model=model_to_use,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=temperature,
        max_retries=3,
    )

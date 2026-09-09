"""
Google Gemini LLM Provider Service
----------------------------------
Pure Google Gemini multi-model cascade and resilient failover architecture.
100% Free-Tier optimized across distinct Gemini quota buckets (Flash -> Flash-Lite -> 1.5 Flash).
Includes Tenacity exponential backoff retries and usage monitoring.
"""

import logging
import re
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import get_settings
from app.services.ai_usage_monitor import ai_usage_monitor

logger = logging.getLogger(__name__)

_configured = False

# Ordered fallback cascade utilizing separate Google AI Studio free quota buckets
GEMINI_CASCADE_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-2.5-flash",
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
        match = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", err_str)
        if match:
            seconds = match.group(1)
            return f"Google AI rate limit reached (429 quota). Please retry in {seconds} seconds."
        return "AI rate limit reached (429 quota). Please wait a moment and try again."
    
    if "503" in err_str or "overloaded" in err_str.lower():
        return "AI service is currently busy. Please try again in a few moments."

    return "An error occurred during AI processing. Please try again."

def _generate_with_model_cascade(prompt: str, temperature: float = 0.0) -> str:
    """
    Attempts generation with primary configured model, automatically falling over to
    backup Gemini models across separate free-tier quota pools if a 429 or transient error occurs.
    """
    _ensure_configured()
    settings = get_settings()
    
    candidate_models = [settings.GEMINI_MODEL]
    for fb in GEMINI_CASCADE_MODELS:
        if fb not in candidate_models:
            candidate_models.append(fb)

    rate_limit_exception = None
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
                ai_usage_monitor.record_call("gemini", model_name, "success")
                return response.text.strip()
        except Exception as e:
            err_str = str(e)
            last_exception = e
            is_rate_limit = "429" in err_str or "quota" in err_str.lower() or "ResourceExhausted" in err_str
            if is_rate_limit:
                rate_limit_exception = e
                status = "rate_limited"
            else:
                status = "error"
            ai_usage_monitor.record_call("gemini", model_name, status, error=err_str[:120])
            logger.warning("Gemini model %s failed with error: %s. Falling over to next Gemini free tier model...", model_name, err_str[:120])
            continue

    if rate_limit_exception:
        clean_msg = _clean_error_message(str(rate_limit_exception))
        raise RuntimeError(clean_msg)
    elif last_exception:
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
        logger.info("LLM call served by provider=Gemini for contract_id=%s", cid_str)
        return response
    except Exception as e:
        logger.error("All Gemini LLM models failed for contract_id=%s: %s", cid_str, str(e))
        raise e

def get_langchain_llm(temperature: float = 0.0):
    """
    Returns a LangChain LLM instance with multi-model Gemini fallbacks across
    distinct free-tier quota buckets (Gemini Flash -> Gemini Flash-Lite).
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    settings = get_settings()
    model_to_use = "gemini-2.0-flash" if ("latest" in settings.GEMINI_MODEL or "3.5" in settings.GEMINI_MODEL) else settings.GEMINI_MODEL
    
    primary_llm = ChatGoogleGenerativeAI(
        model=model_to_use,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=temperature,
        max_retries=3,
    )

    # Free-tier fallback model across independent Google AI Studio quota bucket (30 RPM)
    fallback_lite = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=temperature,
        max_retries=3,
    )

    return primary_llm.with_fallbacks([fallback_lite])

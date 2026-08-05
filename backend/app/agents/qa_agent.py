import json
import re
import logging
from typing import Dict, Any, List, TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from app.services.llm_provider import get_llm_response
from app.services.vector_store import get_vector_store_service

logger = logging.getLogger(__name__)

class QAState(TypedDict):
    """
    State schema for the conversational Q&A agent (Agent 5).
    """
    contract_id: int
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    error: Optional[str]

QA_SYSTEM_PROMPT = """You are an expert AI Legal Document Assistant.
Your task is to answer questions about the provided contract accurately, objectively, and in plain English.

Answer the user's question based strictly on the provided contract text snippets.
Always cite which part of the contract your answer is based on (e.g., citing Chunk index or using quotations).
If the answer cannot be found or reasonably inferred from the provided contract text, say so explicitly — never make up or assume an answer.

Return your response in structured JSON with two keys:
- "answer": The plain-English answer to the question with proper citations referencing the relevant chunk index/indices.
- "not_found": A boolean indicating whether the answer could not be found in the provided contract (true if not found, false if found).

Do NOT include markdown formatting, backticks (like ```json), or text before/after the JSON.
"""

def _clean_and_parse_json(text: str) -> Dict[str, Any]:
    """Cleans LLM response text and parses it as a JSON dictionary."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: search for JSON object with regex
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        
        logger.error(f"Failed to parse JSON from LLM response for Q&A: {text[:200]}")
        return {
            "answer": "Could not parse answer from assistant response.",
            "not_found": True
        }

def answer_question_node(state: QAState) -> Dict[str, Any]:
    """
    LangGraph node function: retrieves relevant contract chunks using RAG vector search,
    passes them with the user's question to the Gemini LLM, and populates the response state.
    """
    contract_id = state.get("contract_id", 0)
    question = state.get("question", "")

    if not question:
        return {
            "answer": "Please ask a specific question about this contract.",
            "sources": [],
            "error": "No question provided."
        }

    # 1. Retrieve relevant chunks (top 5) from vector store using RAG
    vector_store = get_vector_store_service()
    sources = []
    retrieved_texts = []
    
    try:
        results = vector_store.query_contract_chunks(contract_id, question, n_results=5)
        for res in results:
            chunk_idx = res.get("chunk_index")
            text = res.get("text")
            similarity = res.get("similarity", 0.0)
            if text:
                sources.append({
                    "chunk_index": chunk_idx,
                    "text": text,
                    "similarity": similarity
                })
                retrieved_texts.append(f"--- Document Section (Chunk {chunk_idx}) ---\n{text}")
    except Exception as e:
        logger.error(f"Error querying vector store for contract {contract_id} chunks: {e}")
        return {
            "answer": "Failed to retrieve relevant context from the contract.",
            "sources": [],
            "error": str(e)
        }

    if not retrieved_texts:
        return {
            "answer": "This contract has not been processed or ingested yet. I cannot answer questions without ingestion.",
            "sources": [],
            "error": "No vector store chunks found for this contract."
        }

    context = "\n\n".join(retrieved_texts)

    # 2. Build the full prompt for LLM
    prompt = (
        f"{QA_SYSTEM_PROMPT}\n\n"
        f"USER QUESTION: {question}\n\n"
        f"--- CONTRACT TEXT SNIPPETS (RETRIEVED VIA RAG) ---\n"
        f"{context}\n\n"
        f"Please provide the answer in the required JSON format now."
    )

    # 3. Call LLM
    try:
        llm_response = get_llm_response(prompt, temperature=0.0, contract_id=contract_id)
        parsed_data = _clean_and_parse_json(llm_response)
        
        answer = parsed_data.get("answer", "")
        not_found = parsed_data.get("not_found", False)
        
        if not_found or not answer.strip():
            answer = "I am sorry, but the answer to your question could not be found or verified in the contract text snippets."
            
        return {
            "answer": answer,
            "sources": sources
        }
    except Exception as e:
        logger.error(f"Error generating answer for contract {contract_id}: {str(e)}")
        return {
            "answer": "An unexpected error occurred while processing the Q&A request.",
            "sources": [],
            "error": str(e)
        }

def build_qa_graph():
    """
    Constructs the LangGraph state graph for the Q&A Agent (Agent 5).
    """
    builder = StateGraph(QAState)
    builder.add_node("answer_question", answer_question_node)
    builder.add_edge(START, "answer_question")
    builder.add_edge("answer_question", END)
    
    return builder.compile()

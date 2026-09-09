"""
AI Legal Document Intelligence Platform
Hugging Face Spaces Entrypoint (Gradio SDK - 100% Free Tier)
------------------------------------------------------------
Provides dual interfaces on Port 7860:
1. Root Route (/): Full React 19 SPA Legal Intelligence Platform
2. Gradio Route (/gradio): Quick Legal Clause Analysis & AI Sandbox
3. Automated startup database migrations for Cloud PostgreSQL (Neon / Supabase)
"""

import os
import sys
from pathlib import Path

# Add backend directory to Python search path
_ROOT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _ROOT_DIR / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Ensure required persistent storage directories exist
for folder in ["uploads", "chroma_data", "backend/uploads", "backend/chroma_data"]:
    (_ROOT_DIR / folder).mkdir(parents=True, exist_ok=True)

def run_startup_migrations():
    """Run database verification & migrations if DATABASE_URL is configured."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        print("[*] Cloud database detected. Verifying and applying Alembic migrations...")
        try:
            from alembic.config import Config
            from alembic import command
            alembic_ini = _BACKEND_DIR / "alembic.ini"
            if alembic_ini.exists():
                cfg = Config(str(alembic_ini))
                cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
                from app.core.config import normalize_database_url
                cfg.set_main_option("sqlalchemy.url", normalize_database_url(database_url))
                command.upgrade(cfg, "head")
                print("[+] Database schema successfully migrated to latest version.")
            else:
                print("[!] Warning: alembic.ini not found at", alembic_ini)
        except Exception as e:
            print(f"[!] Migration notice: {e}")
    else:
        print("[*] Notice: DATABASE_URL not set. Running with default/local database configuration.")

# Import the core FastAPI application
from app.main import app as fastapi_app
import gradio as gr

# ZeroGPU Support for Hugging Face Spaces (100% Free A10G Acceleration)
try:
    import spaces
except ImportError:
    class _MockSpaces:
        def GPU(self, func=None, **kwargs):
            if func is None:
                return lambda f: f
            return func
    spaces = _MockSpaces()

# Build companion Gradio Quick-Analysis Workspace
@spaces.GPU
def analyze_clause_quick(clause_text: str, analysis_type: str) -> str:
    """Quick LLM-powered clause analyzer for the Gradio interface."""
    if not clause_text or not clause_text.strip():
        return "Please enter or paste a legal clause to analyze."
    
    try:
        from app.services.llm_provider import get_llm_response
        prompt = (
            f"You are an expert legal AI assistant. Perform a {analysis_type} on the following legal clause.\n\n"
            f"Clause:\n\"\"\"\n{clause_text.strip()}\n\"\"\"\n\n"
            f"Provide:\n"
            f"1. Plain-English Explanation\n"
            f"2. Risk Assessment (Low, Medium, or High)\n"
            f"3. Potential Concerns or Missing Protections\n"
            f"4. Recommended Modifications"
        )
        return get_llm_response(prompt, temperature=0.2)
    except Exception as e:
        return f"AI Service Error: {str(e)}\n\nPlease ensure GEMINI_API_KEY is configured in your Space Secrets."

with gr.Blocks(title="AI Legal Document Intelligence Platform") as demo:
    gr.Markdown("# ⚖️ AI Legal Document Intelligence Platform")
    gr.Markdown(
        "Welcome to the AI Legal Document Intelligence Platform on Hugging Face Spaces! "
        "Use this quick analysis interface below, or launch the [Full React Web Application](/) for complete "
        "document management, multi-agent analysis, PDF viewer, contract comparisons, and interactive Q&A."
    )
    
    with gr.Row():
        with gr.Column(scale=1):
            clause_input = gr.Textbox(
                label="Legal Clause or Agreement Text",
                placeholder="Paste contract clause, indemnity term, termination clause, or non-compete here...",
                lines=8,
            )
            analysis_choice = gr.Radio(
                choices=["Comprehensive Risk & Explanation", "Plain-English Summary", "Risk Identification", "Redline / Negotiation Revision"],
                value="Comprehensive Risk & Explanation",
                label="Analysis Mode",
            )
            submit_btn = gr.Button("⚡ Analyze Clause with Gemini", variant="primary")
        
        with gr.Column(scale=1):
            analysis_output = gr.Markdown(
                label="Analysis Results",
                value="*Results will appear here after clicking 'Analyze Clause'...*",
            )
    
    submit_btn.click(
        fn=analyze_clause_quick,
        inputs=[clause_input, analysis_choice],
        outputs=[analysis_output],
    )
    
    gr.Markdown("---")
    gr.Markdown(
        "### 🚀 Full Platform Features Available:\n"
        "- **React 19 Dashboard**: Visit [`/`](/) to access the full user interface.\n"
        "- **Interactive API Docs**: Visit [`/docs`](/docs) for the OpenAPI Swagger interface.\n"
        "- **Database Diagnostics**: Visit [`/health/db`](/health/db) to view cloud database health."
    )

# Mount Gradio onto the FastAPI application at /gradio
# This preserves all FastAPI routes and the React SPA at / while adding Gradio at /gradio
app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")

# Ensure Gradio mount precedes the React SPA catch-all route in the route table
gradio_mount = app.routes.pop()
app.routes.insert(0, gradio_mount)

if __name__ == "__main__":
    run_startup_migrations()
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    print(f"[*] Starting unified server on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")

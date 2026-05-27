"""
config.py
─────────────────────────────────────────────────────────────────────
Configurações globais da aplicação.
Lê variáveis sensíveis do ambiente (arquivo .env ou sistema).

Para carregar o .env automaticamente, instale python-dotenv:
    pip install python-dotenv

E adicione ao run.py (antes de create_app()):
    from dotenv import load_dotenv; load_dotenv()
─────────────────────────────────────────────────────────────────────
"""

import os

# ─────────────────────────────────────────────────────────────────────
# DIRETÓRIOS
# ─────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

MEDIA_DIR = os.path.join(BASE_DIR, "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────
# FFMPEG
# ─────────────────────────────────────────────────────────────────────

FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "ffmpeg")

# ─────────────────────────────────────────────────────────────────────
# GROQ  — lido do ambiente, nunca hardcoded
# ─────────────────────────────────────────────────────────────────────

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

GROQ_HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json",
}
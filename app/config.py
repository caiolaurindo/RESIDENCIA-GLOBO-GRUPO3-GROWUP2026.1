import os

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

MEDIA_DIR = os.path.join(
    BASE_DIR,
    "media"
)

os.makedirs(
    MEDIA_DIR,
    exist_ok=True
)

# ============================================
# FFMPEG
# ============================================

FFMPEG_PATH = "ffmpeg"

# Caso necessário:
# FFMPEG_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"

# ============================================
# GROQ
# ============================================

GROQ_API_KEY = "SUACHAVEDOGROQ"

GROQ_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

GROQ_HEADERS = {

    "Authorization":
        f"Bearer {GROQ_API_KEY}",

    "Content-Type":
        "application/json"
}
"""
run.py — ponto de entrada da aplicação.

Carrega o .env automaticamente (requer python-dotenv).
"""

from dotenv import load_dotenv

load_dotenv()   # lê o arquivo .env antes de qualquer import da app

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )
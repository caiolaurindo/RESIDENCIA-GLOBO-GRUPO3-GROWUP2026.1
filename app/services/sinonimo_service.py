"""
sinonimo_service.py
─────────────────────────────────────────────────────────────────────
Camada de fallback inteligente:
    1. Solicita 3 sinônimos à LLM (Groq / llama-3.3-70b-versatile).
    2. Testa cada sinônimo contra o banco VLibras.
    3. Retorna o primeiro que existir, ou None.

Variáveis de ambiente necessárias (ver .env.example):
    GROQ_API_KEY   → chave da API Groq (https://console.groq.com)
─────────────────────────────────────────────────────────────────────
"""

import json
import os

import requests

from app.services.vlibras_db import buscar_termo, normalizar

# ─────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────────────────────────────

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.3-70b-versatile"

def _get_headers() -> dict:
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY não definida. "
            "Adicione-a no arquivo .env ou nas variáveis de ambiente."
        )
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


# ─────────────────────────────────────────────────────────────────────
# FUNÇÕES INTERNAS
# ─────────────────────────────────────────────────────────────────────

def _pedir_sinonimos(palavra: str) -> list[str]:
    """
    Chama a LLM e retorna lista de até 3 sinônimos.
    Em caso de erro, retorna lista vazia (não quebra o fluxo).
    """
    prompt = (
        f"A palavra '{palavra}' não existe no dicionário do VLibras. "
        "Retorne uma lista em formato JSON com exatamente 3 sinônimos "
        "diretos para ela em português, em ordem de relevância. "
        "Responda SOMENTE com o array JSON, sem explicações. "
        'Exemplo: ["casa", "lar", "moradia"]'
    )

    payload = {
        "model": _GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Você é um especialista em língua portuguesa. "
                    "Responda sempre com JSON puro, sem markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 80,
    }

    try:
        response = requests.post(
            _GROQ_URL,
            headers=_get_headers(),
            json=payload,
            timeout=10,
        )
        response.raise_for_status()

        content = (
            response.json()["choices"][0]["message"]["content"]
            .strip()
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        sinonimos = json.loads(content)
        if isinstance(sinonimos, list):
            return [str(s).strip() for s in sinonimos[:3]]

    except Exception as exc:
        print(f"⚠️  Erro ao buscar sinônimos para '{palavra}': {exc}")

    return []


# ─────────────────────────────────────────────────────────────────────
# API PÚBLICA
# ─────────────────────────────────────────────────────────────────────

def resolver_via_sinonimo(palavra: str) -> dict:
    """
    Tenta resolver uma palavra ausente no banco VLibras via sinônimos.

    Retorna um dict com:
        {
            "palavra_original":  str,
            "sinonimos_testados": list[str],
            "termo_vlibras":     str | None,   # None → não resolvido
            "estrategia":        "sinonimo" | "datilologia" | "original"
        }
    """
    sinonimos = _pedir_sinonimos(palavra)
    testados = []

    for s in sinonimos:
        testados.append(s)
        termo = buscar_termo(s)
        if termo:
            print(f"🔄 '{palavra}' → sinônimo '{s}' → '{termo}'")
            return {
                "palavra_original": palavra,
                "sinonimos_testados": testados,
                "termo_vlibras": termo,
                "estrategia": "sinonimo",
            }

    # Nenhum sinônimo funcionou → datilologia (letra a letra)
    datilologia = _para_datilologia(palavra)
    print(f"🔤 '{palavra}' → datilologia: {datilologia}")

    return {
        "palavra_original": palavra,
        "sinonimos_testados": testados,
        "termo_vlibras": datilologia if datilologia else None,
        "estrategia": "datilologia" if datilologia else "original",
    }


def _para_datilologia(palavra: str) -> str | None:
    """
    Converte a palavra em uma sequência de letras separadas por espaço
    (o VLibras aceita letras isoladas como datilologia).
    Filtra apenas letras A-Z.
    """
    letras = [
        c for c in normalizar(palavra) if c.isalpha()
    ]
    if not letras:
        return None
    return " ".join(letras)
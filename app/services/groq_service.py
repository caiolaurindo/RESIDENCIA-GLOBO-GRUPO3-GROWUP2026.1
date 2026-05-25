import json
import requests

from app.config import (
    GROQ_URL,
    GROQ_HEADERS
)

def otimizar_srt_completo(entries):

    linhas = []

    for i, e in enumerate(entries):

        linhas.append(

            f"""
ID: {i}

TEMPO:
{e['start']} --> {e['end']}

FRASE:
{e['original']}
"""
        )

    texto_completo = "\n".join(linhas)

    prompt = f"""
Você é especialista em Libras.

Transforme frases em versões ideais
para o avatar do VLibras.

OBJETIVOS:

- evitar soletração;
- resumir;
- melhorar fluidez;
- preservar significado;
- linguagem visual;
- natural para Libras.

RETORNE APENAS JSON.

[
  {{
    "id": 0,
    "texto_otimizado": "Olá tudo bem"
  }}
]

FRASES:

{texto_completo}
"""

    payload = {

        "model":
            "llama-3.3-70b-versatile",

        "messages": [

            {
                "role": "system",
                "content":
                    "Você traduz frases para Libras."
            },

            {
                "role": "user",
                "content":
                    prompt
            }
        ],

        "temperature": 0.2
    }

    response = requests.post(

        GROQ_URL,

        headers=GROQ_HEADERS,

        json=payload
    )

    if response.status_code != 200:

        raise Exception(
            response.text
        )

    data = response.json()

    content = (

        data["choices"][0]
        ["message"]
        ["content"]
        .strip()
    )

    content = content.replace(
        "```json",
        ""
    )

    content = content.replace(
        "```",
        ""
    ).strip()

    return json.loads(content)
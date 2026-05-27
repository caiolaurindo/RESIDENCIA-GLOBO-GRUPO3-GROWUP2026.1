"""
validacao_service.py
─────────────────────────────────────────────────────────────────────
Orquestra o pipeline completo de validação de vocabulário:

    texto / .srt
        │
        ▼
    tokenização + limpeza
        │
        ▼
    busca direta no banco VLibras  ──(achou)──▶  termo validado
        │ (não achou)
        ▼
    fallback: LLM → sinônimos → banco
        │
        ├──(sinônimo ok)──▶  termo substituto
        └──(nenhum ok)  ──▶  datilologia / palavra original
        │
        ▼
    glosa final montada
─────────────────────────────────────────────────────────────────────
"""

import re
import unicodedata

from app.services.vlibras_db import buscar_termo
from app.services.sinonimo_service import resolver_via_sinonimo


# ─────────────────────────────────────────────────────────────────────
# TOKENIZAÇÃO
# ─────────────────────────────────────────────────────────────────────

# Caracteres que devem ser removidos antes de validar cada token
_PONTUACAO = re.compile(r"[^\w\s]", flags=re.UNICODE)

# Ruídos fonéticos comuns em legendas que não têm sinal em Libras
_RUIDOS = frozenset({
    "hmm", "hm", "ahh", "ah", "eh", "uh", "uhh",
    "né", "né?", "hein", "oxe", "ô", "ó",
})


def tokenizar(texto: str) -> list[str]:
    """
    Quebra o texto em tokens limpos (sem pontuação, sem ruídos).
    Mantém a capitalização original para log; a busca normaliza internamente.
    """
    texto = _PONTUACAO.sub(" ", texto)
    tokens = texto.split()
    return [t for t in tokens if t.lower() not in _RUIDOS and len(t) > 0]


# ─────────────────────────────────────────────────────────────────────
# VALIDAÇÃO DE UM ÚNICO TOKEN
# ─────────────────────────────────────────────────────────────────────

def validar_token(palavra: str) -> dict:
    """
    Valida um único token contra o banco VLibras.

    Retorna:
    {
        "palavra_original":  str,
        "termo_vlibras":     str | None,
        "estrategia":        "exato" | "lema" | "sinonimo" |
                             "datilologia" | "original",
        "validado":          bool,
        "sinonimos_testados": list[str]   (só no fallback)
    }
    """
    # ── 1. Busca direta (exata + lema) ──────────────────────────────
    termo = buscar_termo(palavra)
    if termo:
        estrategia = (
            "exato"
            if termo.upper().replace("_", "") == palavra.upper().replace("_", "")
            else "lema"
        )
        return {
            "palavra_original": palavra,
            "termo_vlibras": termo,
            "estrategia": estrategia,
            "validado": True,
            "sinonimos_testados": [],
        }

    # ── 2. Fallback: LLM → sinônimos ────────────────────────────────
    resultado = resolver_via_sinonimo(palavra)

    validado = resultado["estrategia"] in ("sinonimo",)

    return {
        "palavra_original": palavra,
        "termo_vlibras": resultado["termo_vlibras"],
        "estrategia": resultado["estrategia"],
        "validado": validado,
        "sinonimos_testados": resultado["sinonimos_testados"],
    }


# ─────────────────────────────────────────────────────────────────────
# VALIDAÇÃO DE UMA FRASE COMPLETA
# ─────────────────────────────────────────────────────────────────────

def validar_frase(texto: str) -> dict:
    """
    Valida todos os tokens de uma frase e monta a glosa final.

    Retorna:
    {
        "texto_original": str,
        "glosa":          str,           # para enviar ao VLibras
        "tokens":         list[dict],    # detalhe de cada palavra
        "total":          int,
        "validados":      int,
        "nao_validados":  int,
    }
    """
    tokens = tokenizar(texto)
    resultados = []

    for palavra in tokens:
        r = validar_token(palavra)
        resultados.append(r)

    # Monta a glosa: usa termo_vlibras quando disponível, senão a palavra original
    partes_glosa = []
    for r in resultados:
        if r["termo_vlibras"]:
            partes_glosa.append(r["termo_vlibras"])
        else:
            partes_glosa.append(r["palavra_original"].upper())

    glosa = " ".join(partes_glosa)

    validados = sum(1 for r in resultados if r["validado"])

    return {
        "texto_original": texto,
        "glosa": glosa,
        "tokens": resultados,
        "total": len(resultados),
        "validados": validados,
        "nao_validados": len(resultados) - validados,
    }


# ─────────────────────────────────────────────────────────────────────
# VALIDAÇÃO DE ENTRADAS SRT (lista de entries do parse_srt)
# ─────────────────────────────────────────────────────────────────────

def validar_entries_srt(entries: list[dict]) -> list[dict]:
    """
    Recebe a lista de entries já parseadas (saída de parse_srt) e
    enriquece cada uma com a glosa validada.

    Cada entry de saída terá os campos originais + :
        "glosa":          str    → enviada ao VLibras
        "validacao":      dict   → detalhe completo de validar_frase()
    """
    resultado = []
    total = len(entries)

    for i, entry in enumerate(entries, start=1):
        texto = entry.get("original", "")
        print(f"🔍 [{i}/{total}] Validando: {texto!r}")

        validacao = validar_frase(texto)

        resultado.append({
            **entry,
            "glosa": validacao["glosa"],
            "validacao": validacao,
        })

    return resultado
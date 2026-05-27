"""
vlibras_db.py
─────────────────────────────────────────────────────────────────────
Carrega os arquivos JSON do VLibras uma única vez na memória e expõe
funções de busca com normalização (sem acento, maiúsculas).

Os arquivos esperados em  <RAIZ>/vlibrasDataBase/:
    signspatch201830.json
    signspatch201831.json

Cada arquivo é uma lista de objetos  { "name": "TERMO", "patch": "..." }
─────────────────────────────────────────────────────────────────────
"""

import json
import os
import unicodedata

# ─────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DE CAMINHOS
# ─────────────────────────────────────────────────────────────────────

_BASE_DIR = os.path.dirname(                  # app/services/
    os.path.dirname(                          # app/
        os.path.abspath(__file__)
    )
)

VLIBRAS_DB_DIR = os.path.join(
    os.path.dirname(_BASE_DIR),               # raiz do projeto
    "vlibrasDataBase"
)

_DB_FILES = [
    "signspatch201830.json",
    "signspatch201831.json",
]

# ─────────────────────────────────────────────────────────────────────
# NORMALIZAÇÃO
# ─────────────────────────────────────────────────────────────────────

def normalizar(texto: str) -> str:
    """
    Converte para maiúsculas e remove acentos/diacríticos.
    Exemplo: "abandonár" → "ABANDONAR"
    """
    texto = texto.upper()
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# ─────────────────────────────────────────────────────────────────────
# CARGA E CACHE (executado uma única vez na importação do módulo)
# ─────────────────────────────────────────────────────────────────────

# Estrutura principal: { "TERMO_NORMALIZADO": "TERMO_ORIGINAL_NO_JSON" }
_vocab: dict[str, str] = {}

# Índice secundário para busca por "miolo":
# { "LEMA_NORMALIZADO": "TERMO_ORIGINAL_NO_JSON" }
# Ex.: "1S_ABANDONAR_1S" → chave "ABANDONAR" → valor "1S_ABANDONAR_1S"
_lema_index: dict[str, str] = {}


def _extrair_lema(nome: str) -> str | None:
    """
    Extrai o lema central de termos compostos como '1S_ABANDONAR_1S'
    ou '0_QUILÔMETRO'.

    Regra: remove segmentos puramente numéricos (ou compostos por
    dígitos + 'S') das extremidades e retorna o que sobrar.
    Retorna None se o lema for igual ao nome original (sem prefixos).
    """
    import re
    partes = nome.split("_")
    prefixo_re = re.compile(r"^\d+S?$")

    # Remove prefixos/sufixos numéricos das bordas
    while partes and prefixo_re.match(partes[0]):
        partes.pop(0)
    while partes and prefixo_re.match(partes[-1]):
        partes.pop()

    lema = "_".join(partes)

    # Só é índice secundário se o lema for diferente do nome completo
    if lema and lema != nome:
        return lema
    return None


def _carregar_banco() -> None:
    """Lê todos os arquivos JSON e popula _vocab e _lema_index."""
    total = 0
    for filename in _DB_FILES:
        path = os.path.join(VLIBRAS_DB_DIR, filename)
        if not os.path.exists(path):
            print(f"⚠️  Arquivo não encontrado: {path}")
            continue

        with open(path, "r", encoding="utf-8") as f:
            dados = json.load(f)

        for item in dados:
            nome_original = item.get("name", "").strip()
            if not nome_original:
                continue

            chave = normalizar(nome_original)
            _vocab[chave] = nome_original
            total += 1

            # Índice de lema (miolo do termo)
            lema = _extrair_lema(chave)
            if lema and lema not in _lema_index:
                _lema_index[lema] = nome_original

    print(f"✅ VLibras DB carregado: {total} termos | "
          f"{len(_lema_index)} lemas indexados")


# Executa na importação
_carregar_banco()


# ─────────────────────────────────────────────────────────────────────
# API PÚBLICA
# ─────────────────────────────────────────────────────────────────────

def buscar_termo(palavra: str) -> str | None:
    """
    Busca uma palavra no vocabulário VLibras.

    Ordem de prioridade:
        1. Correspondência exata normalizada  ("CASA" → "CASA")
        2. Correspondência por lema           ("ABANDONAR" → "1S_ABANDONAR_1S")

    Retorna o termo exato do JSON ou None se não encontrado.
    """
    chave = normalizar(palavra)

    # 1. Exata
    if chave in _vocab:
        return _vocab[chave]

    # 2. Por lema
    if chave in _lema_index:
        return _lema_index[chave]

    return None


def existe(palavra: str) -> bool:
    """Atalho booleano para buscar_termo."""
    return buscar_termo(palavra) is not None


def tamanho_vocab() -> int:
    """Retorna o número de termos carregados."""
    return len(_vocab)
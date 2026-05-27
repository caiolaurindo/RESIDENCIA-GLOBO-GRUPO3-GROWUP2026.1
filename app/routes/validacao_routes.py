"""
validacao_routes.py
─────────────────────────────────────────────────────────────────────
Rotas Flask para a camada de validação de vocabulário VLibras.

Endpoints:
    POST /validar-frase        → valida texto livre
    POST /validar-srt          → valida arquivo .srt completo
    GET  /vocab/info           → informações sobre o banco carregado
    GET  /vocab/buscar?q=<w>   → testa uma palavra manualmente
─────────────────────────────────────────────────────────────────────
"""

import traceback

from flask import Blueprint, request, jsonify

from app.utils.parser import parse_srt

from app.services.vlibras_db import (
    buscar_termo,
    tamanho_vocab,
)

from app.services.validacao_service import (
    validar_frase,
    validar_entries_srt,
)

# ─────────────────────────────────────────────────────────────────────
# BLUEPRINT
# ─────────────────────────────────────────────────────────────────────

validacao_bp = Blueprint("validacao", __name__)


# ─────────────────────────────────────────────────────────────────────
# POST /validar-frase
# ─────────────────────────────────────────────────────────────────────

@validacao_bp.route("/validar-frase", methods=["POST"])
def endpoint_validar_frase():
    """
    Body JSON: { "texto": "Olá, como você está?" }

    Retorna a glosa validada e o detalhe de cada token.
    """
    try:
        body = request.get_json(force=True, silent=True) or {}
        texto = body.get("texto", "").strip()

        if not texto:
            return jsonify({"error": "Campo 'texto' é obrigatório"}), 400

        resultado = validar_frase(texto)

        return jsonify({"success": True, **resultado})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────
# POST /validar-srt
# ─────────────────────────────────────────────────────────────────────

@validacao_bp.route("/validar-srt", methods=["POST"])
def endpoint_validar_srt():
    """
    Multipart form-data: campo 'file' com o arquivo .srt.

    Retorna cada legenda enriquecida com a glosa validada.
    """
    try:
        if "file" not in request.files:
            return jsonify({"error": "Arquivo não enviado"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "Arquivo inválido"}), 400

        srt_content = file.read().decode("utf-8")
        entries = parse_srt(srt_content)

        if not entries:
            return jsonify({"error": "Nenhuma legenda encontrada no SRT"}), 422

        print(f"🎬 SRT recebido: {len(entries)} legendas")

        entries_validadas = validar_entries_srt(entries)

        return jsonify({
            "success": True,
            "total": len(entries_validadas),
            "entries": entries_validadas,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────
# GET /vocab/info
# ─────────────────────────────────────────────────────────────────────

@validacao_bp.route("/vocab/info", methods=["GET"])
def vocab_info():
    """Retorna metadados do banco VLibras carregado em memória."""
    return jsonify({
        "success": True,
        "total_termos": tamanho_vocab(),
        "status": "carregado",
    })


# ─────────────────────────────────────────────────────────────────────
# GET /vocab/buscar?q=palavra
# ─────────────────────────────────────────────────────────────────────

@validacao_bp.route("/vocab/buscar", methods=["GET"])
def vocab_buscar():
    """
    Testa uma palavra manualmente contra o banco.
    Ex.: GET /vocab/buscar?q=abandonar
    """
    palavra = request.args.get("q", "").strip()

    if not palavra:
        return jsonify({"error": "Parâmetro 'q' é obrigatório"}), 400

    termo = buscar_termo(palavra)

    return jsonify({
        "success": True,
        "palavra": palavra,
        "encontrado": termo is not None,
        "termo_vlibras": termo,
    })
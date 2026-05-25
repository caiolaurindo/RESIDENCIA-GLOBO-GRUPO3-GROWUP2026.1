from flask import (
    Blueprint,
    request,
    jsonify,
    send_from_directory
)

import os
import traceback

from app.utils.parser import parse_srt

from app.services.groq_service import (
    otimizar_srt_completo
)

from app.services.srt_service import (
    gerar_srt
)

from app.services.ffmpeg_service import (
    salvar_video_mp4,
    MEDIA_DIR
)

# =========================================================
# BLUEPRINT
# =========================================================

srt_bp = Blueprint(
    'srt',
    __name__
)

# =========================================================
# HEALTH
# =========================================================

@srt_bp.route('/')
def home():

    return jsonify({
        "status": "online"
    })

# =========================================================
# OTIMIZAR SRT
# =========================================================

@srt_bp.route(
    '/otimizar-srt',
    methods=['POST']
)
def otimizar_srt():

    try:

        # =====================================
        # VALIDAR ARQUIVO
        # =====================================

        if 'file' not in request.files:

            return jsonify({
                "error":
                    "Arquivo não enviado"
            }), 400

        file = request.files['file']

        if file.filename == '':

            return jsonify({
                "error":
                    "Arquivo inválido"
            }), 400

        # =====================================
        # LER SRT
        # =====================================

        srt_content = (
            file.read()
            .decode('utf-8')
        )

        # =====================================
        # PARSE
        # =====================================

        entries = parse_srt(
            srt_content
        )

        print(
            f"🎬 TOTAL LEGENDAS: {len(entries)}"
        )

        # =====================================
        # OTIMIZAÇÃO IA
        # =====================================

        otimizado = otimizar_srt_completo(
            entries
        )

        resultado = []

        # =====================================
        # MAPEAR RESULTADO
        # =====================================

        for item in otimizado:

            idx = item["id"]

            texto_otimizado = (
                item["texto_otimizado"]
                .strip()
            )

            original = entries[idx]

            print(
                f"✅ {original['original']}"
            )

            print(
                f"🤟 {texto_otimizado}"
            )

            resultado.append({

                "start":
                    original["start"],

                "end":
                    original["end"],

                "texto_original":
                    original["original"],

                "texto_otimizado":
                    texto_otimizado
            })

        # =====================================
        # GERAR NOVO SRT
        # =====================================

        novo_srt = gerar_srt(
            resultado
        )

        return jsonify({

            "success": True,

            "total":
                len(resultado),

            "entries":
                resultado,

            "srt_otimizado":
                novo_srt
        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# =========================================================
# SALVAR VIDEO
# =========================================================

@srt_bp.route(
    '/salvar-video',
    methods=['POST']
)
def salvar_video():

    try:

        # =====================================
        # VALIDAR VIDEO
        # =====================================

        if 'video' not in request.files:

            return jsonify({
                "error":
                    "Vídeo não enviado"
            }), 400

        video = request.files['video']

        # =====================================
        # SALVAR MP4
        # =====================================

        mp4_path = salvar_video_mp4(
            video
        )

        filename = os.path.basename(
            mp4_path
        )

        print(
            f"✅ VIDEO FINAL: {mp4_path}"
        )

        return jsonify({

            "success": True,

            "video_mp4":
                mp4_path,

            "filename":
                filename,

            "download_url":
                f"/download-video/{filename}"
        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# =========================================================
# DOWNLOAD VIDEO
# =========================================================

@srt_bp.route(
    '/download-video/<filename>',
    methods=['GET']
)
def download_video(filename):

    try:

        return send_from_directory(

            MEDIA_DIR,

            filename,

            as_attachment=True
        )

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500

# =========================================================
# LISTAR VIDEOS
# =========================================================

@srt_bp.route(
    '/videos',
    methods=['GET']
)
def listar_videos():

    try:

        arquivos = []

        for file in os.listdir(MEDIA_DIR):

            if file.endswith('.mp4'):

                arquivos.append({

                    "nome": file,

                    "download":
                        f"/download-video/{file}"
                })

        arquivos.sort(
            key=lambda x: x["nome"],
            reverse=True
        )

        return jsonify({

            "success": True,

            "total":
                len(arquivos),

            "videos":
                arquivos
        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500


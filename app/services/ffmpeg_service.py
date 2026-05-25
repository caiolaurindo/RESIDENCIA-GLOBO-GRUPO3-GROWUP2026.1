import os
import subprocess

from datetime import datetime

from app.config import (
    MEDIA_DIR,
    FFMPEG_PATH
)

def salvar_video_mp4(video):

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    webm_path = os.path.join(

        MEDIA_DIR,

        f"libras_{timestamp}.webm"
    )

    mp4_path = os.path.join(

        MEDIA_DIR,

        f"libras_{timestamp}.mp4"
    )

    # ============================================
    # SAVE WEBM
    # ============================================

    video.save(webm_path)

    print(f"🎥 WEBM salvo: {webm_path}")

    # ============================================
    # CONVERTER MP4 FULL HD
    # ============================================

    command = [

        FFMPEG_PATH,

        "-y",

        "-i",
        webm_path,

        "-vf",
        "scale=1920:1080",

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "23",

        "-pix_fmt",
        "yuv420p",

        "-movflags",
        "+faststart",

        mp4_path
    ]

    result = subprocess.run(

        command,

        capture_output=True,

        text=True
    )

    print(result.stdout)
    print(result.stderr)

    if result.returncode != 0:

        raise Exception(result.stderr)

    print(f"✅ MP4 salvo: {mp4_path}")

    # ============================================
    # REMOVE WEBM
    # ============================================

    if os.path.exists(webm_path):

        os.remove(webm_path)

    return mp4_path
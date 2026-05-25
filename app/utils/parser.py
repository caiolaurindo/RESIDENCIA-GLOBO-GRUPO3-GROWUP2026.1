import re

from app.utils.timestamp import (
    timestamp_para_segundos
)

def parse_srt(text):

    blocks = re.split(
        r'\r?\n\r?\n',
        text.strip()
    )

    entries = []

    for block in blocks:

        lines = block.strip().splitlines()

        if len(lines) < 3:
            continue

        try:

            index = lines[0]

            time_line = lines[1]

            times = time_line.split(' --> ')

            start = times[0].strip()

            end = times[1].strip()

            original_text = ' '.join(
                lines[2:]
            ).strip()

            start_seconds = (
                timestamp_para_segundos(start)
            )

            end_seconds = (
                timestamp_para_segundos(end)
            )

            duration = (
                end_seconds - start_seconds
            )

            entries.append({

                "index":
                    index,

                "start":
                    start,

                "end":
                    end,

                "duration":
                    duration,

                "original":
                    original_text
            })

        except Exception:
            continue

    return entries
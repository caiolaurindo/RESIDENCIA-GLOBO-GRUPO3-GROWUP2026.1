def gerar_srt(entries):

    resultado = []

    for i, e in enumerate(entries, start=1):

        resultado.append(str(i))

        resultado.append(
            f"{e['start']} --> {e['end']}"
        )

        resultado.append(
            e['texto_otimizado']
        )

        resultado.append("")

    return '\n'.join(resultado)
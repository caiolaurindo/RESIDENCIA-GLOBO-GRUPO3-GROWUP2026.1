def timestamp_para_segundos(ts):

    h, m, s_ms = ts.split(':')

    s, ms = s_ms.split(',')

    return (

        int(h) * 3600 +

        int(m) * 60 +

        int(s) +

        int(ms) / 1000
    )
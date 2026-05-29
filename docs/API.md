# Referência da API

API REST em **Flask**, porta padrão **5000**, com **CORS** habilitado para o frontend.

**Base URL:** `https://residencia-globo-grupo3-growup2026-1-1.onrender.com/`

---

## Índice

1. [Visão geral](#visão-geral)
2. [Formato de erros](#formato-de-erros)
3. [API principal (SRT e vídeo)](#api-principal-srt-e-vídeo)
4. [API de validação (vocabulário VLibras)](#api-de-validação-vocabulário-vlibras)
5. [Modelos de dados](#modelos-de-dados)
6. [Serviços internos (backend)](#serviços-internos-backend)

---

## Visão geral

| Grupo | Prefixo | Uso |
|-------|---------|-----|
| SRT / vídeo | rotas na raiz (`/`) | Fluxo do conversor: otimizar legendas, salvar e baixar MP4 |
| Validação | rotas na raiz (`/`) | Validar texto contra o banco de sinais do VLibras (sem gravar vídeo) |

O frontend em [`frontend/index.html`](../frontend/index.html) consome principalmente:

- `POST /otimizar-srt`
- `POST /salvar-video`
- `GET /download-video/<filename>`

A API de validação é independente e pode ser usada por scripts, testes ou integrações futuras.

---

## Formato de erros

Respostas de erro costumam seguir:

```json
{
  "error": "mensagem descritiva"
}
```

Ou, em rotas que usam o padrão `success`:

```json
{
  "success": false,
  "error": "mensagem descritiva"
}
```

| HTTP | Significado usual |
|------|-------------------|
| 400 | Parâmetro ou arquivo ausente / inválido |
| 422 | SRT sem legendas parseáveis |
| 500 | Erro interno (IA, FFmpeg, exceção não tratada) |

---

## API principal (SRT e vídeo)

### `GET /`

Health check do servidor.

**Resposta 200:**

```json
{
  "status": "online"
}
```

---

### `POST /otimizar-srt`

Envia um arquivo `.srt`, faz o parse das legendas e reescreve cada frase com **Groq** (modelo `llama-3.3-70b-versatile`) para ficar mais adequada ao avatar do VLibras.

**Content-Type:** `multipart/form-data`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `file` | arquivo | sim | Arquivo `.srt` em UTF-8 |

**Resposta 200 (sucesso):**

```json
{
  "success": true,
  "total": 5,
  "entries": [
    {
      "start": "00:00:00,000",
      "end": "00:00:04,000",
      "texto_original": "Olá, bem-vindo ao teste.",
      "texto_otimizado": "OLA BEM VINDO TESTE"
    }
  ],
  "srt_otimizado": "1\n00:00:00,000 --> 00:00:04,000\n..."
}
```

| Campo | Descrição |
|-------|-----------|
| `entries` | Lista usada pelo frontend para sincronizar o avatar (`texto_otimizado` + timestamps originais) |
| `srt_otimizado` | Novo arquivo SRT completo em texto, só com as frases otimizadas |

**Erros:**

- `400` — campo `file` ausente ou nome vazio
- `500` — falha na Groq (`GROQ_API_KEY` inválida/ausente) ou JSON inválido retornado pela IA

**Implementação:** [`app/routes/srt_routes.py`](../app/routes/srt_routes.py) → `parse_srt` + `otimizar_srt_completo` + `gerar_srt`

**Exemplo curl:**

```bash
curl -X POST http://localhost:5000/otimizar-srt \
  -F "file=@teste-avatar.srt"
```

---

### `POST /salvar-video`

Recebe o vídeo gravado no navegador (WebM), salva temporariamente, converte para **MP4 1920×1080** (H.264) com FFmpeg e remove o WebM.

**Content-Type:** `multipart/form-data`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `video` | arquivo | sim | Blob WebM enviado pelo `MediaRecorder` |

**Resposta 200 (sucesso):**

```json
{
  "success": true,
  "video_mp4": "C:\\...\\media\\libras_20260529_134615.mp4",
  "filename": "libras_20260529_134615.mp4",
  "download_url": "/download-video/libras_20260529_134615.mp4"
}
```

| Campo | Descrição |
|-------|-----------|
| `video_mp4` | Caminho absoluto no servidor (útil para debug) |
| `filename` | Nome do arquivo em `media/` |
| `download_url` | Caminho relativo para montar o link de download no frontend |

**Erros:**

- `400` — campo `video` ausente
- `500` — FFmpeg não encontrado ou falha na conversão

**Parâmetros FFmpeg** (via [`app/services/ffmpeg_service.py`](../app/services/ffmpeg_service.py)):

- Codec: `libx264`, preset `medium`, CRF `23`
- Escala: `1920:1080`
- `+faststart` para streaming web

**Exemplo curl:**

```bash
curl -X POST http://localhost:5000/salvar-video \
  -F "video=@gravacao.webm"
```

---

### `GET /download-video/<filename>`

Baixa um MP4 gerado na pasta `media/`.

**Parâmetros de URL:**

| Nome | Descrição |
|------|-----------|
| `filename` | Nome do arquivo (ex.: `libras_20260529_134615.mp4`) |

**Resposta 200:** arquivo binário (`Content-Disposition: attachment`)

**Erros:** `500` se o arquivo não existir

**Exemplo:**

```
GET http://localhost:5000/download-video/libras_20260529_134615.mp4
```

No frontend, o link costuma ser:

`http://localhost:5000` + `download_url`

---

### `GET /videos`

Lista todos os `.mp4` em `media/`, ordenados do mais recente ao mais antigo (por nome).

**Resposta 200:**

```json
{
  "success": true,
  "total": 2,
  "videos": [
    {
      "nome": "libras_20260529_134615.mp4",
      "download": "/download-video/libras_20260529_134615.mp4"
    }
  ]
}
```

---

## API de validação (vocabulário VLibras)

Camada que valida palavras contra o banco JSON em `vlibrasDataBase/` (`signspatch201830.json`, `signspatch201831.json`). **Não é usada** pelo `frontend/index.html` no fluxo atual de gravação.

Blueprint: [`app/routes/validacao_routes.py`](../app/routes/validacao_routes.py)

### Pipeline de validação (por token)

1. Tokenização (remove pontuação e ruídos como "hmm", "ah")
2. Busca no banco: match exato ou por lema (`1S_ABANDONAR_1S` → `ABANDONAR`)
3. Se não achar: Groq sugere até 3 sinônimos → testa cada um no banco
4. Monta a **glosa** final (termos VLibras separados por espaço)

---

### `POST /validar-frase`

Valida um texto livre.

**Content-Type:** `application/json`

**Body:**

```json
{
  "texto": "Olá, como você está?"
}
```

**Resposta 200:**

```json
{
  "success": true,
  "texto_original": "Olá, como você está?",
  "glosa": "OLA COMO VOCE ESTAR",
  "tokens": [
    {
      "palavra_original": "Olá",
      "termo_vlibras": "OLA",
      "estrategia": "exato",
      "validado": true,
      "sinonimos_testados": []
    }
  ],
  "total": 4,
  "validados": 3,
  "nao_validados": 1
}
```

| Campo `estrategia` (token) | Significado |
|----------------------------|-------------|
| `exato` | Palavra encontrada no banco |
| `lema` | Encontrada via lema composto |
| `sinonimo` | Substituída por sinônimo sugerido pela IA |
| `datilologia` / `original` | Mantida a palavra original (sem sinal garantido) |

**Erros:** `400` se `texto` vazio; `500` em falha interna

---

### `POST /validar-srt`

Valida todas as legendas de um arquivo SRT.

**Content-Type:** `multipart/form-data`

| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| `file` | arquivo `.srt` | sim |

**Resposta 200:**

```json
{
  "success": true,
  "total": 5,
  "entries": [
    {
      "index": "1",
      "start": "00:00:00,000",
      "end": "00:00:04,000",
      "duration": 4.0,
      "original": "Olá, bem-vindo.",
      "glosa": "OLA BEM VINDO",
      "validacao": { }
    }
  ]
}
```

Cada `entry` repete os campos do parse + `glosa` + objeto `validacao` (mesmo formato de `/validar-frase`).

**Erros:** `400`, `422` (SRT vazio), `500`

---

### `GET /vocab/info`

Metadados do vocabulário carregado em memória na inicialização do servidor.

**Resposta 200:**

```json
{
  "success": true,
  "total_termos": 12345,
  "status": "carregado"
}
```

---

### `GET /vocab/buscar`

Testa uma palavra no banco.

**Query:**

| Parâmetro | Obrigatório | Exemplo |
|-----------|-------------|---------|
| `q` | sim | `?q=abandonar` |

**Resposta 200:**

```json
{
  "success": true,
  "palavra": "abandonar",
  "encontrado": true,
  "termo_vlibras": "1S_ABANDONAR_1S"
}
```

**Erros:** `400` se `q` ausente

---

## Modelos de dados

### Legenda após `parse_srt`

```json
{
  "index": "1",
  "start": "00:00:00,000",
  "end": "00:00:04,000",
  "duration": 4.0,
  "original": "texto da legenda"
}
```

Timestamps no formato SRT (`HH:MM:SS,mmm`).

### Entrada otimizada (`/otimizar-srt`)

```json
{
  "start": "00:00:00,000",
  "end": "00:00:04,000",
  "texto_original": "...",
  "texto_otimizado": "..."
}
```

---

## Serviços internos (backend)

| Módulo | Responsabilidade |
|--------|------------------|
| [`app/utils/parser.py`](../app/utils/parser.py) | Parse do conteúdo SRT em blocos |
| [`app/utils/timestamp.py`](../app/utils/timestamp.py) | Conversão de timestamp para segundos |
| [`app/services/groq_service.py`](../app/services/groq_service.py) | Otimização em lote via Groq |
| [`app/services/srt_service.py`](../app/services/srt_service.py) | Montagem do SRT de saída |
| [`app/services/ffmpeg_service.py`](../app/services/ffmpeg_service.py) | WebM → MP4 |
| [`app/services/vlibras_db.py`](../app/services/vlibras_db.py) | Carga e busca no vocabulário |
| [`app/services/sinonimo_service.py`](../app/services/sinonimo_service.py) | Fallback de sinônimos via Groq |
| [`app/services/validacao_service.py`](../app/services/validacao_service.py) | Orquestração da validação |

---

## Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `GROQ_API_KEY` | sim (otimizar + sinônimos) | Chave da API Groq |
| `FFMPEG_PATH` | não | Caminho do executável FFmpeg (padrão: `ffmpeg` no PATH) |

Arquivo de exemplo: [`.env.example`](../.env.example)

---

## Testes

Testes da camada de validação:

```bash
python -m pytest tests/test_validacao.py -v
```

Requer `GROQ_API_KEY` configurada para testes que chamam sinônimos.

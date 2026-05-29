# 🤟 Conversor SRT → Libras IA

Esta documentação descreve a arquitetura, o funcionamento interno e as integrações do **Conversor SRT para Libras IA**. A aplicação web tem como objetivo otimizar arquivos de legendas (SRT) usando Inteligência Artificial e, em seguida, sincronizar essas legendas com o avatar 3D do VLibras, gravando a execução e gerando um vídeo final (MP4).

---

# 📋 Sumário

1. [Visão Geral da Arquitetura](#visão-geral-da-arquitetura)
2. [Integração e Uso Correto do VLibras](#integração-e-uso-correto-do-vlibras)
3. [Gravação do Avatar (Canvas Capture)](#gravação-do-avatar-canvas-capture)
4. [Integração com a API Rest](#integração-com-a-api-rest)
5. [Fluxo de Execução Completo](#fluxo-de-execução-completo)
6. [Instruções de Configuração](#instruções-de-configuração)

---

# 🏗️ Visão Geral da Arquitetura

O front-end (HTML/JS/CSS) atua como um orquestrador. Ele não faz o processamento pesado; em vez disso, ele se comunica com uma API Python/Node (rodando em `https://residencia-globo-grupo3-growup2026-1-1.onrender.com/`) para a conversão de IA e processamento de vídeo, e com a API injetada do **VLibras** para renderização 3D da língua de sinais.

## Tecnologias e APIs Envolvidas

* **VLibras Widget API**: Roteiro de animação e renderização 3D.
* **MediaRecorder API (Nativa do Browser)**: Captura do canvas 3D em tempo real.
* **Backend (Localhost API)**: Processamento de IA (Texto → Glosas) e conversão WebM → MP4 Full HD.

---

# 🧠 Integração e Uso Correto do VLibras

O VLibras, por padrão, é um widget flutuante projetado para sobrepor sites inteiros. Para este projeto, nós o **"enjaulamos"** dentro de um container específico (`div#avatarContainer`) para compor a interface de estúdio.

## 1. Inicialização

O script padrão do VLibras é carregado via CDN:

```html
<script src="https://vlibras.gov.br/app/vlibras-plugin.js"></script>
```

E instanciado globalmente:

```javascript
new window.VLibras.Widget('https://vlibras.gov.br/app');
```

---

## 2. O "Pulo do Gato" do CSS (Isolamento do Widget)

Como o VLibras usa `position: fixed`, ele ignoraria a grid da interface se não fosse por uma técnica específica de CSS.

O `.vlibras-embed-container` cria um novo contexto de empilhamento (*stacking context*):

```css
.vlibras-embed-container {
    /* Cria novo stacking context para impedir o position: fixed de vazar para a tela toda */
    transform: translateZ(0);
    contain: layout style;
    position: relative;
}
```

Além disso, forçamos o widget a ter:

* `position: absolute !important`
* `width: 100%`
* `height: 100%`

Tudo isso para preencher completamente o container pai.

Também escondemos o botão nativo de acessibilidade do VLibras:

```css
[vw-access-button] {
    display: none !important;
}
```

---

## 3. Execução Programática de Sinais

Para enviar os textos para o avatar sem intervenção humana, utilizamos a API de player exposta pelo plugin do VLibras após o carregamento:

```javascript
// Onde `texto_otimizado` é a frase simplificada pela IA (glosa)
window.plugin?.player?.translate(item.texto_otimizado);
```

---

# 🎥 Gravação do Avatar (Canvas Capture)

Este é um dos módulos mais avançados do código. Nós extraímos a stream de vídeo diretamente do motor 3D do VLibras em vez de pedir ao usuário para gravar a tela.

---

## 1. Atravessando o Shadow DOM

O VLibras renderiza seu modelo 3D em um `<canvas>`, mas esse canvas fica protegido dentro de um Shadow Root (encapsulamento de componentes Web).

A função `findCanvasDeep(root)` é recursiva e vasculha a árvore do DOM ignorando as barreiras do Shadow DOM para encontrar o elemento `<canvas>` onde o 3D está rodando.

---

## 2. Captura e Gravação

Após encontrar o canvas:

### Captura da Stream

```javascript
const stream = canvas.captureStream(30);
```

* Captura em tempo real
* 30 FPS

---

### Inicialização do MediaRecorder

```javascript
const recorder = new MediaRecorder(stream, {
    mimeType: 'video/webm'
});
```

---

### Coleta dos Chunks

```javascript
let chunks = [];

recorder.ondataavailable = (event) => {
    if (event.data.size > 0) {
        chunks.push(event.data);
    }
};
```

---

# 🔌 Integração com a API Rest

A aplicação presume que há um backend rodando em:

```txt
http://localhost:5000
```

---

## 1. POST `/otimizar-srt`

### Objetivo

Enviar o arquivo SRT cru para ser otimizado pela IA em uma gramática mais fácil para o VLibras (glosas).

---

### Payload

```javascript
const formData = new FormData();
formData.append("file", arquivoSRT);
```

---

### Resposta Esperada

```json
{
  "success": true,
  "entries": [
    {
      "texto_original": "Olá, seja bem vindo",
      "texto_otimizado": "OI BEM-VINDO",
      "start": "00:00:01,000",
      "end": "00:00:04,500"
    }
  ]
}
```

---

## 2. POST `/salvar-video`

### Objetivo

Enviar o vídeo WebM capturado no frontend para o backend para conversão em MP4 Full HD.

---

### Payload

```javascript
const formData = new FormData();
formData.append("video", videoBlob);
```

---

### Resposta Esperada

```json
{
  "success": true,
  "video_mp4": "/media/arquivo_final_123.mp4"
}
```

---

# 🔄 Fluxo de Execução Completo

A sequência correta dos eventos durante a execução do sistema é:

---

## 1. Upload (`processarSRT()`)

O usuário sobe o arquivo `.srt`.

O front-end:

1. Envia o arquivo para a API
2. Recebe o array de legendas otimizadas
3. Converte os tempos SRT para milissegundos usando `srtToMs()`
4. Renderiza a prévia lateral usando `renderPreview()`

---

## 2. Ativação do Avatar (`abrirVLibrasEGravar()`)

Um clique programático é feito no botão oculto do VLibras:

```javascript
toggleAvatarLibras();
```

Isso força o carregamento do boneco 3D.

---

## 3. Espera (`esperarVLibras()`)

O sistema faz polling a cada `500ms` verificando se:

```javascript
window.plugin.player.translate
```

já existe na memória.

Quando existir, significa que:

* O Unity/WebGL terminou de carregar
* O avatar já está pronto para receber comandos

---

## 4. Sincronização e Gravação (`gerarVideo()`)

### Início da Gravação

O `MediaRecorder` inicia a captura do canvas.

---

### Enfileiramento das Falas

Um loop com `setTimeout()` baseado nos timestamps do SRT agenda as chamadas:

```javascript
window.plugin.player.translate(item.texto_otimizado);
```

Isso garante sincronização exata entre:

* Legenda
* Movimento do avatar
* Linha temporal original do vídeo

---

### Exemplo Simplificado

```javascript
setTimeout(() => {
    window.plugin.player.translate(item.texto_otimizado);
}, item.start_ms);
```

---

## 5. Finalização (`enviarVideo()`)

Após o último sinal + 3 segundos:

1. A gravação é interrompida
2. Os chunks são unidos em um `Blob`
3. O arquivo WebM é enviado para `/salvar-video`
4. O backend converte para MP4
5. O link final é liberado para download

---

# 🛠️ Instruções de Configuração para Próximos Desenvolvedores

## Backend

Garanta que a API esteja rodando no IP/porta estipulados na variável:

```javascript
const API_URL = "http://localhost:5000";
```

---

## Navegador

Este projeto deve ser executado em navegadores baseados em Chromium:

* Google Chrome
* Microsoft Edge
* Brave

Navegadores antigos ou Safari podem apresentar limitações em:

* `canvas.captureStream()`
* `MediaRecorder`
* codecs WebM

---

## Hospedagem / CORS

Caso o front-end e o backend estejam em domínios diferentes, o backend deverá permitir requisições CORS.

### Exemplo (Flask)

```python
from flask_cors import CORS

CORS(app)
```

---

## Manutenção do VLibras

Como o VLibras é carregado via CDN governamental:

```txt
https://vlibras.gov.br/app
```

o projeto depende da estabilidade dos servidores deles.

A função `findCanvasDeep()` foi criada para ser agnóstica à estrutura interna do widget, porém mudanças drásticas na arquitetura do VLibras podem exigir atualização da lógica de busca do `<canvas>`.

---

# ✅ Considerações Finais

O projeto combina:

* Processamento de linguagem natural (IA)
* Renderização 3D
* Captura de vídeo em tempo real
* Sincronização temporal de legendas

Tudo isso de forma automatizada diretamente no navegador.

A arquitetura foi desenhada para manter:

* desacoplamento entre front-end e back-end
* flexibilidade para futuras melhorias
* compatibilidade com pipelines de acessibilidade digital
* possibilidade futura de renderização em lote e cloud rendering

import { useState, useEffect, useRef, useCallback } from "react";

const API_URL = "http://localhost:5000";

// ── utilitários ──────────────────────────────────────────────────────────────

function srtToMs(time) {
  const [main, ms] = time.split(",");
  const [h, m, s] = main.split(":");
  return (
    parseInt(h) * 3600000 +
    parseInt(m) * 60000 +
    parseInt(s) * 1000 +
    parseInt(ms)
  );
}

function findCanvasDeep(root) {
  if (!root) return null;
  const direct = root.querySelector?.("canvas");
  if (direct) return direct;
  for (const el of root.querySelectorAll?.("*") ?? []) {
    if (el.shadowRoot) {
      const found = findCanvasDeep(el.shadowRoot);
      if (found) return found;
    }
  }
  return null;
}

// ── hook: VLibras ────────────────────────────────────────────────────────────

function useVLibras(containerRef) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;

    // injeta o script apenas uma vez
    if (!document.getElementById("vlibras-script")) {
      const script = document.createElement("script");
      script.id = "vlibras-script";
      script.src = "https://vlibras.gov.br/app/vlibras-plugin.js";
      script.onload = () => {
        new window.VLibras.Widget("https://vlibras.gov.br/app");
        waitForPlugin();
      };
      document.head.appendChild(script);
    } else if (window.VLibras) {
      waitForPlugin();
    }

    // Observa o DOM e move o wrapper injetado para dentro do nosso container
    const observer = new MutationObserver(() => {
      const wrapper = document.querySelector("[vw-plugin-wrapper]");
      if (wrapper && !containerRef.current.contains(wrapper)) {
        const parent = wrapper.closest("[vw]");
        if (parent) {
          // garante que o [vw] pai vá para dentro do container
          containerRef.current.appendChild(parent);
        }
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });

    return () => observer.disconnect();
  }, []);

  function waitForPlugin() {
    const iv = setInterval(() => {
      if (window.plugin?.player?.translate) {
        clearInterval(iv);
        setReady(true);
      }
    }, 500);
  }

  function translate(text) {
    window.plugin?.player?.translate(text);
  }

  function toggle() {
    const btn = document.querySelector("[vw-access-button]");
    if (btn) btn.click();
  }

  return { ready, translate, toggle };
}

// ── hook: gravação ───────────────────────────────────────────────────────────

function useRecorder() {
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timeoutsRef = useRef([]);
  const [recording, setRecording] = useState(false);

  function clearTimeouts() {
    timeoutsRef.current.forEach(clearTimeout);
    timeoutsRef.current = [];
  }

  async function start(glossas, onFinish) {
    const canvas = findCanvasDeep(document);
    if (!canvas) return { error: "Canvas não encontrado" };

    chunksRef.current = [];
    clearTimeouts();

    let stream;
    try {
      stream = canvas.captureStream(30);
    } catch {
      return { error: "captureStream não suportado" };
    }

    const mimeType =
      ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"].find(
        (m) => MediaRecorder.isTypeSupported(m)
      ) || "video/webm";

    const recorder = new MediaRecorder(stream, { mimeType });
    recorderRef.current = recorder;

    recorder.ondataavailable = (e) => {
      if (e.data?.size > 0) chunksRef.current.push(e.data);
    };
    recorder.onstop = () => {
      setRecording(false);
      const blob = new Blob(chunksRef.current, { type: "video/webm" });
      onFinish(blob);
    };

    recorder.start(100);
    setRecording(true);

    // agenda traduções
    glossas.forEach((item) => {
      const t = setTimeout(() => {
        window.plugin?.player?.translate(item.texto_otimizado);
      }, srtToMs(item.start));
      timeoutsRef.current.push(t);
    });

    // para automaticamente
    const total = srtToMs(glossas[glossas.length - 1].end) + 3000;
    timeoutsRef.current.push(setTimeout(stop, total));

    return { error: null };
  }

  function stop() {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop();
    }
    clearTimeouts();
  }

  return { recording, start, stop };
}

// ── componentes ──────────────────────────────────────────────────────────────

function UploadBox({ onChange }) {
  return (
    <div style={styles.uploadBox}>
      <span style={styles.uploadIcon}>📄</span>
      <h2 style={styles.uploadTitle}>Selecione o arquivo SRT</h2>
      <input
        type="file"
        accept=".srt"
        onChange={(e) => onChange(e.target.files[0])}
        style={styles.fileInput}
      />
    </div>
  );
}

function StatusBar({ status, recording }) {
  return (
    <div style={styles.statusContainer}>
      <span style={styles.statusText}>{status}</span>
      {recording && (
        <span style={styles.recordBadge}>🔴 GRAVANDO AVATAR</span>
      )}
    </div>
  );
}

function PreviewList({ glossas }) {
  return (
    <div style={styles.preview}>
      <h3 style={styles.previewTitle}>🧠 Prévia da IA</h3>
      <div style={styles.previewList}>
        {glossas.length === 0 && (
          <p style={styles.emptyMsg}>Nenhuma entrada ainda. Processe um SRT.</p>
        )}
        {glossas.map((item, i) => (
          <div key={i} style={styles.previewItem}>
            <div style={styles.original}>{item.texto_original}</div>
            <div style={styles.optimized}>🤟 {item.texto_otimizado}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AvatarPanel({ containerRef, recording }) {
  return (
    <div
      ref={containerRef}
      style={{
        ...styles.avatarContainer,
        borderColor: recording ? "#dc2626" : "#1e293b",
        boxShadow: recording ? "0 0 15px rgba(220,38,38,0.3)" : "none",
      }}
    >
      {/* estrutura base do VLibras — o plugin move seus elementos para cá */}
      <div vw="true" className="enabled" style={styles.vwRoot}>
        <div vw-access-button="true" className="active" style={{ display: "none" }} />
        <div vw-plugin-wrapper="true" style={styles.vwWrapper}>
          <div className="vw-plugin-top-wrapper" style={styles.vwTopWrapper} />
        </div>
      </div>
      <p style={styles.avatarPlaceholder}>
        Clique em "Abrir / Fechar VLibras" para carregar o avatar
      </p>
    </div>
  );
}

// ── app principal ─────────────────────────────────────────────────────────────

export default function App() {
  const [file, setFile] = useState(null);
  const [glossas, setGlossas] = useState([]);
  const [status, setStatus] = useState("Aguardando arquivo...");
  const [downloadUrl, setDownloadUrl] = useState(null);

  const containerRef = useRef(null);
  const { ready: vlibrasReady, toggle } = useVLibras(containerRef);
  const { recording, start: startRec, stop: stopRec } = useRecorder();

  // ── processar SRT ──
  async function processarSRT() {
    if (!file) { alert("Selecione um SRT"); return; }
    setStatus("🧠 IA otimizando legendas...");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${API_URL}/otimizar-srt`, { method: "POST", body: fd });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);
      setGlossas(data.entries);
      setStatus(`✅ ${data.entries.length} frases otimizadas`);
    } catch (e) {
      console.error(e);
      setStatus("❌ Erro ao processar SRT");
    }
  }

  // ── gerar vídeo ──
  async function gerarVideo() {
    if (glossas.length === 0) { alert("Processe o SRT primeiro."); return; }
    if (!vlibrasReady) { alert("Aguarde o VLibras carregar."); return; }

    setStatus("🎥 Gravando avatar VLibras...");
    setDownloadUrl(null);

    const { error } = await startRec(glossas, async (blob) => {
      await enviarVideo(blob);
    });

    if (error) setStatus(`❌ ${error}`);
  }

  // ── enviar vídeo ──
  async function enviarVideo(blob) {
    setStatus("⚡ Convertendo vídeo Full HD...");
    try {
      const fd = new FormData();
      fd.append("video", blob, "libras.webm");
      const res = await fetch(`${API_URL}/salvar-video`, { method: "POST", body: fd });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);
      const nome = data.video_mp4.split("\\").pop();
      setDownloadUrl(`${API_URL}/media/${nome}`);
      setStatus("✅ Vídeo salvo em /media");
    } catch (e) {
      console.error(e);
      setStatus("❌ Erro ao salvar vídeo");
    }
  }

  // ── render ──
  return (
    <div style={styles.body}>
      <div style={styles.container}>
        <div style={styles.card}>

          <h1 style={styles.h1}>🤟 Conversor SRT → Libras IA</h1>
          <p style={styles.subtitle}>Otimização automática de legendas para o VLibras usando IA.</p>

          <UploadBox onChange={setFile} />

          <div style={styles.buttons}>
            <button style={styles.btnPrimary} onClick={processarSRT}>
              ⚡ Processar SRT
            </button>
            <button style={styles.btnLibras} onClick={toggle}>
              🤟 Abrir / Fechar VLibras
            </button>
            <button
              style={recording ? styles.btnRecording : styles.btnSuccess}
              onClick={recording ? stopRec : gerarVideo}
            >
              {recording ? "⏹ Parar Gravação" : "🎬 Gerar Vídeo"}
            </button>
            {downloadUrl && (
              <a href={downloadUrl} style={styles.downloadBtn}>
                ⬇ Baixar MP4
              </a>
            )}
          </div>

          <StatusBar status={status} recording={recording} />

          <div style={styles.workspaceGrid}>
            <PreviewList glossas={glossas} />
            <AvatarPanel containerRef={containerRef} recording={recording} />
          </div>

        </div>
      </div>

      {/* CSS global para os elementos injetados pelo VLibras */}
      <style>{`
        [vw-access-button] { display: none !important; }

        [vw-plugin-wrapper] {
          position: absolute !important;
          inset: 0 !important;
          width: 100% !important;
          height: 100% !important;
          box-shadow: none !important;
          background: transparent !important;
        }

        .vw-plugin-top-wrapper {
          position: absolute !important;
          inset: 0 !important;
          width: 100% !important;
          height: 100% !important;
        }

        /* Força o wrapper injetado dinamicamente a ficar dentro do container */
        #vlibras-container [vw] {
          position: absolute !important;
          inset: 0 !important;
          width: 100% !important;
          height: 100% !important;
        }

        @keyframes pulse-recording {
          50% { opacity: 0.5; }
        }

        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #1e293b; border-radius: 10px; }
        ::-webkit-scrollbar-thumb { background: #475569; border-radius: 10px; }
      `}</style>
    </div>
  );
}

// ── estilos ───────────────────────────────────────────────────────────────────

const styles = {
  body: {
    fontFamily: "'Segoe UI', Arial, sans-serif",
    background: "#0f172a",
    color: "white",
    minHeight: "100vh",
    padding: "40px",
  },
  container: {
    maxWidth: 1100,
    margin: "auto",
  },
  card: {
    background: "#111827",
    borderRadius: 20,
    padding: 30,
    boxShadow: "0 0 40px rgba(0,0,0,0.4)",
  },
  h1: {
    fontSize: 36,
    marginBottom: 10,
  },
  subtitle: {
    color: "#94a3b8",
    marginBottom: 30,
  },
  uploadBox: {
    border: "2px dashed #334155",
    borderRadius: 16,
    padding: 40,
    textAlign: "center",
    marginBottom: 25,
    background: "#0b1220",
  },
  uploadIcon: {
    fontSize: 32,
    display: "block",
    marginBottom: 10,
  },
  uploadTitle: {
    fontSize: 20,
    marginBottom: 10,
  },
  fileInput: {
    marginTop: 12,
    color: "white",
  },
  buttons: {
    display: "flex",
    gap: 15,
    flexWrap: "wrap",
    marginBottom: 25,
  },
  btnBase: {
    border: "none",
    padding: "14px 24px",
    borderRadius: 12,
    cursor: "pointer",
    fontSize: 15,
    fontWeight: "bold",
    transition: "transform 0.2s",
    color: "white",
  },
  get btnPrimary() {
    return { ...this.btnBase, background: "#2563eb" };
  },
  get btnSuccess() {
    return { ...this.btnBase, background: "#16a34a" };
  },
  get btnLibras() {
    return { ...this.btnBase, background: "#7c3aed" };
  },
  get btnRecording() {
    return { ...this.btnBase, background: "#dc2626" };
  },
  downloadBtn: {
    textDecoration: "none",
    background: "#16a34a",
    color: "white",
    padding: "14px 24px",
    borderRadius: 12,
    fontWeight: "bold",
    fontSize: 15,
    display: "inline-flex",
    alignItems: "center",
  },
  statusContainer: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    background: "#0b1220",
    padding: 16,
    borderRadius: 12,
    marginBottom: 25,
  },
  statusText: {
    color: "#cbd5e1",
    fontSize: 15,
  },
  recordBadge: {
    background: "#dc2626",
    color: "white",
    padding: "4px 12px",
    borderRadius: 20,
    fontSize: 12,
    fontWeight: "bold",
    animation: "pulse-recording 1s infinite",
  },
  workspaceGrid: {
    display: "grid",
    gridTemplateColumns: "1.5fr 1fr",
    gap: 20,
    marginTop: 20,
  },
  preview: {
    background: "#0b1220",
    borderRadius: 16,
    padding: 20,
    height: 540,
    display: "flex",
    flexDirection: "column",
  },
  previewTitle: {
    marginBottom: 15,
    flexShrink: 0,
  },
  previewList: {
    overflowY: "auto",
    flexGrow: 1,
    paddingRight: 10,
  },
  previewItem: {
    padding: 12,
    borderBottom: "1px solid #1e293b",
  },
  original: {
    color: "#94a3b8",
    marginBottom: 5,
    fontSize: 14,
  },
  optimized: {
    color: "#22c55e",
    fontWeight: "bold",
    fontSize: 14,
  },
  emptyMsg: {
    color: "#475569",
    fontSize: 14,
    textAlign: "center",
    marginTop: 40,
  },
  avatarContainer: {
    background: "#0b1220",
    borderRadius: 16,
    height: 540,
    border: "2px solid #1e293b",
    position: "relative",
    overflow: "hidden",
    transition: "border-color 0.3s, box-shadow 0.3s",
    // cria novo stacking context para tentar conter position:fixed do VLibras
    transform: "translateZ(0)",
    contain: "layout style",
  },
  avatarPlaceholder: {
    color: "#64748b",
    textAlign: "center",
    position: "absolute",
    top: "50%",
    left: "50%",
    transform: "translate(-50%, -50%)",
    width: "80%",
    fontSize: 14,
    pointerEvents: "none",
    zIndex: 1,
  },
  vwRoot: {
    position: "absolute",
    inset: 0,
    width: "100%",
    height: "100%",
  },
  vwWrapper: {
    position: "absolute",
    inset: 0,
    width: "100%",
    height: "100%",
    boxShadow: "none",
    background: "transparent",
  },
  vwTopWrapper: {
    position: "absolute",
    inset: 0,
    width: "100%",
    height: "100%",
  },
};
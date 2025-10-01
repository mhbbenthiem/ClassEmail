"use strict";

/* ========================== CONFIG & HELPERS ========================== */
const API = "/api";
const $   = (s) => document.querySelector(s);
const on  = (id, evt, fn) => { const el = document.getElementById(id); if (el) el.addEventListener(evt, fn); };
const now = () => new Date().toLocaleString("pt-BR", { hour12: false });

async function safeJson(r){
  try { return await r.json(); }
  catch { return { detail: (await r.text()).slice(0, 300) }; }
}

function humanSize(bytes){
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes/1024; if (kb < 1024) return `${Math.round(kb)} KB`;
  const mb = kb/1024; return `${mb.toFixed(1)} MB`;
}
function shortenName(name, max=42){
  if (name.length <= max) return name;
  const dot = name.lastIndexOf("."); const ext = dot > -1 ? name.slice(dot) : "";
  const base = name.slice(0, max - ext.length - 3);
  return base + "…" + ext;
}

/* ========================== DOM REFS & STATE ========================== */
const els = {
  fileEl:    document.getElementById("fileInput"),
  fileBadge: document.getElementById("fileBadge"),
  fileName:  document.getElementById("selectedFileName"),
  fileMeta:  document.getElementById("selectedFileMeta"),
  btnRemove: document.getElementById("btnRemoveFile"),
  btnAnalyze:document.getElementById("btnAnalyze"),
  btnRestart:document.getElementById("btnRestart"),
  emailText: document.getElementById("emailText"),
  statusRow: document.getElementById("statusRow") || document.body,
  btnCopy:   document.getElementById("btnCopy"),
};
let currentFile = null;

/* ========================== FILE BADGE ========================== */
function showFileBadge(file){
  if (!els.fileBadge) return;
  els.fileName.textContent = shortenName(file.name);
  els.fileMeta.textContent = `• ${humanSize(file.size)}`;
  els.fileBadge.style.display = "inline-flex";
}
function hideFileBadge(){
  if (!els.fileBadge) return;
  els.fileBadge.style.display = "none";
  els.fileName.textContent = "";
  els.fileMeta.textContent = "";
}
function clearFileSelection(){
  if (els.fileEl) els.fileEl.value = "";
  currentFile = null;
  hideFileBadge();
}

/* quando o usuário escolhe um arquivo */
els.fileEl?.addEventListener("change", (e) => {
  const f = e.target.files?.[0];
  if (f && f.size > 0){
    const okExt = /\.(txt|pdf)$/i;
    const okTypes = ["text/plain","application/pdf"];
    if (!(okExt.test(f.name) || okTypes.includes(f.type))){
      els.statusRow.innerHTML = '<span class="muted">Formato não suportado: use .txt ou .pdf.</span>';
      clearFileSelection();
      return;
    }
    currentFile = f;
    showFileBadge(f);
    els.statusRow.innerHTML = `<span class="muted">Arquivo selecionado: ${f.name}</span>`;
  } else {
    clearFileSelection();
  }
});

/* botão “remover” no badge */
els.btnRemove?.addEventListener("click", () => {
  clearFileSelection();
  els.statusRow.innerHTML = '<span class="muted">Arquivo removido. Você pode colar um texto ou escolher outro arquivo.</span>';
});

/* ========================== API KPIs ========================== */
async function refreshApiKPIs(){
  try{
    let r = await fetch(`${API}/stats`);
    if (r.ok){
      const j = await r.json();
      $("#sessTotal")?.textContent = j.total_classifications ?? 0;
      $("#apiAvg")?.textContent = `${((+j.average_confidence||0)*100).toFixed(1)}%`;
      $("#sessProd")?.textContent = j.productive_count ?? 0;
      $("#sessImprod")?.textContent = j.unproductive_count ?? 0;
      return;
    }
    r = await fetch(`${API}/health`);
    if (r.ok) $("#apiAvg") && ($("#apiAvg").textContent = "OK");
  }catch(e){ console.warn("refreshApiKPIs:", e); }
}

/* ========================== HISTÓRICO & KPIs SESSÃO ========================== */
const KEY = "ac_history_v3";
function loadHist(){ try{ return JSON.parse(localStorage.getItem(KEY) || "[]"); }catch{ return []; } }
function saveHist(list){ localStorage.setItem(KEY, JSON.stringify(list.slice(-200))); }
function addEntry(j){ const list = loadHist(); list.push(j); saveHist(list); renderHistory(); renderSessionKPIs(); }

function snip(t){ return t && t.length>160 ? t.slice(0,160) + "…" : (t||""); }
function renderHistory(){
  const list = loadHist().slice().reverse();
  const el = $("#history"); if (!el) return;
  el.innerHTML = "";
  if (!list.length){ el.innerHTML = '<div class="muted">Nada por aqui ainda.</div>'; return; }
  list.forEach(it => {
    const div = document.createElement("div");
    div.className = "item";
    div.innerHTML = `
      <div class="toprow">
        <div class="left">
          <span class="badge ${it.category === "Produtivo" ? "ok" : "neutral"}">${it.category}</span>
          <span class="mono">${(it.confidence*100).toFixed(1)}%</span>
        </div>
        <div class="ts">${it.ts || ""}</div>
      </div>
      <div class="snip" style="margin-top:6px">${snip(it.original_text)}</div>
    `;
    el.appendChild(div);
  });
}
function renderSessionKPIs(){
  const list = loadHist();
  const total = list.length;
  const prod = list.filter(x => x.category === "Produtivo").length;
  const impr = total - prod;
  $("#sessTotal") && ($("#sessTotal").textContent = total);
  $("#sessProd")  && ($("#sessProd").textContent  = prod);
  $("#sessImprod")&& ($("#sessImprod").textContent= impr);
  const pct = total ? Math.round((prod/total)*100) : 0;
  $("#sessBar") && ($("#sessBar").style.width = pct + "%");
}
function resetSession(){
  localStorage.removeItem(KEY);
  clearFileSelection();
  renderHistory();
  renderSessionKPIs();
  clearResult();
  els.statusRow.innerHTML = '<span class="muted">Sessão reiniciada.</span>';
}

/* ========================== RENDER RESULTADO ========================== */
function clearResult(){
  $("#statusRow") && ($("#statusRow").innerHTML = '<span class="muted">Aguardando…</span>');
  $("#catRow")  && ($("#catRow").style.display  = "none");
  $("#confRow") && ($("#confRow").style.display = "none");
  $("#respRow") && ($("#respRow").style.display = "none");
  $("#origRow") && ($("#origRow").style.display = "none");
}
function showResult(j){
  $("#statusRow") && ($("#statusRow").innerHTML = '<span class="muted">Concluído</span>');
  $("#catRow")  && ($("#catRow").style.display  = "");
  $("#confRow") && ($("#confRow").style.display = "");
  $("#respRow") && ($("#respRow").style.display = "");
  $("#origRow") && ($("#origRow").style.display = "");
  $("#resp")   && ($("#resp").textContent = j.suggested_response || "");
  $("#badge")  && ($("#badge").textContent = j.category);
  $("#badge")  && ($("#badge").classList.remove("ok","neutral"));
  $("#badge")  && ($("#badge").classList.add(j.category === "Produtivo" ? "ok" : "neutral"));
  $("#conf")   && ($("#conf").textContent = (j.confidence*100).toFixed(1) + "%");
  $("#orig")   && ($("#orig").textContent = j.original_text || "");
}
function toast(msg){
  const t = document.getElementById("toast"); if (!t) return;
  t.textContent = msg; t.classList.add("show");
  setTimeout(()=>t.classList.remove("show"), 2200);
}
function copyResp(){
  const el = $("#resp"); if (!el) return;
  const sel = window.getSelection(); const r = document.createRange();
  r.selectNodeContents(el); sel.removeAllRanges(); sel.addRange(r);
  document.execCommand("copy"); sel.removeAllRanges();
  $("#statusRow") && ($("#statusRow").innerHTML = '<span class="muted">Resposta copiada ✓</span>');
}

/* ========================== ANALYZE UNIFICADO (com fallback) ========================== */
function setLoading(is){
  if (!els.btnAnalyze) return;
  els.btnAnalyze.disabled = is;
  els.btnAnalyze.classList.toggle("is-loading", is);
  els.btnAnalyze.innerHTML = is ? '<i class="fas fa-spinner fa-spin"></i> Analisando…'
                                : '<i class="fas fa-search"></i> Analisar';
}

async function analyze(e){
  if (e) e.preventDefault();

  const text = (els.emailText?.value || "").trim();
  const file = currentFile;
  const hasFile = !!(file && file instanceof File && file.size > 0);

  if (!hasFile && !text){
    els.statusRow.innerHTML = '<span class="muted">Cole um texto ou selecione um arquivo.</span>';
    return;
  }

  els.statusRow.innerHTML = hasFile
    ? `<span class="muted">Processando arquivo: ${file.name}…</span>`
    : '<span class="muted">Processando texto…</span>';

  setLoading(true);
  try{
    let resp, data;

    // Tenta /analyze
    if (hasFile){
      const fd = new FormData();
      fd.append("file", file, file.name); // CHAVE "file"
      // debug opcional:
      // for (const [k,v] of fd.entries()) console.log("FormData:", k, v?.name || v);
      resp = await fetch(`${API}/analyze`, { method:"POST", body: fd });
    } else {
      resp = await fetch(`${API}/analyze`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ text })
      });
    }

    // Fallback se /analyze não existir
    if (resp.status === 404){
      if (hasFile){
        const fd = new FormData(); fd.append("file", file, file.name);
        resp = await fetch(`${API}/classify-file`, { method:"POST", body: fd });
      } else {
        resp = await fetch(`${API}/classify-text`, {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body: JSON.stringify({ text })
        });
      }
    }

    data = await safeJson(resp);
    if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);

    // sucesso
    showResult(data);
    addEntry({ ...data, ts: now(), filename: hasFile ? file.name : undefined });
    await refreshApiKPIs();

    if (hasFile){
      clearFileSelection();
      els.statusRow.innerHTML = '<span class="muted">Concluído. Arquivo removido da seleção.</span>';
    } else {
      els.statusRow.innerHTML = '<span class="muted">Concluído.</span>';
    }

  }catch(err){
    console.warn("analyze error:", err);
    els.statusRow.innerHTML = `<span class="muted">Erro: ${(err && err.message) || "Falha ao processar"}</span>`;
  }finally{
    setLoading(false);
  }
}

/* ========================== WIRES ========================== */
on("btnAnalyze","click", analyze);
on("btnRestart","click", () => { if (confirm("Limpar histórico desta sessão?")) resetSession(); });
on("btnCopy",  "click",  copyResp);
document.addEventListener("keydown", (e)=>{
  if((e.ctrlKey||e.metaKey) && e.key==="Enter") analyze();
  if(e.key==="Escape") { clearFileSelection(); }
});

/* ========================== BOOT ========================== */
renderHistory();
renderSessionKPIs();
refreshApiKPIs();
clearResult();

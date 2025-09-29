const API = "/api";

async function safeJson(r){
  try { return await r.json(); }
  catch { return { detail: (await r.text()).slice(0, 300) }; }
}

async function refreshApiKPIs(){
  try{
    // tenta /stats
    let r = await fetch(`${API}/stats`);
    if (r.ok) {
      const j = await r.json();
      const elTotal = document.querySelector("#sessTotal");
      const elConf  = document.querySelector("#apiAvg");
      const elProd  = document.querySelector("#sessProd");
      const elImpr  = document.querySelector("#sessImprod");
      if (elTotal) elTotal.textContent = j.total_classifications ?? 0;
      if (elConf)  elConf.textContent  = (+(j.average_confidence||0)*100).toFixed(1)+"%";
      if (elProd)  elProd.textContent  = j.productive_count ?? 0;
      if (elImpr)  elImpr.textContent  = j.unproductive_count ?? 0;
      return;
    }

    // fallback: /health (só indica 'ok')
    r = await fetch(`${API}/health`);
    if (r.ok) {
      const elConf = document.querySelector("#apiAvg");
      if (elConf) elConf.textContent = "OK";
    }
  }catch(e){
    console.warn("refreshApiKPIs:", e);
  }
}


function clearFileSelection(){
  const fileInput = document.getElementById("fileInput");
  const fileBadge = document.getElementById("fileBadge");
  if (fileInput) fileInput.value = "";
  if (fileBadge) fileBadge.style.display = "none";
}

async function analyze(e){
  if (e) e.preventDefault();
  const txtEl  = document.getElementById("emailText");
  const fileEl = document.getElementById("fileInput");
  const text   = (txtEl?.value || "").trim();
  const file   = fileEl?.files?.[0];

  // 1) tenta /analyze (rota “tudo em um”)
  try{
    let resp;
    if (file){
      const fd = new FormData(); fd.append("file", file);
      resp = await fetch(`${API}/analyze`, { method:"POST", body: fd });
    } else {
      if (!text) { alert("Cole um texto ou selecione um arquivo."); return; }
      resp = await fetch(`${API}/analyze`, {
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body: JSON.stringify({ text })
      });
    }
    if (resp.status !== 404) { // se NÃO for 404, processa normalmente
      const data = await safeJson(resp);
      if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
      // TODO: renderizar resultado
      refreshApiKPIs();
      return;
    }
  }catch(e){
    // se caiu aqui e não foi 404, segue o fluxo (vamos tentar fallback)
    if (e?.message && !/HTTP 404|Not Found/i.test(e.message)) throw e;
  }

  // 2) Fallback: usa as rotas que EXISTEM no seu backend
  let endpoint, options;
  if (file){
    const fd = new FormData(); fd.append("file", file);
    endpoint = `${API}/classify-file`;
    options  = { method:"POST", body: fd };
  } else {
    endpoint = `${API}/classify-text`;
    options  = {
      method:"POST",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify({ text })
    };
  }
  const r2 = await fetch(endpoint, options);
  const d2 = await safeJson(r2);
  if (!r2.ok) throw new Error(d2.detail || `HTTP ${r2.status}`);

  // TODO: renderizar resultado com d2
  refreshApiKPIs();
}


  const $ = s => document.querySelector(s);
  const els = {
    fileInput: $("#fileInput"),
    fileBadge: $("#fileBadge"),
    fileName:  $("#selectedFileName"),
    fileMeta:  $("#selectedFileMeta"),
    btnRemove: $("#btnRemoveFile"),
    btnAnalyze: $("#btnAnalyze"),
    statusRow: $("#statusRow"), // opcional: se tiver uma área de status
  };

  // helpers
  function humanSize(bytes){
    if (bytes < 1024) return `${bytes} B`;
    const kb = bytes/1024; if (kb < 1024) return `${Math.round(kb)} KB`;
    const mb = kb/1024; return `${mb.toFixed(1)} MB`;
  }
  function shortenName(name, max=42){
    if (name.length <= max) return name;
    const dot = name.lastIndexOf(".");
    const ext = dot > -1 ? name.slice(dot) : "";
    const base = name.slice(0, max - ext.length - 3);
    return base + "…" + ext;
  }
  function showFileBadge(file){
    els.fileName.textContent = shortenName(file.name);
    els.fileMeta.textContent = `• ${humanSize(file.size)}`;
    els.fileBadge.style.display = "inline-flex";
  }
  function hideFileBadge(){
    els.fileBadge.style.display = "none";
    els.fileName.textContent = "";
    els.fileMeta.textContent = "";
  }

  // on change → mostra badge
  els.fileInput.addEventListener("change", () => {
    const f = els.fileInput.files && els.fileInput.files[0];
    if (!f){ hideFileBadge(); return; }

    // valida extensão/tipo básico
    const okExt = /\.(txt|pdf)$/i;
    const okTypes = ["text/plain","application/pdf"];
    if (!(okExt.test(f.name) || okTypes.includes(f.type))) {
      if (els.statusRow) els.statusRow.innerHTML = '<span class="muted">Formato não suportado: use .txt ou .pdf.</span>';
      els.fileInput.value = "";
      hideFileBadge();
      return;
    }

    showFileBadge(f);
    if (els.statusRow) els.statusRow.innerHTML = '<span class="muted">Arquivo selecionado. Clique em “Analisar”.</span>';
  });

// botão “Remover” → limpa input e esconde badge
els.btnRemove.addEventListener("click", () => {
  els.fileInput.value = "";
  hideFileBadge();
  if (els.statusRow) els.statusRow.innerHTML = '<span class="muted">Arquivo removido. Você pode colar um texto ou escolher outro arquivo.</span>';
});


    // Session history
    const KEY = "ac_history_v3"; 
    function loadHist(){ try{ return JSON.parse(localStorage.getItem(KEY) || "[]"); }catch(e){ return []; } }
    function saveHist(list){ localStorage.setItem(KEY, JSON.stringify(list.slice(-200))); }
    function addEntry(j){ const list = loadHist(); list.push(j); saveHist(list); renderHistory(); renderSessionKPIs(); }
    function resetSession(){
      localStorage.removeItem(KEY);            // limpa histórico da sessão
      try { fileInput.value = ""; } catch(e){} // limpa input de arquivo (se existir)
      if (typeof hideFileBadge === "function") hideFileBadge(); // esconde o “arquivo selecionado”
      renderHistory();
      renderSessionKPIs();
      clearResult();
      document.getElementById("statusRow").innerHTML =
        '<span class="muted">Sessão reiniciada.</span>';
    }
    function setLoading(is){ 
      const btn = document.getElementById("btnAnalyze");
      btn.disabled = is; btn.textContent = is ? "Analisando…" : "Analisar";
      btn.classList.toggle("is-loading", is);
    }
    async function analyze(){ 
      // ...
      setLoading(true);
      try { /* fetch */ } finally { setLoading(false); }
    }


    function snip(t){ return t && t.length>160 ? t.slice(0,160) + "…" : (t||""); }
    function renderHistory(){
      const list = loadHist().slice().reverse();
      const el = $("#history"); el.innerHTML = "";
      if(!list.length){ el.innerHTML = '<div class="muted">Nada por aqui ainda.</div>'; return; }
      list.forEach(it => {
        const div = document.createElement("div");
        div.className = "item";
        div.innerHTML = `
          <div class="toprow">
            <div class="left">
              <span class="badge ${it.category === "Produtivo" ? "ok":"neutral"}">${it.category}</span>
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
      const impr = list.filter(x => x.category !== "Produtivo").length;
      $("#sessTotal").textContent = total;
      $("#sessProd").textContent = prod;
      $("#sessImprod").textContent = impr;
      const pct = total ? Math.round((prod/total)*100) : 0;
      $("#sessBar").style.width = pct + "%";
    }
    function exportCSV(){
      const list = loadHist();
      const rows = [["ts","categoria","confiança","arquivo","texto","sugerida"]]
        .concat(list.map(x=>[x.ts,x.category,x.confidence,x.filename||"",x.original_text||"",x.suggested_response||""]));
      const csv = rows.map(r=>r.map(v=>`"${String(v).replace(/"/g,'""')}"`).join(",")).join("\n");
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([csv],{type:"text/csv"})); a.download = "historico.csv"; a.click();
    }


    function clearResult(){
      $("#statusRow").innerHTML = '<span class="muted">Aguardando…</span>';
      $("#catRow").style.display = "none";
      $("#confRow").style.display = "none";
      $("#origRow").style.display = "none";
    }
    function showResult(j){
      $("#statusRow").innerHTML = '<span class="muted">Concluído</span>';
      $("#catRow").style.display = ""; $("#confRow").style.display = ""; $("#respRow").style.display = ""; $("#origRow").style.display = "";
      $("#resp").textContent = j.suggested_response || "";
      $("#badge").textContent = j.category;
      $("#badge").className = "badge " + (j.category === "Produtivo" ? "ok" : "neutral");
      $("#conf").textContent = (j.confidence*100).toFixed(1) + "%";
      $("#orig").textContent = j.original_text;
    }
    function toast(msg){ const t = document.getElementById("toast"); t.textContent=msg; t.classList.add("show");
      setTimeout(()=>t.classList.remove("show"), 2200); }
    document.addEventListener("keydown", (e)=>{
      if((e.ctrlKey||e.metaKey) && e.key==="Enter") analyze();
      if(e.key==="Escape") { fileInput.value=""; hideFileBadge(); }
    });

    function copyResp(){
    const sel = window.getSelection(); const r = document.createRange();
    r.selectNodeContents($("#resp")); sel.removeAllRanges(); sel.addRange(r);
    document.execCommand("copy"); sel.removeAllRanges();
    $("#statusRow").innerHTML = '<span class="muted">Resposta copiada ✓</span>';
  }
  document.getElementById("btnCopy").addEventListener("click", copyResp);
    function showError(){ $("#statusRow").innerHTML = '<span class="muted">Erro ao processar. Tente novamente.</span>'; }

    async function classifyText(){
      const text = $("#emailText").value.trim(); if(!text) return;
      $("#statusRow").innerHTML = '<span class="muted">Processando…</span>';
      try{
        const r = await fetch(API + "/classify-text", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({text})});
        const j = await r.json(); if(!r.ok) throw new Error(j.detail || "Falha");
        showResult(j); addEntry({...j, ts: now()}); refreshApiKPIs();
      }catch(e){ showError(); }
    }
    async function classifyFile(){
      const f = $("#fileInput").files[0]; if(!f) return;
      $("#statusRow").innerHTML = '<span class="muted">Enviando…</span>';
      try{
        const fd = new FormData(); fd.append("file", f);
        const r = await fetch(API + "/classify-file", {method:"POST", body:fd});
        const j = await r.json(); if(!r.ok) throw new Error(j.detail || "Falha");
        showResult(j); addEntry({...j, ts: now(), filename: f.name}); refreshApiKPIs();
      }catch(e){ showError(); }
    }
  document.getElementById("btnAnalyze").addEventListener("click", analyze)
  async function analyze(){
      const f = fileInput.files[0];
      const text = $("#emailText").value.trim();

      if(!f && !text){
        statusRow.innerHTML = '<span class="muted">Cole um texto ou selecione um arquivo.</span>';
        return;
      }

      statusRow.innerHTML = f
        ? `<span class="muted">Processando arquivo: ${f.name}…</span>`
        : '<span class="muted">Processando texto…</span>';

      try{
        let r, j;

        if (f) {
          const fd = new FormData();
          fd.append("file", f);
          r = await fetch(API + "/analyze", { method:"POST", body: fd });
        } else {
          r = await fetch(API + "/analyze", {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({ text })
          });
        }

        j = await r.json();
        if(!r.ok) throw new Error(j.detail || "Falha");

        // resultado + histórico
        showResult(j);
        addEntry({ ...j, ts: now(), filename: f ? f.name : undefined });
        refreshApiKPIs();

        // 👇 NOVO: limpar o arquivo da UI após análise bem-sucedida
        if (f) {
          fileInput.value = "";    // limpa o input
          hideFileBadge();         // esconde o badge com o nome do arquivo
          statusRow.innerHTML = '<span class="muted">Concluído. Arquivo removido da seleção.</span>';
        } else {
          statusRow.innerHTML = '<span class="muted">Concluído.</span>';
        }

      }catch(e){
        // mantém o arquivo caso queira reenviar após erro
        statusRow.innerHTML = '<span class="muted">Erro ao processar. Tente novamente.</span>';
        console.warn(e);
      }
    }

  renderHistory(); renderSessionKPIs(); refreshApiKPIs();

  // helper seguro: só adiciona evento se o elemento existir
  function on(id, evt, fn){
    const el = document.getElementById(id);
    if (el) el.addEventListener(evt, fn);
  }
  on("btnAnalyze", "click", analyze);
  on("btnRestart","click", () => {
    if (confirm("Limpar histórico desta sessão?")) resetSession();
  });
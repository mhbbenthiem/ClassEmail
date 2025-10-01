# trechos essenciais do backend/app.py
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import inspect, logging

from .email_classifier import EmailClassifier
from .utils import preprocess_text, extract_text_from_file

logger = logging.getLogger(__name__)
app = FastAPI(title="Email Classifier API", version="1.0.0")

try:
    WEB_DIR = (Path(__file__).resolve().parent.parent / "web")
    if WEB_DIR.exists():
        app.mount("/ui", StaticFiles(directory=str(WEB_DIR), html=True), name="ui")
except Exception:
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

classifier = EmailClassifier()

@app.on_event("startup")
async def startup_event():
    try:
        await classifier.initialize()
        logger.info("Models ready")
    except Exception as e:
        logger.exception(f"Startup failed: {e}")

@app.get("/health")
async def health():
    return {"status":"healthy","models_loaded":getattr(classifier,"is_initialized",False)}

class ClassificationRequest(BaseModel):
    text: str

async def _run_classifier(processed: str, original: str):
    method = getattr(classifier, "classify_email", None) or getattr(classifier, "classify", None)
    if method is None:
        raise HTTPException(status_code=500, detail="Classifier missing method.")
    out = method(processed_text=processed, original_text=original)
    if inspect.isawaitable(out): return await out
    return out

@app.post("/classify-text")
async def classify_text(req: ClassificationRequest):
    processed = preprocess_text(req.text)
    return await _run_classifier(processed, req.text)

@app.post("/classify-file")
async def classify_file(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > 4*1024*1024:
        raise HTTPException(status_code=413, detail="Arquivo muito grande (máx 4 MB)")
    text = extract_text_from_file(content, file.filename)  # aceita .txt e .pdf com texto
    processed = preprocess_text(text)
    return await _run_classifier(processed, text)

@app.post("/analyze")
async def analyze(request: Request):
    ct = (request.headers.get("content-type") or "").lower()
    try:
        # --- multipart: arquivo OU texto no form ---
        if "multipart/form-data" in ct:
            form = await request.form()

            # debug: ver o que realmente chegou
            try:
                logger.info(f"/analyze multipart keys: {list(form.keys())}")
            except Exception:
                pass

            up = form.get("file")

            if isinstance(up, UploadFile) and getattr(up, "filename", ""):
                content = await up.read()
                if len(content) > 4 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="Arquivo muito grande (máx 4 MB).")
                text = extract_text_from_file(content, up.filename)

            # se não houver 'file', mas vier 'text' no form, processa texto
            elif "text" in form and str(form["text"]).strip():
                text = str(form["text"]).strip()

            else:
                raise HTTPException(status_code=400, detail="Envie 'file' (multipart) ou 'text'.")

        # --- JSON com {"text": "..."} ---
        elif "application/json" in ct or "text/json" in ct:
            data = await request.json()
            text = (data or {}).get("text", "")
            if not str(text).strip():
                raise HTTPException(status_code=400, detail="Campo 'text' ausente.")

        # --- texto puro (raro, mas útil p/ testes) ---
        elif "text/plain" in ct:
            raw = await request.body()
            text = raw.decode("utf-8", errors="ignore").strip()
            if not text:
                raise HTTPException(status_code=400, detail="Corpo de texto vazio.")

        # --- fallback: tenta JSON mesmo sem header certo ---
        else:
            try:
                data = await request.json()
                text = (data or {}).get("text", "")
                if not str(text).strip():
                    raise HTTPException(status_code=400, detail="Envie JSON {'text': ...} ou multipart com 'file'.")
            except Exception:
                raise HTTPException(status_code=400, detail="Envie JSON {'text': ...} ou multipart com 'file'.")

        # pré-processa + classifica
        processed = preprocess_text(text)
        result = await _run_classifier(processed, text)
        return result

    except ValueError as e:
        # Ex.: PDF sem texto extraível
        raise HTTPException(status_code=400, detail=str(e))
    
@app.get("/stats")
async def stats():
    return {
        "total_classifications": getattr(classifier, "total_classifications", 0),
        "productive_count": getattr(classifier, "productive_count", 0),
        "unproductive_count": getattr(classifier, "unproductive_count", 0),
        "average_confidence": (
            sum(getattr(classifier, "confidence_scores", []) or [0]) /
            max(1, len(getattr(classifier, "confidence_scores", [])))
        ),
    }

_internal_app = app  # guarda o app atual

from fastapi import FastAPI as _FastAPI
app = _FastAPI(title="Email Classifier (mounted)")
app.mount("/api", _internal_app)
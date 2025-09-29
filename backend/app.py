from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
import os
from .email_classifier import EmailClassifier
from .utils import preprocess_text, extract_text_from_file
import logging
import inspect
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Email Classifier API",
    description="API para classificação automática de emails corporativos",
    version="1.0.0"
)

WEB_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "web"))
# 🔧 Em serverless (Vercel) os arquivos estáticos de /web são servidos pela Vercel,
# então só monte /ui se a pasta existir no filesystem desta função.
try:
    WEB_DIR = (Path(__file__).resolve().parent.parent / "web")
    if WEB_DIR.exists():
        app.mount("/ui", StaticFiles(directory=str(WEB_DIR), html=True), name="ui")
        logger.info(f"Mounted /ui from {WEB_DIR}")
    else:
        logger.info("Static UI not mounted (web/ not present in function bundle).")
except Exception as e:
    logger.info(f"Skipping static mount: {e}")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize classifier
classifier = EmailClassifier()

class ClassificationRequest(BaseModel):
    text: str

class ClassificationResponse(BaseModel):
    category: str
    confidence: float
    original_text: str
    suggested_response: str

@app.on_event("startup")
async def startup_event():
    """Initialize AI models on startup"""
    logger.info("Initializing AI models...")
    await classifier.initialize()
    logger.info("AI models loaded successfully!")

@app.get("/")
async def root():
    return {
        "message": "Email Classifier API - Orçamento Zero",
        "status": "online",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "models_loaded": classifier.is_initialized}

async def _run_classifier(text_processed: str, text_original: str):
    method = getattr(classifier, "classify_email", None) or getattr(classifier, "classify", None)
    if method is None:
        raise HTTPException(status_code=500, detail="Classifier missing 'classify_email' or 'classify' method.")
    # chama primeiro...
    maybe_coro = method(processed_text=text_processed, original_text=text_original)
    # ...e se for coroutine/awaitable, aguarda
    if inspect.isawaitable(maybe_coro):
        return await maybe_coro
    return maybe_coro


@app.post("/analyze")
async def analyze(request: Request):
    ct = request.headers.get("content-type", "") or ""
    try:
        if ct.startswith("multipart/form-data"):
            form = await request.form()
            up = form.get("file")
            if not isinstance(up, UploadFile):
                raise HTTPException(status_code=400, detail="Campo 'file' ausente.")
            content = await up.read()
            text = extract_text_from_file(content, up.filename)
        else:
            data = await request.json()
            text = (data or {}).get("text", "")
            if not text.strip():
                raise HTTPException(status_code=400, detail="Campo 'text' ausente.")

        processed = preprocess_text(text)
        result = await _run_classifier(processed, text)  # seu helper já trata sync/async
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))  # PDF sem texto etc.
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao processar: {e}")
    
@app.post("/classify-text", response_model=ClassificationResponse)
async def classify_text(req: ClassificationRequest):
    text = req.text
    processed = preprocess_text(text)
    result = await _run_classifier(processed, text)
    return ClassificationResponse(**result)

@app.post("/classify-file", response_model=ClassificationResponse)
async def classify_file(file: UploadFile = File(...)):
    content = await file.read()
    try:
        text = extract_text_from_file(content, file.filename)  # .txt ou .pdf (texto selecionável)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao ler arquivo: {e}")

    processed = preprocess_text(text)
    result = await _run_classifier(processed, text)
    return ClassificationResponse(**result)

@app.get("/stats")
async def get_classifier_stats():
    """Retorna estatísticas do classificador"""
    return {
        "total_classifications": classifier.total_classifications,
        "productive_count": classifier.productive_count,
        "unproductive_count": classifier.unproductive_count,
        "average_confidence": classifier.get_average_confidence(),
        "models_loaded": classifier.is_initialized
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
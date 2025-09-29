# api/index.py  (HELLO API DE TESTE)
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

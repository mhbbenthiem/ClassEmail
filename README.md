# ClassEmail
EXECUÇÂO LOCAL:
-> Pré requisitos
    - Python 3.10+ (recomendado 3.11).
    - Pip atualizado (python -m pip install -U pip).
    - Ambiente virtual (opcional, recomendado).
-> Instalar dependências
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # macOS/Linux
    source .venv/bin/activate

    pip install -r requirements.txt

-> Subir a API
    # a partir da raiz do repo
    uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload

-> Abrir o frontend
    - abrir no navegador: web/index.html

EXEMPLOS PARA TESTE:
-> Improdutivo (esperado):

    “Olá, equipe! Passando só para desejar um ótimo final de ano e agradecer pelo trabalho de vocês. Abraços!”

    “Parabéns pelo excelente trabalho no último trimestre!”

    “Obrigado! Era só isso mesmo, bom dia!”

-> Produtivo (esperado):

    “Poderiam informar o status do chamado #48291? O acesso continua com erro.”

    “Segue anexo com a fatura. Preciso da aprovação até sexta.”

    “Conseguem redefinir meu login? Recebo falha de autenticação desde ontem.”


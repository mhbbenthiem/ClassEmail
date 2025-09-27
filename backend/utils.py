import re
from typing import Dict
import logging
import nltk
from nltk.corpus import stopwords
from nltk.stem import RSLPStemmer
from nltk.tokenize import word_tokenize
from PyPDF2 import PdfReader
import io

logger = logging.getLogger(__name__)

INTENT_PATTERNS = [
    ("status", r"\b(status|andamento|situa[cç][aã]o|progresso)\b"),
    ("login", r"\b(login|acesso|403|senha|bloqueio)\b"),
    ("fatura", r"\b(fatura|nf|nota fiscal|boleto|pagamento|cobran[çc]a|vencida|vencimento)\b"),
    ("anexo", r"\b(anexo|segue(m)? em anexo|arquivo(s)?|documento)\b"),
    ("prazo", r"\b(prazo|deadline|entrega|quando|data prevista|previs[aã]o)\b"),
    ("api", r"\b(api|endpoint|payload|integra[cç][aã]o)\b"),
    ("contrato", r"\b(contrato|assinatura(s)?|pendente|validar)\b"),
    ("reabrir_ticket", r"\b(reabrir|reabertura|voltou a ocorrer|persist(e|iu))\b"),
    ("cadastro", r"\b(cadastro|atualiza[cç][aã]o cadastral)\b"),
    ("auditoria", r"\b(auditoria|acesso tempor[aá]rio|perfil leitura)\b"),
    ("divergencia", r"\b(diverg[eê]ncia|inconsist[eê]ncia|dashboard|relat[oó]rio)\b"),
    ("pagamento", r"\b(previs[aã]o de pagamento|pagamento|financeiro)\b"),
]

GREETINGS_PATTERNS = [
    r"\bboas festas\b",
    r"\bfeliz natal\b",
    r"\bfeliz ano novo\b",
    r"\bparab(e|é)ns\b",
    r"\bmuito obrigad[oa]\b",
    r"\bobrigad[oa]\b",
    r"\bagrade(ço|cemos)\b",
    r"\babraços?\b",
]
ACTION_TRIGGERS = [
    r"\bstatus\b", r"\berro\b", r"\bacesso\b", r"\blogin\b", r"\bprazo\b",
    r"\bchamado\b", r"\bticket\b", r"\bsolicita(c|ç)(a|ã)o\b", r"\bverifica(r|ção)\b",
    r"\bpoderia(m)?\b", r"\benviar\b", r"\banex(o|ei)\b", r"\bsegue(m)?\b",
    r"\bnf\b", r"\bnota fiscal\b", r"\bfatura\b", r"\bpendente\b",
    r"\batualiza(r|ç[aã]o)\b", r"\bd(ú|u)vida\b",
]
def is_greeting_no_action(text: str) -> bool:
    t = re.sub(r"\s+", " ", text.lower())
    if "?" in t:  # pergunta = tende a ação
        return False
    if any(re.search(p, t) for p in ACTION_TRIGGERS):
        return False
    return any(re.search(p, t) for p in GREETINGS_PATTERNS)

def detect_intent(text: str) -> str:
    t = re.sub(r"\s+", " ", text.lower())
    for name, pat in INTENT_PATTERNS:
        if re.search(pat, t):
            return name
    return "outro"

def suggest_response(category: str, text: str) -> str:
    """Gera resposta curta, objetiva e segura, sem inventar dados."""
    if category == "Improdutivo":
        if is_greeting_no_action(text):
            return ("Obrigado pela mensagem e pelas felicitações! "
                    "Agradecemos o contato e permanecemos à disposição.")
        return ("Obrigado pelo retorno! "
                "Se precisar de alguma ação específica, é só nos sinalizar.")
    # Produtivo → escolhe por intenção
    intent = detect_intent(text)
    if intent == "status":
        return ("Claro! Para conferir o status com precisão, poderia informar o número do chamado/solicitação "
                "e, se possível, o nome do solicitante e a data de abertura? Assim agilizamos o retorno.")
    if intent == "login":
        return ("Entendi o problema de acesso. Para avançarmos, envie por favor: usuário/e-mail, sistema/URL, "
                "data e horário aproximados do erro e, se houver, a mensagem exibida (print ajuda). Vamos verificar.")
    if intent == "fatura":
        return ("Recebido sobre a fatura. Para tratarmos, confirme o número/competência, valor e vencimento. "
                "Se houver comprovante ou boleto atualizado, anexe por gentileza.")
    if intent == "anexo":
        return ("Recebemos o(s) arquivo(s). Vamos validar e retornamos com os próximos passos. "
                "Se houver alguma ação específica esperada, nos informe.")
    if intent == "prazo":
        return ("Vamos verificar o cronograma e retornar a previsão. "
                "Se houver datas críticas, avise para priorizarmos.")
    if intent == "api":
        return ("Para a integração via API, compartilharemos endpoint, autenticação e exemplos de payload. "
                "Avise o caso de uso (consulta/envio) e, se necessário, um IP/caller para liberação.")
    if intent == "contrato":
        return ("Vamos checar as assinaturas pendentes do contrato e retornamos com a situação e o próximo passo.")
    if intent == "reabrir_ticket":
        return ("Vamos reabrir o ticket. Pode informar se houve alguma mudança antes da recorrência e anexar logs/prints?")
    if intent == "cadastro":
        return ("Para atualizar o cadastro, envie os campos a ajustar (endereço, responsáveis, contatos) "
                "e os documentos, se houver.")
    if intent == "auditoria":
        return ("Certo, podemos liberar acesso temporário (leitura) para auditoria. "
                "Informe o e-mail do usuário e o período desejado.")
    if intent == "divergencia":
        return ("Obrigado pelo alerta de divergência. Compartilhe um exemplo (período, filtro e valor esperado) "
                "para reproduzirmos e corrigirmos.")
    if intent == "pagamento":
        return ("Vamos consultar o financeiro sobre a previsão de pagamento e retornamos. "
                "Se puder, informe número da NF e data de vencimento.")
    # fallback produtivo
    return ("Recebido! Para avançarmos mais rápido, poderia detalhar contexto, objetivo e algum ID (chamado/NF/contrato)?")

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('rslp', quiet=True)
except:
    logger.warning("Could not download NLTK data. Using fallback preprocessing.")

# Initialize Portuguese stemmer
try:
    stemmer = RSLPStemmer()
    portuguese_stopwords = set(stopwords.words('portuguese'))
except:
    stemmer = None
    portuguese_stopwords = set()

def get_device_info() -> str:
    """Retorna info do dispositivo sem exigir PyTorch instalado."""
    try:
        import torch  # import opcional/lazy

        # CUDA (NVIDIA)
        if hasattr(torch, "cuda") and torch.cuda.is_available():
            try:
                name = torch.cuda.get_device_name(0)
            except Exception:
                name = "CUDA GPU"
            return f"CUDA GPU: {name}"

        # MPS (Apple Silicon)
        if (
            hasattr(torch, "backends")
            and hasattr(torch.backends, "mps")
            and torch.backends.mps.is_available()
        ):
            return "Apple Silicon MPS"

        # Torch presente mas sem aceleração
        return "CPU"
    except Exception:
        # Torch ausente ou qualquer erro → CPU
        return "CPU"


def preprocess_text(text: str) -> str:
    """
    Preprocess email text using NLP techniques:
    - Lowercase conversion
    - Remove punctuation and special characters
    - Tokenization
    - Remove stopwords
    - Stemming (when available)
    """
    try:
        # Basic cleaning
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)  # Remove punctuation
        text = re.sub(r'\d+', ' ', text)      # Remove numbers
        text = re.sub(r'\s+', ' ', text)      # Remove extra spaces
        text = text.strip()
        
        if not text:
            return ""
        
        # Tokenization
        try:
            tokens = word_tokenize(text, language='portuguese')
        except:
            # Fallback tokenization
            tokens = text.split()
        
        # Remove stopwords
        if portuguese_stopwords:
            tokens = [token for token in tokens if token not in portuguese_stopwords]
        
        # Stemming
        if stemmer:
            try:
                tokens = [stemmer.stem(token) for token in tokens]
            except:
                # If stemming fails, keep original tokens
                pass
        
        # Remove very short tokens
        tokens = [token for token in tokens if len(token) > 2]
        
        return ' '.join(tokens)
        
    except Exception as e:
        logger.error(f"Preprocessing error: {e}")
        # Fallback: basic cleaning only
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        text = re.sub(r'\s+', ' ', text).strip()
        return text

def calculate_keyword_score(text: str) -> Dict:
    """
    Calculate productivity score based on corporate keywords
    Returns category, confidence, and raw score
    """
    # Usar texto em minúsculas SEM stemming (ideal: passar o original lower() na chamada)
    t = text.lower()

    productive_keywords = [
        'solicitação', 'solicit', 'pedido', 'requisição', 'requer',
        'problema', 'erro', 'falha', 'bug', 'defeito', 'issue',
        'suporte', 'ajuda', 'help', 'auxílio', 'assistência',
        'dúvida', 'questão', 'pergunta', 'esclarecimento',
        'status', 'andamento', 'atualização', 'progresso', 'situação',
        'prazo', 'cronograma', 'deadline', 'entrega', 'conclusão',
        'sistema', 'aplicação', 'software', 'plataforma', 'versão',
        'instalação', 'configuração', 'integração', 'api', 'banco',
        'dados', 'relatório', 'dashboard', 'login', 'acesso',
        'documento', 'arquivo', 'anexo', 'contrato', 'proposta',
        'orçamento', 'fatura', 'pagamento', 'cobrança', 'processo',
        'aprovação', 'autorização', 'validação', 'conferência',
        'urgente', 'prioridade', 'crítico', 'importante', 'emergência',
        'imediato', 'asap', 'o quanto antes', 'brevemente'
    ]

    unproductive_keywords = [
        'obrigado', 'obrigada', 'thanks', 'agradecimento', 'gratidão',
        'parabéns', 'congratulações', 'felicitações', 'cumprimentos',
        'feliz natal', 'ano novo', 'happy new year', 'boas festas',
        'feriado', 'férias', 'vacation', 'aniversário', 'birthday',
        'casamento', 'formatura', 'aposentadoria', 'festa', 'evento',
        'cordialmente', 'atenciosamente', 'respeitosamente',
        'saudações', 'abraços', 'beijos', 'carinho', 'love',
        'tchau', 'bye', 'falou', 'até mais', 'see you', 'weekend',
        'fim de semana', 'coffee', 'café', 'almoço', 'lunch',
        'excellent', 'excelente', 'ótimo', 'perfeito', 'maravilhoso',
        'fantástico', 'incrível', 'amazing', 'wonderful'
    ]

    # Palavras que NÃO indicam ação (penalizam o score produtivo se aparecerem)
    non_action_words = [
        'obrigado', 'obrigada', 'agradeço', 'agradecemos',
        'parabéns', 'boas festas', 'feliz natal', 'feliz ano novo'
    ]

    productive_score = sum(1 for kw in productive_keywords if kw in t)
    unproductive_score = sum(1 for kw in unproductive_keywords if kw in t)

    # Penalização leve se houver termos claramente não-ação
    for w in non_action_words:
        if w in t and productive_score > 0:
            productive_score -= 1

    total_score = productive_score + unproductive_score

    if productive_score > unproductive_score:
        category = 'Produtivo'
        raw_score = productive_score
        confidence = min(0.6 + (productive_score * 0.08), 0.9)
    elif unproductive_score > productive_score:
        category = 'Improdutivo'
        raw_score = unproductive_score
        confidence = min(0.6 + (unproductive_score * 0.08), 0.9)
    else:
        # Empate/zero: se for saudação sem ação → Improdutivo; senão Produtivo
        if is_greeting_no_action(t):
            category = 'Improdutivo'
            raw_score = 0
            confidence = 0.8
        else:
            category = 'Produtivo'
            raw_score = 0
            confidence = 0.5

    return {
        'category': category,
        'confidence': confidence,
        'score': raw_score,
        'productive_matches': productive_score,
        'unproductive_matches': unproductive_score
    }


def validate_email_content(text: str) -> bool:
    """Validate if text looks like email content"""
    if not text or len(text.strip()) < 10:
        return False
    
    # Check for minimum meaningful content
    words = text.split()
    if len(words) < 3:
        return False
    
    return True

def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """Extrai texto de .txt e .pdf (fallback de encoding para .txt)."""
    fn = filename.lower()
    if fn.endswith('.pdf'):
        reader = PdfReader(io.BytesIO(file_content))
        pages = [(p.extract_text() or "") for p in reader.pages]
        text = "\n".join(pages).strip()
        if not text:
            raise ValueError("Não foi possível extrair texto do PDF (páginas vazias).")
        return text
    if fn.endswith('.txt'):
        try:
            return file_content.decode('utf-8')
        except UnicodeDecodeError:
            for encoding in ['latin1', 'cp1252', 'iso-8859-1']:
                try:
                    return file_content.decode(encoding)
                except Exception:
                    continue
            raise ValueError("Não foi possível decodificar o arquivo .txt em nenhum encoding suportado.")
    raise ValueError(f"Formato de arquivo não suportado: {filename}")
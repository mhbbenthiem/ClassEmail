import logging
from typing import Dict
from transformers import pipeline
from .utils import calculate_keyword_score, get_device_info, is_greeting_no_action, suggest_response

logger = logging.getLogger(__name__)

class EmailClassifier:
    def __init__(self):
        self.classifier_pipeline = None
        self.is_initialized = False
        self.total_classifications = 0
        self.productive_count = 0
        self.unproductive_count = 0
        self.confidence_scores = []
        
    async def initialize(self):
        """Initialize AI models"""
        try:
            logger.info("Loading sentiment analysis model...")
            
            # Use a lightweight model for better performance
            model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
            
            device = -1
            try:
                import torch  # opcional; pode não existir
                if torch.cuda.is_available():
                    device = 0
            except Exception:
                # torch ausente ou indisponível → CPU
                device = -1

            # Tenta carregar o modelo; se falhar, usa somente regras/keywords
            try:
                self.classifier_pipeline = pipeline(
                    "sentiment-analysis",
                    model=model_name,
                    tokenizer=model_name,
                    device=device,
                    max_length=512,
                    truncation=True,
                )
                self.model_loaded = True
            except Exception as e:
                self.classifier_pipeline = None
                self.model_loaded = False
            
            logger.info(f"Model loaded successfully on device: {get_device_info()}")
            self.is_initialized = True
            
        except Exception as e:
            logger.warning(f"Could not load transformer model: {e}")
            logger.info("Using fallback keyword-based classification")
            self.is_initialized = True  # Still functional with keyword-based approach

    async def classify_email(self, processed_text: str, original_text: str) -> Dict:
        """Classify email using hybrid approach: AI + Keywords"""
        # 0) Curto-circuito: felicitação/agradecimento sem pedido ⇒ Improdutivo
        if is_greeting_no_action(original_text):
            category = "Improdutivo"
            confidence = 0.95
            suggested = suggest_response(category, original_text)
            self._update_stats(category, confidence)
            return {
                "category": category,
                "confidence": confidence,
                "original_text": original_text,
                "suggested_response": suggested,
            }

        try:
            # 1) Score por keywords deve usar o TEXTO ORIGINAL (lower), não o stemmado
            keyword_result = calculate_keyword_score(original_text.lower())

            # 2) (Opcional) AI
            ai_category = None
            ai_confidence = 0.5
            if self.classifier_pipeline:
                try:
                    text_for_ai = original_text[:512]
                    ai_result = self.classifier_pipeline(text_for_ai)
                    lbl = str(ai_result[0].get("label", "")).lower()
                    ai_confidence = float(ai_result[0].get("score", 0.0))

                    # Heurística robusta p/ rótulos possíveis do modelo (negative/neutral/positive ou LABEL_*)
                    if "neg" in lbl or lbl == "label_0":
                        ai_category = "Produtivo"      # negativo costuma indicar problema → ação
                    elif "pos" in lbl or lbl == "label_2":
                        ai_category = "Improdutivo"    # positivo tende a ser elogio/agradecimento
                    else:
                        ai_category = None             # neutral → não força decisão
                except Exception as e:
                    logger.warning(f"AI classification failed: {e}")

            # 3) Combinação
            final_category, final_confidence = self._combine_results(
                keyword_result, ai_category, ai_confidence
            )

            # 4) Sugestão e métricas
            suggested = suggest_response(final_category, original_text)  # <- nome correto
            self._update_stats(final_category, final_confidence)

            return {
                "category": final_category,
                "confidence": final_confidence,
                "original_text": original_text[:100] + "..." if len(original_text) > 100 else original_text,
                "suggested_response": suggested,
            }

        except Exception as e:
            logger.exception(f"Classification error: {e}")
            # Fallback seguro: usa keywords no TEXTO ORIGINAL, atualiza métricas e inclui sugestão
            keyword_result = calculate_keyword_score(original_text.lower())
            fallback_category = keyword_result.get("category", "Produtivo")
            fallback_confidence = float(keyword_result.get("confidence", 0.5))
            suggested = suggest_response(fallback_category, original_text)
            self._update_stats(fallback_category, fallback_confidence)
            return {
                "category": fallback_category,
                "confidence": fallback_confidence,
                "original_text": original_text[:100] + "..." if len(original_text) > 100 else original_text,
                "suggested_response": suggested,
            }


    def _combine_results(self, keyword_result: Dict, ai_category: str, ai_confidence: float) -> tuple:
        """Combine keyword and AI classification results"""
        keyword_category = keyword_result['category']
        keyword_confidence = keyword_result['confidence']
        keyword_score = keyword_result['score']
        
        # If keywords provide strong signal, use that
        if keyword_score >= 3:  # Strong keyword presence
            return keyword_category, min(0.85 + (keyword_score * 0.03), 0.95)
        
        # If AI is available and confident, combine with keywords
        if ai_category and ai_confidence > 0.7:
            if ai_category == keyword_category:
                # Both agree - high confidence
                combined_confidence = min(0.8 + (ai_confidence * 0.15), 0.95)
                return keyword_category, combined_confidence
            else:
                # Disagreement - use higher confidence source
                if keyword_confidence > ai_confidence:
                    return keyword_category, keyword_confidence
                else:
                    return ai_category, ai_confidence
        
        # Fallback to keyword-based result
        return keyword_category, keyword_confidence


    def _update_stats(self, category: str, confidence: float):
        """Update classification statistics"""
        self.total_classifications += 1
        self.confidence_scores.append(confidence)
        
        if category == 'Produtivo':
            self.productive_count += 1
        else:
            self.unproductive_count += 1

    def get_average_confidence(self) -> float:
        """Get average confidence score"""
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores) / len(self.confidence_scores)
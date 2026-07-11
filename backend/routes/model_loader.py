import pickle
import threading
import os
import logging
from typing import Any, Tuple

logger = logging.getLogger(__name__)

class ModelLoader:
    """Thread-safe model loader with read-write lock."""
    
    def __init__(self):
        self._model = None
        self._vectorizer = None
        self._label_encoder = None
        self._lock = threading.RLock()
        self._model_path = os.getenv('MODEL_PATH', 'linear_svm_model.pkl')
        self._vectorizer_path = os.getenv('VECTORIZER_PATH', 'tfidf_vectorizer.pkl')
        self._label_encoder_path = os.getenv('LABEL_ENCODER_PATH', 'label_encoder.pkl')
        
        # Load initial models
        self.load_models()

    def load_models(self) -> bool:
        """Load models from disk."""
        try:
            with self._lock:
                self._model = pickle.load(open(self._model_path, 'rb'))
                self._vectorizer = pickle.load(open(self._vectorizer_path, 'rb'))
                if os.path.exists(self._label_encoder_path):
                    self._label_encoder = pickle.load(open(self._label_encoder_path, 'rb'))
                logger.info("✅ Models loaded successfully")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to load models: {e}")
            return False

    def reload_models(self) -> bool:
        """Reload models from disk without server restart."""
        try:
            # Load new models into temporary variables
            new_model = pickle.load(open(self._model_path, 'rb'))
            new_vectorizer = pickle.load(open(self._vectorizer_path, 'rb'))
            new_label_encoder = None
            if os.path.exists(self._label_encoder_path):
                new_label_encoder = pickle.load(open(self._label_encoder_path, 'rb'))

            # Acquire write lock and swap
            with self._lock:
                self._model = new_model
                self._vectorizer = new_vectorizer
                self._label_encoder = new_label_encoder
            
            logger.info("✅ Models reloaded successfully (zero downtime!)")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to reload models: {e}")
            return False

    def predict(self, text: str) -> Tuple[str, float]:
        """Predict using current model."""
        with self._lock:
            if self._model is None or self._vectorizer is None:
                raise ValueError("Models not loaded")
            
            vectorized = self._vectorizer.transform([text])
            prediction = self._model.predict(vectorized)[0]
            
            # Get confidence (if model supports it)
            confidence = 0.0
            if hasattr(self._model, 'predict_proba'):
                proba = self._model.predict_proba(vectorized)[0]
                confidence = max(proba)
            else:
                confidence = 1.0
            
            return prediction, confidence

    def get_status(self) -> dict:
        """Get model status."""
        with self._lock:
            return {
                'model_loaded': self._model is not None,
                'vectorizer_loaded': self._vectorizer is not None,
                'label_encoder_loaded': self._label_encoder is not None,
                'model_path': self._model_path,
                'vectorizer_path': self._vectorizer_path,
            }

# Global instance
model_loader = ModelLoader()
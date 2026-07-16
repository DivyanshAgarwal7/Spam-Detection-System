import pickle
import os
import logging
from typing import Tuple
from .worker import get_worker

logger = logging.getLogger(__name__)

class ModelLoader:
    """Model Loader with the worker pool."""
    
    def __init__(self):
        self.model_path = 'linear_svm_model.pkl'
        self.vectorizer_path = 'tfidf_vectorizer.pkl'
        self._worker = get_worker()
        logger.info("✅ Model loader initialized")

    def predict(self, text: str) -> Tuple[str, float]:
        """Predict using worker pool."""
        return self._worker.predict(text)

    def get_status(self) -> dict:
        """Get model status."""
        return {
            'model_path': self.model_path,
            'vectorizer_path': self.vectorizer_path,
            'worker_pool_ready': True
        }

# Global instance
model_loader = ModelLoader()

import concurrent.futures
import pickle
import os
import logging
from typing import Tuple, Any

logger = logging.getLogger(__name__)

class PredictionWorker:
    """Worker pool for CPU-bound ML inference."""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or os.cpu_count() or 4
        self.executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=self.max_workers
        )
        logger.info(f"✅ Prediction worker pool initialized with {self.max_workers} workers")
    
    def predict(self, text: str, model_path: str, vectorizer_path: str) -> Tuple[str, float]:
        """Submit prediction task to worker pool."""
        future = self.executor.submit(
            self._predict_task,
            text,
            model_path,
            vectorizer_path
        )
        return future.result()
    
    @staticmethod
    def _predict_task(text: str, model_path: str, vectorizer_path: str) -> Tuple[str, float]:
        """CPU-bound prediction task executed in worker process."""
        try:
            # Load models in worker
            model = pickle.load(open(model_path, 'rb'))
            vectorizer = pickle.load(open(vectorizer_path, 'rb'))
            
            # Vectorize and predict
            vectorized = vectorizer.transform([text])
            prediction = model.predict(vectorized)[0]
            
            # Get confidence
            confidence = 0.0
            if hasattr(model, 'predict_proba'):
                proba = model.predict_proba(vectorized)[0]
                confidence = max(proba)
            else:
                confidence = 1.0
            
            return prediction, confidence
            
        except Exception as e:
            logger.error(f"Prediction task failed: {e}")
            raise

    def shutdown(self):
        """Clean shutdown of worker pool."""
        self.executor.shutdown(wait=True)
        logger.info("✅ Worker pool shut down")

# Global worker instance
_worker = None

def get_worker() -> PredictionWorker:
    """Get or create global worker instance."""
    global _worker
    if _worker is None:
        _worker = PredictionWorker()
    return _worker
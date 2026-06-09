import os
# Avoid forcing offline mode on Render so sentence-transformers can download the model
if not os.environ.get("RENDER"):
    os.environ["HF_HUB_OFFLINE"] = "1"
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Loads sentence-transformers model (MiniLM has 384 dimensions)
        self.model = SentenceTransformer(model_name)
        
    def get_embedding(self, text: str) -> list[float]:
        if not text:
            # Return zero vector if text is empty (avoid errors)
            return [0.0] * 384
        embedding = self.model.encode(text)
        return embedding.tolist()

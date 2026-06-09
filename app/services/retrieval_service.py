from sqlalchemy.orm import Session
from app.models.models import Destination
from app.services.embedding_service import EmbeddingService

class RetrievalService:
    def __init__(self, db: Session, embedding_service: EmbeddingService):
        self.db = db
        self.embedding_service = embedding_service
        
    def add_destination(self, name: str, description: str, category: str) -> Destination:
        # Construct context representation for embedding: "Name (category): description"
        text_to_embed = f"{name} ({category}): {description}"
        embedding = self.embedding_service.get_embedding(text_to_embed)
        
        destination = Destination(
            name=name,
            description=description,
            category=category,
            embedding=embedding
        )
        self.db.add(destination)
        self.db.commit()
        self.db.refresh(destination)
        return destination
        
    def search_similar(self, query: str, limit: int = 5) -> list[Destination]:
        query_embedding = self.embedding_service.get_embedding(query)
        
        bind_name = self.db.bind.dialect.name if self.db.bind else 'postgresql'
        if bind_name == 'postgresql':
            # Use pgvector's cosine_distance order
            return self.db.query(Destination).order_by(
                Destination.embedding.cosine_distance(query_embedding)
            ).limit(limit).all()
        else:
            # SQLite fallback: retrieve all, compute cosine similarity in Python
            destinations = self.db.query(Destination).all()
            
            import math
            def cosine_similarity(v1, v2):
                if not v1 or not v2:
                    return 0.0
                dot_product = sum(x * y for x, y in zip(v1, v2))
                magnitude1 = math.sqrt(sum(x * x for x in v1))
                magnitude2 = math.sqrt(sum(y * y for y in v2))
                if not magnitude1 or not magnitude2:
                    return 0.0
                return dot_product / (magnitude1 * magnitude2)
            
            scored = []
            for d in destinations:
                dist = 1.0 - cosine_similarity(d.embedding, query_embedding)
                scored.append((dist, d))
                
            scored.sort(key=lambda x: x[0])
            return [d for _, d in scored[:limit]]

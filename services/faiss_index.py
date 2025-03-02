"""
this file is responsible for creating and loading FAISS indexes.
"""
import os
from langchain_community.vectorstores import FAISS
# from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores.faiss import DistanceStrategy
from langchain_openai import OpenAIEmbeddings

from core import settings
class FAISSIndexService:
    """Service for creating and loading FAISS indexes."""
    def __init__(self):
        self.embeddings_model = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY, model=settings.EMBEDDING_MODEL)
        self.vector_store = None

    async def create_faiss_index(self, documents):
        """Create and save a FAISS index."""
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        self.vector_store = await FAISS.afrom_texts(texts=texts, embedding=self.embeddings_model, metadatas=metadatas) # ,distance_strategy=DistanceStrategy.JACCARD
        self.vector_store.save_local(settings.FAISS_INDEX_PATH)
        print(f"FAISS index saved to {settings.FAISS_INDEX_PATH}")

    def load_index(self):
        """Load the FAISS index."""
        if os.path.exists(settings.FAISS_INDEX_PATH):
            self.vector_store = FAISS.load_local(settings.FAISS_INDEX_PATH, self.embeddings_model,allow_dangerous_deserialization=True)            
        return self.vector_store
    

  





















  


from pydantic_settings import BaseSettings
from .get_secret import get_secret

class Settings(BaseSettings):
    APP_API_KEY: str = "4e3f2b5c8a1d6e7f9a2b3c4d5f6ed235"
    OPENAI_API_KEY: str = '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'
    LANGCHAIN_API_KEY: str = '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'
    LANGCHAIN_TRACING_V2: str= "true"
    LANGSMITH_PROJECT :str = "Wzgate Chatbot"
    LANGCHAIN_ENDPOINT :str = "https://api.smith.langchain.com"
    EMBEDDING_MODEL :str = "text-embedding-3-large"
    LOG_LEVEL: str = 'INFO'
    MODEL_NAME: str = 'gpt-4o-mini'
    DOCUMENTS_JSON_PATH: str = "test_data.json"
    SOURCE_DATA: str = r"services/source_doc"
    FAISS_INDEX_PATH: str = SOURCE_DATA + "_faiss_index"
    MIN_CHUNK_SIZE: int = 300
    BREAKPOINT_THRESHOLD: float = 0.5


settings = Settings()

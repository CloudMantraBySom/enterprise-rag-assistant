from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Azure OpenAI
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_openai_chat_deployment: str = "gpt-4o"
    azure_openai_embed_deployment: str = "text-embedding-3-large"

    # Local fallback
    openai_api_key: str = ""

    # Web search
    tavily_api_key: str = ""

    # Observability
    langchain_api_key: str = ""
    langchain_tracing_v2: str = "true"
    langchain_project: str = "enterprise-rag-assistant"

    # Storage
    vector_store_path: str = "./vector_store"
    docs_path: str = "./data"

    # RAG tuning
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_k: int = 4


settings = Settings()

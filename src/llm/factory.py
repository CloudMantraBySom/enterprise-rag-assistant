from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from src.config import settings


def get_llm(temperature: float = 0.0):
    """Return Azure OpenAI chat model; fall back to direct OpenAI for local dev."""
    if settings.azure_openai_api_key:
        return AzureChatOpenAI(
            azure_deployment=settings.azure_openai_chat_deployment,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            temperature=temperature,
        )
    return ChatOpenAI(
        model="gpt-4o",
        temperature=temperature,
        api_key=settings.openai_api_key,
    )


def get_embeddings():
    """Return Azure OpenAI embeddings; fall back to direct OpenAI."""
    if settings.azure_openai_api_key:
        return AzureOpenAIEmbeddings(
            azure_deployment=settings.azure_openai_embed_deployment,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
        )
    return OpenAIEmbeddings(
        model="text-embedding-3-large",
        api_key=settings.openai_api_key,
    )

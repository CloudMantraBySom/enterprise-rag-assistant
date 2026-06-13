import os
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from src.config import settings
from src.llm.factory import get_embeddings


def build_vector_store():
    """Load PDFs from DOCS_PATH, chunk, embed, persist FAISS index."""
    loader = PyPDFDirectoryLoader(settings.docs_path)
    docs   = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_documents(docs)

    db = FAISS.from_documents(chunks, get_embeddings())
    db.save_local(settings.vector_store_path)
    print(f"Indexed {len(chunks)} chunks from {len(docs)} pages.")
    return db


def load_vector_store():
    if not os.path.exists(settings.vector_store_path):
        return build_vector_store()
    return FAISS.load_local(
        settings.vector_store_path,
        get_embeddings(),
        allow_dangerous_deserialization=True,
    )


def get_retriever():
    return load_vector_store().as_retriever(
        search_kwargs={"k": settings.retrieval_k}
    )

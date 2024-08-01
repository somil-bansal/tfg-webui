import json
import logging
import mimetypes
import os
import socket
import urllib.parse
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Union, Sequence, Iterator, Dict, Any
from typing import Optional

import nltk
# from langchain.text_splitter import RecursiveCharacterTextSplitter
import pymupdf4llm
import sentence_transformers
import validators
from chromadb.utils.batch_utils import create_batches
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
)
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from llama_index.core.node_parser import SimpleNodeParser, MarkdownElementNodeParser, TokenTextSplitter
from llama_index.core.schema import ImageNode, TextNode, ImageDocument
# from langchain_core.documents import Document
from llama_index.core.utils import Tokenizer
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.readers.file import (
    UnstructuredReader
)
from llama_parse import LlamaParse
from pydantic import BaseModel
from llama_index.core.schema import Document as LlamaIndexDocument
from pymupdf import pymupdf
from redis.commands.search import result
from unstructured.documents.elements import CompositeElement, Element, Table, Image, Text
from unstructured.partition.pdf import partition_pdf
from unstructured.staging.base import elements_to_json

from apps.rag.search.brave import search_brave
from apps.rag.search.duckduckgo import search_duckduckgo
from apps.rag.search.google_pse import search_google_pse
from apps.rag.search.jina_search import search_jina
from apps.rag.search.main import SearchResult
from apps.rag.search.searxng import search_searxng
from apps.rag.search.serper import search_serper
from apps.rag.search.serply import search_serply
from apps.rag.search.serpstack import search_serpstack
from apps.rag.search.tavily import search_tavily
from apps.rag.utils import (
    get_model_path,
    get_embedding_function,
    query_doc,
    query_doc_with_hybrid_search,
)
from apps.webui.models.documents import (
    Documents,
    DocumentForm,
)
from apps.webui.models.files import (
    Files,
)
from config import (
    AppConfig,
    ENV,
    SRC_LOG_LEVELS,
    UPLOAD_DIR,
    DOCS_DIR,
    RAG_TOP_K,
    RAG_RELEVANCE_THRESHOLD,
    RAG_EMBEDDING_ENGINE,
    RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
    RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
    ENABLE_RAG_HYBRID_SEARCH,
    ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
    RAG_RERANKING_MODEL,
    PDF_EXTRACT_IMAGES,
    RAG_RERANKING_MODEL_AUTO_UPDATE,
    RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
    RAG_OPENAI_API_BASE_URL,
    RAG_OPENAI_API_KEY,
    DEVICE_TYPE,
    CHROMA_CLIENT,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    RAG_TEMPLATE,
    ENABLE_RAG_LOCAL_WEB_FETCH,
    ENABLE_RAG_WEB_SEARCH,
    RAG_WEB_SEARCH_ENGINE,
    RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
    SEARXNG_QUERY_URL,
    GOOGLE_PSE_API_KEY,
    GOOGLE_PSE_ENGINE_ID,
    BRAVE_SEARCH_API_KEY,
    SERPSTACK_API_KEY,
    SERPSTACK_HTTPS,
    SERPER_API_KEY,
    SERPLY_API_KEY,
    TAVILY_API_KEY,
    RAG_WEB_SEARCH_RESULT_COUNT,
    RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
    RAG_EMBEDDING_OPENAI_BATCH_SIZE,
)
from constants import ERROR_MESSAGES
from utils.misc import (
    calculate_sha256,
    calculate_sha256_string,
    sanitize_filename,
    extract_folders_after_data_docs,
)
from utils.utils import get_verified_user, get_admin_user, get_data_admin

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

app = FastAPI()

app.state.config = AppConfig()

app.state.config.TOP_K = RAG_TOP_K
app.state.config.RELEVANCE_THRESHOLD = RAG_RELEVANCE_THRESHOLD

app.state.config.ENABLE_RAG_HYBRID_SEARCH = ENABLE_RAG_HYBRID_SEARCH
app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION = (
    ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION
)

app.state.config.CHUNK_SIZE = CHUNK_SIZE
app.state.config.CHUNK_OVERLAP = CHUNK_OVERLAP

app.state.config.RAG_EMBEDDING_ENGINE = RAG_EMBEDDING_ENGINE
app.state.config.RAG_EMBEDDING_MODEL = RAG_EMBEDDING_MODEL
app.state.config.RAG_EMBEDDING_OPENAI_BATCH_SIZE = RAG_EMBEDDING_OPENAI_BATCH_SIZE
app.state.config.RAG_RERANKING_MODEL = RAG_RERANKING_MODEL
app.state.config.RAG_TEMPLATE = RAG_TEMPLATE

app.state.config.OPENAI_API_BASE_URL = RAG_OPENAI_API_BASE_URL
app.state.config.OPENAI_API_KEY = RAG_OPENAI_API_KEY

app.state.config.PDF_EXTRACT_IMAGES = PDF_EXTRACT_IMAGES

app.state.config.ENABLE_RAG_WEB_SEARCH = ENABLE_RAG_WEB_SEARCH
app.state.config.RAG_WEB_SEARCH_ENGINE = RAG_WEB_SEARCH_ENGINE
app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST = RAG_WEB_SEARCH_DOMAIN_FILTER_LIST

app.state.config.SEARXNG_QUERY_URL = SEARXNG_QUERY_URL
app.state.config.GOOGLE_PSE_API_KEY = GOOGLE_PSE_API_KEY
app.state.config.GOOGLE_PSE_ENGINE_ID = GOOGLE_PSE_ENGINE_ID
app.state.config.BRAVE_SEARCH_API_KEY = BRAVE_SEARCH_API_KEY
app.state.config.SERPSTACK_API_KEY = SERPSTACK_API_KEY
app.state.config.SERPSTACK_HTTPS = SERPSTACK_HTTPS
app.state.config.SERPER_API_KEY = SERPER_API_KEY
app.state.config.SERPLY_API_KEY = SERPLY_API_KEY
app.state.config.TAVILY_API_KEY = TAVILY_API_KEY
app.state.config.RAG_WEB_SEARCH_RESULT_COUNT = RAG_WEB_SEARCH_RESULT_COUNT
app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS = RAG_WEB_SEARCH_CONCURRENT_REQUESTS


def update_embedding_model(
        embedding_model: str,
        update_model: bool = False,
):
    if embedding_model and app.state.config.RAG_EMBEDDING_ENGINE == "":
        app.state.sentence_transformer_ef = sentence_transformers.SentenceTransformer(
            get_model_path(embedding_model, update_model),
            device=DEVICE_TYPE,
            trust_remote_code=RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
        )
    else:
        app.state.sentence_transformer_ef = None


def update_reranking_model(
        reranking_model: str,
        update_model: bool = False,
):
    if reranking_model:
        app.state.sentence_transformer_rf = sentence_transformers.CrossEncoder(
            get_model_path(reranking_model, update_model),
            device=DEVICE_TYPE,
            trust_remote_code=RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
        )
    else:
        app.state.sentence_transformer_rf = None


update_embedding_model(
    app.state.config.RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
)

update_reranking_model(
    app.state.config.RAG_RERANKING_MODEL,
    RAG_RERANKING_MODEL_AUTO_UPDATE,
)

app.state.EMBEDDING_FUNCTION = get_embedding_function(
    app.state.config.RAG_EMBEDDING_ENGINE,
    app.state.config.RAG_EMBEDDING_MODEL,
    app.state.sentence_transformer_ef,
    app.state.config.OPENAI_API_KEY,
    app.state.config.OPENAI_API_BASE_URL,
    app.state.config.RAG_EMBEDDING_OPENAI_BATCH_SIZE,
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CollectionNameForm(BaseModel):
    collection_name: Optional[str] = "test"


class UrlForm(CollectionNameForm):
    url: str


class SearchForm(CollectionNameForm):
    query: str


@app.get("/")
async def get_status():
    return {
        "status": True,
        "chunk_size": app.state.config.CHUNK_SIZE,
        "chunk_overlap": app.state.config.CHUNK_OVERLAP,
        "template": app.state.config.RAG_TEMPLATE,
        "embedding_engine": app.state.config.RAG_EMBEDDING_ENGINE,
        "embedding_model": app.state.config.RAG_EMBEDDING_MODEL,
        "reranking_model": app.state.config.RAG_RERANKING_MODEL,
        "openai_batch_size": app.state.config.RAG_EMBEDDING_OPENAI_BATCH_SIZE,
    }


@app.get("/embedding")
async def get_embedding_config(user=Depends(get_admin_user)):
    return {
        "status": True,
        "embedding_engine": app.state.config.RAG_EMBEDDING_ENGINE,
        "embedding_model": app.state.config.RAG_EMBEDDING_MODEL,
        "openai_config": {
            "url": app.state.config.OPENAI_API_BASE_URL,
            "key": app.state.config.OPENAI_API_KEY,
            "batch_size": app.state.config.RAG_EMBEDDING_OPENAI_BATCH_SIZE,
        },
    }


@app.get("/reranking")
async def get_reraanking_config(user=Depends(get_admin_user)):
    return {
        "status": True,
        "reranking_model": app.state.config.RAG_RERANKING_MODEL,
    }


class OpenAIConfigForm(BaseModel):
    url: str
    key: str
    batch_size: Optional[int] = None


class EmbeddingModelUpdateForm(BaseModel):
    openai_config: Optional[OpenAIConfigForm] = None
    embedding_engine: str
    embedding_model: str


@app.post("/embedding/update")
async def update_embedding_config(
        form_data: EmbeddingModelUpdateForm, user=Depends(get_admin_user)
):
    log.info(
        f"Updating embedding model: {app.state.config.RAG_EMBEDDING_MODEL} to {form_data.embedding_model}"
    )
    try:
        app.state.config.RAG_EMBEDDING_ENGINE = form_data.embedding_engine
        app.state.config.RAG_EMBEDDING_MODEL = form_data.embedding_model

        if app.state.config.RAG_EMBEDDING_ENGINE in ["ollama", "openai"]:
            if form_data.openai_config is not None:
                app.state.config.OPENAI_API_BASE_URL = form_data.openai_config.url
                app.state.config.OPENAI_API_KEY = form_data.openai_config.key
                app.state.config.RAG_EMBEDDING_OPENAI_BATCH_SIZE = (
                    form_data.openai_config.batch_size
                    if form_data.openai_config.batch_size
                    else 1
                )

        update_embedding_model(app.state.config.RAG_EMBEDDING_MODEL)

        app.state.EMBEDDING_FUNCTION = get_embedding_function(
            app.state.config.RAG_EMBEDDING_ENGINE,
            app.state.config.RAG_EMBEDDING_MODEL,
            app.state.sentence_transformer_ef,
            app.state.config.OPENAI_API_KEY,
            app.state.config.OPENAI_API_BASE_URL,
            app.state.config.RAG_EMBEDDING_OPENAI_BATCH_SIZE,
        )

        return {
            "status": True,
            "embedding_engine": app.state.config.RAG_EMBEDDING_ENGINE,
            "embedding_model": app.state.config.RAG_EMBEDDING_MODEL,
            "openai_config": {
                "url": app.state.config.OPENAI_API_BASE_URL,
                "key": app.state.config.OPENAI_API_KEY,
                "batch_size": app.state.config.RAG_EMBEDDING_OPENAI_BATCH_SIZE,
            },
        }
    except Exception as e:
        log.exception(f"Problem updating embedding model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


class RerankingModelUpdateForm(BaseModel):
    reranking_model: str


@app.post("/reranking/update")
async def update_reranking_config(
        form_data: RerankingModelUpdateForm, user=Depends(get_admin_user)
):
    log.info(
        f"Updating reranking model: {app.state.config.RAG_RERANKING_MODEL} to {form_data.reranking_model}"
    )
    try:
        app.state.config.RAG_RERANKING_MODEL = form_data.reranking_model

        update_reranking_model(app.state.config.RAG_RERANKING_MODEL), True

        return {
            "status": True,
            "reranking_model": app.state.config.RAG_RERANKING_MODEL,
        }
    except Exception as e:
        log.exception(f"Problem updating reranking model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@app.get("/config")
async def get_rag_config(user=Depends(get_admin_user)):
    return {
        "status": True,
        "pdf_extract_images": app.state.config.PDF_EXTRACT_IMAGES,
        "chunk": {
            "chunk_size": app.state.config.CHUNK_SIZE,
            "chunk_overlap": app.state.config.CHUNK_OVERLAP,
        },
        "web": {
            "ssl_verification": app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
            "search": {
                "enabled": app.state.config.ENABLE_RAG_WEB_SEARCH,
                "engine": app.state.config.RAG_WEB_SEARCH_ENGINE,
                "searxng_query_url": app.state.config.SEARXNG_QUERY_URL,
                "google_pse_api_key": app.state.config.GOOGLE_PSE_API_KEY,
                "google_pse_engine_id": app.state.config.GOOGLE_PSE_ENGINE_ID,
                "brave_search_api_key": app.state.config.BRAVE_SEARCH_API_KEY,
                "serpstack_api_key": app.state.config.SERPSTACK_API_KEY,
                "serpstack_https": app.state.config.SERPSTACK_HTTPS,
                "serper_api_key": app.state.config.SERPER_API_KEY,
                "serply_api_key": app.state.config.SERPLY_API_KEY,
                "tavily_api_key": app.state.config.TAVILY_API_KEY,
                "result_count": app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                "concurrent_requests": app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
            },
        },
    }


class ChunkParamUpdateForm(BaseModel):
    chunk_size: int
    chunk_overlap: int


class WebSearchConfig(BaseModel):
    enabled: bool
    engine: Optional[str] = None
    searxng_query_url: Optional[str] = None
    google_pse_api_key: Optional[str] = None
    google_pse_engine_id: Optional[str] = None
    brave_search_api_key: Optional[str] = None
    serpstack_api_key: Optional[str] = None
    serpstack_https: Optional[bool] = None
    serper_api_key: Optional[str] = None
    serply_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None
    result_count: Optional[int] = None
    concurrent_requests: Optional[int] = None


class WebConfig(BaseModel):
    search: WebSearchConfig
    web_loader_ssl_verification: Optional[bool] = None


class ConfigUpdateForm(BaseModel):
    pdf_extract_images: Optional[bool] = None
    chunk: Optional[ChunkParamUpdateForm] = None
    web: Optional[WebConfig] = None


@app.post("/config/update")
async def update_rag_config(form_data: ConfigUpdateForm, user=Depends(get_admin_user)):
    app.state.config.PDF_EXTRACT_IMAGES = (
        form_data.pdf_extract_images
        if form_data.pdf_extract_images is not None
        else app.state.config.PDF_EXTRACT_IMAGES
    )

    if form_data.chunk is not None:
        app.state.config.CHUNK_SIZE = form_data.chunk.chunk_size
        app.state.config.CHUNK_OVERLAP = form_data.chunk.chunk_overlap

    if form_data.web is not None:
        app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION = (
            form_data.web.web_loader_ssl_verification
        )

        app.state.config.ENABLE_RAG_WEB_SEARCH = form_data.web.search.enabled
        app.state.config.RAG_WEB_SEARCH_ENGINE = form_data.web.search.engine
        app.state.config.SEARXNG_QUERY_URL = form_data.web.search.searxng_query_url
        app.state.config.GOOGLE_PSE_API_KEY = form_data.web.search.google_pse_api_key
        app.state.config.GOOGLE_PSE_ENGINE_ID = (
            form_data.web.search.google_pse_engine_id
        )
        app.state.config.BRAVE_SEARCH_API_KEY = (
            form_data.web.search.brave_search_api_key
        )
        app.state.config.SERPSTACK_API_KEY = form_data.web.search.serpstack_api_key
        app.state.config.SERPSTACK_HTTPS = form_data.web.search.serpstack_https
        app.state.config.SERPER_API_KEY = form_data.web.search.serper_api_key
        app.state.config.SERPLY_API_KEY = form_data.web.search.serply_api_key
        app.state.config.TAVILY_API_KEY = form_data.web.search.tavily_api_key
        app.state.config.RAG_WEB_SEARCH_RESULT_COUNT = form_data.web.search.result_count
        app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS = (
            form_data.web.search.concurrent_requests
        )

    return {
        "status": True,
        "pdf_extract_images": app.state.config.PDF_EXTRACT_IMAGES,
        "chunk": {
            "chunk_size": app.state.config.CHUNK_SIZE,
            "chunk_overlap": app.state.config.CHUNK_OVERLAP,
        },
        "web": {
            "ssl_verification": app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
            "search": {
                "enabled": app.state.config.ENABLE_RAG_WEB_SEARCH,
                "engine": app.state.config.RAG_WEB_SEARCH_ENGINE,
                "searxng_query_url": app.state.config.SEARXNG_QUERY_URL,
                "google_pse_api_key": app.state.config.GOOGLE_PSE_API_KEY,
                "google_pse_engine_id": app.state.config.GOOGLE_PSE_ENGINE_ID,
                "brave_search_api_key": app.state.config.BRAVE_SEARCH_API_KEY,
                "serpstack_api_key": app.state.config.SERPSTACK_API_KEY,
                "serpstack_https": app.state.config.SERPSTACK_HTTPS,
                "serper_api_key": app.state.config.SERPER_API_KEY,
                "serply_api_key": app.state.config.SERPLY_API_KEY,
                "tavily_api_key": app.state.config.TAVILY_API_KEY,
                "result_count": app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                "concurrent_requests": app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
            },
        },
    }


@app.get("/template")
async def get_rag_template(user=Depends(get_verified_user)):
    return {
        "status": True,
        "template": app.state.config.RAG_TEMPLATE,
    }


@app.get("/query/settings")
async def get_query_settings(user=Depends(get_admin_user)):
    return {
        "status": True,
        "template": app.state.config.RAG_TEMPLATE,
        "k": app.state.config.TOP_K,
        "r": app.state.config.RELEVANCE_THRESHOLD,
        "hybrid": app.state.config.ENABLE_RAG_HYBRID_SEARCH,
    }


class QuerySettingsForm(BaseModel):
    k: Optional[int] = None
    r: Optional[float] = None
    template: Optional[str] = None
    hybrid: Optional[bool] = None


@app.post("/query/settings/update")
async def update_query_settings(
        form_data: QuerySettingsForm, user=Depends(get_admin_user)
):
    app.state.config.RAG_TEMPLATE = (
        form_data.template if form_data.template else RAG_TEMPLATE
    )
    app.state.config.TOP_K = form_data.k if form_data.k else 4
    app.state.config.RELEVANCE_THRESHOLD = form_data.r if form_data.r else 0.0
    app.state.config.ENABLE_RAG_HYBRID_SEARCH = (
        form_data.hybrid if form_data.hybrid else False
    )
    return {
        "status": True,
        "template": app.state.config.RAG_TEMPLATE,
        "k": app.state.config.TOP_K,
        "r": app.state.config.RELEVANCE_THRESHOLD,
        "hybrid": app.state.config.ENABLE_RAG_HYBRID_SEARCH,
    }


class QueryDocForm(BaseModel):
    collection_name: str
    query: str
    k: Optional[int] = None
    r: Optional[float] = None
    hybrid: Optional[bool] = None


@app.post("/query/doc")
def query_doc_handler(
        form_data: QueryDocForm,
        user=Depends(get_verified_user),
):
    try:
        if app.state.config.ENABLE_RAG_HYBRID_SEARCH:
            return query_doc_with_hybrid_search(
                collection_name=form_data.collection_name,
                query=form_data.query,
                embedding_function=app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else app.state.config.TOP_K,
                reranking_function=app.state.sentence_transformer_rf,
                r=(
                    form_data.r if form_data.r else app.state.config.RELEVANCE_THRESHOLD
                ),
            )
        else:
            return query_doc(
                collection_name=form_data.collection_name,
                query=form_data.query,
                embedding_function=app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else app.state.config.TOP_K,
            )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


class QueryCollectionsForm(BaseModel):
    collection_names: List[str]
    query: str
    k: Optional[int] = None
    r: Optional[float] = None
    hybrid: Optional[bool] = None


@app.post("/web")
def store_web(form_data: UrlForm, user=Depends(get_verified_user)):
    try:
        loader = get_web_loader(
            form_data.url,
            verify_ssl=app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
        )
        data = loader.load()

        collection_name = form_data.collection_name
        if collection_name == "":
            collection_name = calculate_sha256_string(form_data.url)[:63]

        store_data_in_vector_db(data, collection_name, overwrite=True)
        return {
            "status": True,
            "collection_name": collection_name,
            "filename": form_data.url,
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


def get_web_loader(url: Union[str, Sequence[str]], verify_ssl: bool = True):
    # Check if the URL is valid
    if not validate_url(url):
        raise ValueError(ERROR_MESSAGES.INVALID_URL)
    return SafeWebBaseLoader(
        url,
        verify_ssl=verify_ssl,
        requests_per_second=RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
        continue_on_failure=True,
    )


def validate_url(url: Union[str, Sequence[str]]):
    if isinstance(url, str):
        if isinstance(validators.url(url), validators.ValidationError):
            raise ValueError(ERROR_MESSAGES.INVALID_URL)
        if not ENABLE_RAG_LOCAL_WEB_FETCH:
            # Local web fetch is disabled, filter out any URLs that resolve to private IP addresses
            parsed_url = urllib.parse.urlparse(url)
            # Get IPv4 and IPv6 addresses
            ipv4_addresses, ipv6_addresses = resolve_hostname(parsed_url.hostname)
            # Check if any of the resolved addresses are private
            # This is technically still vulnerable to DNS rebinding attacks, as we don't control WebBaseLoader
            for ip in ipv4_addresses:
                if validators.ipv4(ip, private=True):
                    raise ValueError(ERROR_MESSAGES.INVALID_URL)
            for ip in ipv6_addresses:
                if validators.ipv6(ip, private=True):
                    raise ValueError(ERROR_MESSAGES.INVALID_URL)
        return True
    elif isinstance(url, Sequence):
        return all(validate_url(u) for u in url)
    else:
        return False


def resolve_hostname(hostname):
    # Get address information
    addr_info = socket.getaddrinfo(hostname, None)

    # Extract IP addresses from address information
    ipv4_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET]
    ipv6_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET6]

    return ipv4_addresses, ipv6_addresses


def search_web(engine: str, query: str) -> list[SearchResult]:
    """Search the web using a search engine and return the results as a list of SearchResult objects.
    Will look for a search engine API key in environment variables in the following order:
    - SEARXNG_QUERY_URL
    - GOOGLE_PSE_API_KEY + GOOGLE_PSE_ENGINE_ID
    - BRAVE_SEARCH_API_KEY
    - SERPSTACK_API_KEY
    - SERPER_API_KEY
    - SERPLY_API_KEY
    - TAVILY_API_KEY
    Args:
        query (str): The query to search for
    """

    # TODO: add playwright to search the web
    if engine == "searxng":
        if app.state.config.SEARXNG_QUERY_URL:
            return search_searxng(
                app.state.config.SEARXNG_QUERY_URL,
                query,
                app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SEARXNG_QUERY_URL found in environment variables")
    elif engine == "google_pse":
        if (
                app.state.config.GOOGLE_PSE_API_KEY
                and app.state.config.GOOGLE_PSE_ENGINE_ID
        ):
            return search_google_pse(
                app.state.config.GOOGLE_PSE_API_KEY,
                app.state.config.GOOGLE_PSE_ENGINE_ID,
                query,
                app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception(
                "No GOOGLE_PSE_API_KEY or GOOGLE_PSE_ENGINE_ID found in environment variables"
            )
    elif engine == "brave":
        if app.state.config.BRAVE_SEARCH_API_KEY:
            return search_brave(
                app.state.config.BRAVE_SEARCH_API_KEY,
                query,
                app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No BRAVE_SEARCH_API_KEY found in environment variables")
    elif engine == "serpstack":
        if app.state.config.SERPSTACK_API_KEY:
            return search_serpstack(
                app.state.config.SERPSTACK_API_KEY,
                query,
                app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
                https_enabled=app.state.config.SERPSTACK_HTTPS,
            )
        else:
            raise Exception("No SERPSTACK_API_KEY found in environment variables")
    elif engine == "serper":
        if app.state.config.SERPER_API_KEY:
            return search_serper(
                app.state.config.SERPER_API_KEY,
                query,
                app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SERPER_API_KEY found in environment variables")
    elif engine == "serply":
        if app.state.config.SERPLY_API_KEY:
            return search_serply(
                app.state.config.SERPLY_API_KEY,
                query,
                app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SERPLY_API_KEY found in environment variables")
    elif engine == "duckduckgo":
        return search_duckduckgo(
            query,
            app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
            app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == "tavily":
        if app.state.config.TAVILY_API_KEY:
            return search_tavily(
                app.state.config.TAVILY_API_KEY,
                query,
                app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
            )
        else:
            raise Exception("No TAVILY_API_KEY found in environment variables")
    elif engine == "jina":
        return search_jina(query, app.state.config.RAG_WEB_SEARCH_RESULT_COUNT)
    else:
        raise Exception("No search engine API key found in environment variables")


@app.post("/web/search")
def store_web_search(form_data: SearchForm, user=Depends(get_verified_user)):
    try:
        logging.info(
            f"trying to web search with {app.state.config.RAG_WEB_SEARCH_ENGINE, form_data.query}"
        )
        web_results = search_web(
            app.state.config.RAG_WEB_SEARCH_ENGINE, form_data.query
        )
    except Exception as e:
        log.exception(e)

        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.WEB_SEARCH_ERROR(e),
        )

    try:
        urls = [result.link for result in web_results]
        loader = get_web_loader(urls)
        data = loader.load()

        collection_name = form_data.collection_name
        if collection_name == "":
            collection_name = calculate_sha256_string(form_data.query)[:63]

        store_data_in_vector_db(data, collection_name, overwrite=True)
        return {
            "status": True,
            "collection_name": collection_name,
            "filenames": urls,
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


# def custom_chunking_tokenizer(text, chunk_size=512, chunk_overlap=20):
#     chunks = []
#     current_chunk = ""
#     current_chunk_size = 0
#
#     for line in text.split('\n'):
#         # line_tokens = Tokenizer.encode(line)
#         # line_token_count = len(line_tokens)
#
#         if line.startswith('!['):  # Image reference in Markdown
#             if current_chunk:
#                 chunks.append(current_chunk.strip())
#             chunks.append(line)
#             current_chunk = ""
#             current_chunk_size = 0
#         elif current_chunk_size + line_token_count > chunk_size:
#             if current_chunk:
#                 chunks.append(current_chunk.strip())
#             current_chunk = line + "\n"
#             current_chunk_size = line_token_count
#         else:
#             current_chunk += line + "\n"
#             current_chunk_size += line_token_count
#
#     if current_chunk:
#         chunks.append(current_chunk.strip())
#
#     return chunks


def get_text_nodes(docs: List[LlamaIndexDocument]):
    text_nodes = []
    for idx, page in enumerate(docs):
        text_node = TextNode(text="", metadata={})
        text_nodes.append(text_node)
    return text_nodes


multi_modal_llm = AzureOpenAI(
    engine="tfg-gpt4o",
    azure_endpoint="https://tfgam-aze-eus-openai.openai.azure.com/",
    api_key="fad496d248804765991834c0933b8f26",
    api_version="2024-02-15-preview",
    temperature=0.4,
    model="gpt-4o",
    streaming=False,
)


def get_image_text_nodes(docs: List[LlamaIndexDocument]):
    image_dicts = "get iamges here"
    image_text_nodes = []
    for image_dict in image_dicts:
        image_doc = ImageDocument(iamge_path=image_dict["path"])
        response = multi_modal_llm.complete(prompt="Describe image as alt text, if it is a chart of graph, "
                                                   "be accurate in text describing relationships",
                                            image_documents=[image_doc]
                                            )
        text_node = TextNode(text=str(response), metadata={})
        image_text_nodes.append(text_node)
        return image_text_nodes


def store_data_in_vector_db(data, collection_name, overwrite: bool = False) -> bool:
    # TODO: Create metadata tags, clean docs, process images, process tables,
    # node_parser = SimpleNodeParser.from_defaults(chunk_size=app.state.config.CHUNK_SIZE,
    #                                              chunk_overlap=app.state.config.CHUNK_OVERLAP,
    #                                              tokenizer=custom_chunking_tokenizer)

    # nodes = node_parser.get_nodes_from_documents(data)
    # Process the nodes, handling text and images separately
    # processed_nodes = []
    # for node in nodes:
    #     if node.text.startswith('!['):  # Image node
    #         # Extract image path or data from the Markdown reference
    #         image_path = node.text.split('(')[1].split(')')[0]
    #         processed_nodes.append(ImageNode(image_path=image_path))
    #     else:  # Text node
    #         processed_nodes.append(TextNode(text=node.text))

    text_nodes = get_text_nodes(data)
    image_nodes = get_image_text_nodes(data)
    return store_docs_in_vector_db(text_nodes + image_nodes, collection_name, overwrite)


def store_text_in_vector_db(
        text, metadata, collection_name, overwrite: bool = False
) -> bool:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=app.state.config.CHUNK_SIZE,
        chunk_overlap=app.state.config.CHUNK_OVERLAP,
        add_start_index=True,
    )
    docs = text_splitter.create_documents([text], metadatas=[metadata])
    return store_docs_in_vector_db(docs, collection_name, overwrite)


def store_docs_in_vector_db(docs, collection_name, overwrite: bool = False) -> bool:
    log.info(f"store_docs_in_vector_db {docs} {collection_name}")

    texts = [doc.page_content for doc in docs]
    metadatas = [doc.metadata for doc in docs]

    # ChromaDB does not like datetime formats
    # for meta-data so convert them to string.
    for metadata in metadatas:
        for key, value in metadata.items():
            if isinstance(value, datetime):
                metadata[key] = str(value)

    try:
        if overwrite:
            for collection in CHROMA_CLIENT.list_collections():
                if collection_name == collection.name:
                    log.info(f"deleting existing collection {collection_name}")
                    CHROMA_CLIENT.delete_collection(name=collection_name)

        collection = CHROMA_CLIENT.create_collection(name=collection_name)

        embedding_func = get_embedding_function(
            app.state.config.RAG_EMBEDDING_ENGINE,
            app.state.config.RAG_EMBEDDING_MODEL,
            app.state.sentence_transformer_ef,
            app.state.config.OPENAI_API_KEY,
            app.state.config.OPENAI_API_BASE_URL,
            app.state.config.RAG_EMBEDDING_OPENAI_BATCH_SIZE,
        )

        embedding_texts = list(map(lambda x: x.replace("\n", " "), texts))
        embeddings = embedding_func(embedding_texts)

        for batch in create_batches(
                api=CHROMA_CLIENT,
                ids=[str(uuid.uuid4()) for _ in texts],
                metadatas=metadatas,
                embeddings=embeddings,
                documents=texts,
        ):
            collection.add(*batch)

        return True
    except Exception as e:
        log.exception(e)
        if e.__class__.__name__ == "UniqueConstraintError":
            return True

        return False


def extract_pdf_content_with_context(file_path: str) -> List[Dict[str, Any]]:
    """
    Extract text, images, and tables from a PDF using PyMuPDF while maintaining their order and context.

    Args:
        file_path (str): Path to the input PDF file.

    Returns:
        List[Dict[str, Any]]: List of extracted elements with their content, metadata, and context.
    """
    doc = pymupdf.open(file_path)
    extracted_data = []

    for page_num, page in enumerate(doc):
        page_content = []

        # Extract text blocks
        text_blocks = page.get_text("blocks")
        for block in text_blocks:
            x0, y0, x1, y1, text, block_no, block_type = block
            if block_type == 0:  # Text block
                page_content.append({
                    "type": "Text",
                    "content": text.strip(),
                    "bbox": (x0, y0, x1, y1),
                    "metadata": {"page": page_num + 1}
                })

        # Extract images
        images = page.get_images(full=True)
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_data = base_image["image"]
            image_ext = base_image["ext"]
            image_filename = f"image_p{page_num + 1}_{img_index + 1}.{image_ext}"
            with open(image_filename, "wb") as image_file:
                image_file.write(image_data)

            # Get image rectangle
            image_rect = page.get_image_bbox(img)
            page_content.append({
                "type": "Image",
                "content": image_filename,
                "bbox": image_rect,
                "metadata": {"page": page_num + 1}
            })

        # Extract tables
        tables = page.find_tables()
        for table_index, table in enumerate(tables):
            df = table.to_pandas()
            page_content.append({
                "type": "Table",
                "content": df,
                "bbox": table.bbox,
                "metadata": {"page": page_num + 1}
            })

        # Sort page content by vertical position (top to bottom)
        page_content.sort(key=lambda x: x['bbox'][1])

        extracted_data.extend(page_content)

    doc.close()
    return extracted_data


def group_elements_by_proximity(extracted_data: List[Dict[str, Any]], proximity_threshold: float = 20.0) -> List[
    Dict[str, Any]]:
    """
    Group elements that are close to each other on the page.

    Args:
        extracted_data (List[Dict[str, Any]]): List of extracted elements from the PDF.
        proximity_threshold (float): Maximum vertical distance to consider elements as related.

    Returns:
        List[Dict[str, Any]]: List of grouped elements.
    """
    grouped_data = []
    current_group = []

    for item in extracted_data:
        if not current_group or item['metadata']['page'] != current_group[-1]['metadata']['page'] or \
                item['bbox'][1] - current_group[-1]['bbox'][3] > proximity_threshold:
            if current_group:
                grouped_data.append({
                    "type": "ElementGroup",
                    "content": current_group,
                    "metadata": {"page": current_group[0]['metadata']['page']}
                })
            current_group = [item]
        else:
            current_group.append(item)

    if current_group:
        grouped_data.append({
            "type": "ElementGroup",
            "content": current_group,
            "metadata": {"page": current_group[0]['metadata']['page']}
        })

    return grouped_data


def process_grouped_content(grouped_data: List[Dict[str, Any]], chunk_size: int = 1000, chunk_overlap: int = 200) -> \
        List[Dict[str, Any]]:
    """
    Process the grouped content using LlamaIndex for text chunking and prepare for analysis.

    Args:
        grouped_data (List[Dict[str, Any]]): List of grouped elements from the PDF.
        chunk_size (int): Size of text chunks for semantic chunking.
        chunk_overlap (int): Overlap between text chunks.

    Returns:
        List[Dict[str, Any]]: List of processed elements ready for analysis.
    """
    # text_splitter = TokenTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    parser = SimpleNodeParser(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    processed_data = []
    for group in grouped_data:
        group_text = ""
        group_elements = []

        for item in group['content']:
            if item['type'] == 'Text':
                group_text += item['content'] + "\n"
            group_elements.append(item)

        if group_text.strip():
            chunks = parser.get_nodes_from_documents([LlamaIndexDocument(page_content=group_text)])
            for chunk in chunks:
                processed_data.append({
                    "type": "ContentGroup",
                    "text_content": chunk.text,
                    "elements": group_elements,
                    "metadata": group['metadata']
                })
        else:
            processed_data.append({
                "type": "ContentGroup",
                "text_content": "",
                "elements": group_elements,
                "metadata": group['metadata']
            })

    return processed_data


from llama_index.multi_modal_llms.azure_openai import AzureOpenAIMultiModal

mm_llm = AzureOpenAIMultiModal(
    engine="tfg-gpt4o",
    azure_endpoint="https://tfgam-aze-eus-openai.openai.azure.com/",
    api_key="fad496d248804765991834c0933b8f26",
    api_version="2024-02-15-preview",
    temperature=0.4,
    model="gpt-4o",
    streaming=False,
)


def analyze_content(processed_data: List[Dict[str, Any]]) -> list[TextNode]:
    """
    Analyze the processed content using Claude AI.

    Args:
        processed_data (List[Dict[str, Any]]): List of processed elements from the PDF.

    Returns:
        List[Dict[str, Any]]: List of analyzed elements.
    """

    analyzed_data = []
    for item in processed_data:
        for element in item["elements"]:
            if element["type"] == "Image":
                image_doc = ImageDocument(image_path=element["content"])
                response = mm_llm.complete(prompt="Describe image as alt text, if it is a chart of graph, "
                                                  "be accurate in text describing relationships",
                                           image_documents=[image_doc]
                                           )

                text_node = TextNode(text=str(response), metadata={})
            elif element["type"] == "Text":
                text_node = TextNode(text=element["content"], metadata={})
            elif element["type"] == "Table":
                df = element["content"]
                description = f"Table  on page {item['metadata']['page']}: {df.shape[0]} rows, {df.shape[1]} columns. Columns: {', '.join(df.columns)}"
                metadata = {
                    "table_id": "table",
                    "page": item["metadata"]["page"],
                    "bbox": item["bbox"]
                }
                text_node = TextNode(text=description, metadata=metadata)
            else:
                text_node = TextNode(text="Table here", metadata={})
            analyzed_data.append(text_node)

    return analyzed_data


def multimodal_extraction_pymupdf_with_context(file_path: str, chunk_size: int = 1000, chunk_overlap: int = 200,
                                               proximity_threshold: float = 20.0) -> list[TextNode]:
    """
    Perform multi-modal extraction on a PDF document using PyMuPDF, maintaining context and order.

    Args:
        file_path (str): Path to the input PDF file.
        chunk_size (int): Size of text chunks for semantic chunking.
        chunk_overlap (int): Overlap between text chunks.
        proximity_threshold (float): Maximum vertical distance to consider elements as related.

    Returns:
        List[Dict[str, Any]]: List of extracted, grouped, and analyzed elements.
    """
    extracted_data = extract_pdf_content_with_context(file_path)
    grouped_data = group_elements_by_proximity(extracted_data, proximity_threshold)
    processed_data = process_grouped_content(grouped_data, chunk_size, chunk_overlap)
    analyzed_data = analyze_content(processed_data)
    return analyzed_data


def process_element(element: Element) -> Dict[str, Any]:
    """
    Process a single element and return a dictionary with its type, content, and metadata.
    """
    base_info = {
        "type": element.__class__.__name__,
        "metadata": element.metadata.to_dict()
    }

    if element.category == "Table":
        base_info["content"] = element.metadata.text_as_html
    elif element.category == "TableChunk":
        base_info["content"] = element.metadata.text_as_html
    elif element.category == "Image":
        base_info["content"] = element.metadata.image_path
    elif element.category == "Text":
        base_info["content"] = element.text
    elif element.category == "CompositeElement":
        base_info["content"] = [
            process_element(e) for e in element.metadata.orig_elements
        ]
    else:
        base_info["content"] = element.text
    return base_info


def get_loader(filename: str, file_content_type: str, file_path: str):
    file_ext = filename.split(".")[-1].lower()
    known_type = True

    known_source_ext = [
        "go",
        "py",
        "java",
        "sh",
        "bat",
        "ps1",
        "cmd",
        "js",
        "ts",
        "css",
        "cs",
        "sql",
        "log",
        "dart",
        "dockerfile",
        "conf",
        "bash",
        "svelte",
        "msg",
    ]

    if file_ext == "pdf":
        llama_reader = pymupdf4llm.LlamaMarkdownReader()
        llama_reader = pymupdf
        # docs = pymupdf4llm.to_markdown(file_path, write_images=True)
        folder_path = Path(file_path).parent
        folder_name = Path(file_path).stem + "_images"
        folder_path = folder_path / folder_name
        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)

        # markdown = pymupdf4llm.to_markdown(file_path, write_images=True, image_path=folder_path, table_strategy="all")
        # LlamaParse(result_type="markdown").load_data("")
        # node_parser = MarkdownElementNodeParser(llm=multi_modal_llm, num_workers=3)
        # node_parser.get_nodes_from_documents(docs)
        # node_parser.
        # docs = llama_reader.load_data(file_path, write_images=True, image_path=folder_path, table_strategy="all")
        # loader = PyPDFLoader(
        #     file_path, extract_images=app.state.config.PDF_EXTRACT_IMAGES
        # )

        extracted_data = extract_pdf_content_with_context(file_path)
        grouped_data = group_elements_by_proximity(extracted_data, 20.0)
        processed_data = process_grouped_content(grouped_data, 1024, 100)
        analyzed_data = analyze_content(processed_data)



        # return analyzed_data
        # raw_pdf_elements = partition_pdf(
        #     filename=file_path,
        #     # Unstructured Helpers
        #     extract_images_in_pdf=True,
        #     chunking_strategy="by_title",
        #     strategy="hi_res",
        #     infer_table_structure=True,
        #     hi_res_model_name="yolox",
        #     max_characters=4000,
        #     new_after_n_chars=3800,
        #     combine_text_under_n_chars=2000,
        #     extract_image_block_output_dir=folder_path.as_posix(),
        # )

        # extracted_data = [process_element(element) for element in raw_pdf_elements]

        # Step 3: Optionally use LlamaIndex for additional semantic chunking of text elements
        # text_splitter = TokenTextSplitter(chunk_size=1024, chunk_overlap=100)
        # parser = SimpleNodeParser.from_defaults(chunk_size=1024, chunk_overlap=100)

        # chunked_data = []
        # for item in extracted_data:
        #     if item["type"] == "Text":
        #         chunks = parser.get_nodes_from_documents([Document(text=item["content"])])
        #         for chunk in chunks:
        #             chunked_data.append({
        #                 "type": "TextChunk",
        #                 "content": chunk.text,
        #                 "metadata": item["metadata"]
        #             })
        #     else:
        #         chunked_data.append(item)

        # Step 4: Use Claude AI for multi-modal analysis

        # analyzed_data = []
        # for item in chunked_data:
        #     if item["type"] == "Image":
        #         response = multi_modal_llm.completions.create(
        #             prompt=f"Analyze the following image at path: {item['content']}",
        #             max_tokens_to_sample=1000
        #         )
        #         item["analysis"] = response.completion
        #     if item["type"] in ["Table", "TableChunk"]:
        #         response = multi_modal_llm.completions.create(
        #             prompt=f"Analyze the following {item['type']}:\n\n{item['content']}",
        #             max_tokens_to_sample=1000
        #         )
        #         item["analysis"] = response.completion
        #     elif item["type"] in ["Header", "NarrativeText", "Title", "FigureCaption"]:
        #         response = multi_modal_llm.completions.create(
        #             prompt=f"Analyze the following {item['type']}:\n\n{item['content']}",
        #             max_tokens_to_sample=1000
        #         )
        #         item["analysis"] = response.completion
        #     elif item["type"] == "CompositeElement":
        #         composite_content = "\n".join([
        #             f"{subitem['type']}: {subitem['content']}"
        #             for subitem in item["content"]
        #         ])
        #         response = multi_modal_llm.completions.create(
        #             prompt=f"Analyze the following composite element:\n\n{composite_content}",
        #             max_tokens_to_sample=1000
        #         )
        #         item["analysis"] = response.completion
        #
        #     analyzed_data.append(item)

    # elif file_ext in (["csv", "xml", "html", "html", "ppt", "md", "msg", "doc", "docx", "xls", "xlsx"]):
    #     reader = UnstructuredReader()
    #     docs = reader.load_data(Path(file_path))
    # # elif file_ext in known_source_ext or (
    # #         file_content_type and file_content_type.find("text/") >= 0
    # # ):
    # #     loader = Tex(file_path, autodetect_encoding=True)
    # else:
    #     # loader = TextLoader(file_path, autodetect_encoding=True)
    #     docs = None
    #     known_type = False
    #
    # return docs, known_type


# End point to process upload doc
@app.post("/doc")
def store_doc(
        collection_name: Optional[str] = Form(None),
        file: UploadFile = File(...),
        user=Depends(get_verified_user),
):
    log.info(f"file.content_type: {file.content_type}")
    try:
        unsanitized_filename = file.filename
        filename = os.path.basename(unsanitized_filename)

        file_path = f"{UPLOAD_DIR}/{filename}"

        contents = file.file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
            f.close()

        f = open(file_path, "rb")
        if collection_name == None:
            collection_name = calculate_sha256(f)[:63]
        f.close()

        loader, known_type = get_loader(filename, file.content_type, file_path)
        data = loader.load()

        try:
            result = store_data_in_vector_db(data, collection_name)

            if result:
                return {
                    "status": True,
                    "collection_name": collection_name,
                    "filename": filename,
                    "known_type": known_type,
                }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e,
            )
    except Exception as e:
        log.exception(e)
        if "No pandoc was found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.PANDOC_NOT_INSTALLED,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e),
            )


class ProcessDocForm(BaseModel):
    file_id: str
    collection_name: Optional[str] = None


# Endpoint to process message input document
@app.post("/process/doc")
def process_doc(
        form_data: ProcessDocForm,
        user=Depends(get_verified_user),
):
    try:
        file = Files.get_file_by_id(form_data.file_id)
        file_path = file.meta.get("path", f"{UPLOAD_DIR}/{file.filename}")

        f = open(file_path, "rb")

        collection_name = form_data.collection_name
        if collection_name == None:
            collection_name = calculate_sha256(f)[:63]
        f.close()

        docs, known_type = get_loader(
            file.filename, file.meta.get("content_type"), file_path
        )
        # data = loader.load()

        try:
            result = store_data_in_vector_db(docs, collection_name)

            if result:
                return {
                    "status": True,
                    "collection_name": collection_name,
                    "known_type": known_type,
                }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e,
            )
    except Exception as e:
        log.exception(e)
        if "No pandoc was found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.PANDOC_NOT_INSTALLED,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e),
            )


class TextRAGForm(BaseModel):
    name: str
    content: str
    collection_name: Optional[str] = None


@app.post("/text")
def store_text(
        form_data: TextRAGForm,
        user=Depends(get_verified_user),
):
    collection_name = form_data.collection_name
    if collection_name == None:
        collection_name = calculate_sha256_string(form_data.content)

    result = store_text_in_vector_db(
        form_data.content,
        metadata={"name": form_data.name, "created_by": user.id},
        collection_name=collection_name,
    )

    if result:
        return {"status": True, "collection_name": collection_name}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


@app.get("/scan")
def scan_docs_dir(user=Depends(get_data_admin)):
    for path in Path(DOCS_DIR).rglob("./**/*"):
        try:
            if path.is_file() and not path.name.startswith("."):
                tags = extract_folders_after_data_docs(path)
                filename = path.name
                file_content_type = mimetypes.guess_type(path)

                parts = path.as_posix().split('/')
                try:
                    docs_index = parts.index('docs')
                    group_name = parts[docs_index + 1]
                except (ValueError, IndexError):
                    group_name = "tfg"
                f = open(path, "rb")
                collection_name = calculate_sha256(f)[:63]
                f.close()

                docs, known_type = get_loader(
                    filename, file_content_type[0], str(path)
                )
                # data = loader.load()

                try:
                    result = store_data_in_vector_db(docs, collection_name)

                    if result:
                        sanitized_filename = sanitize_filename(filename)
                        doc = Documents.get_doc_by_name(sanitized_filename, user)
                        # doc = Documents.update_doc_content_by_name(form_data.name, {"tags": form_data.tags})
                        if doc == None:
                            doc = Documents.insert_new_doc(
                                user.id,
                                group_name,
                                DocumentForm(
                                    **{
                                        "name": sanitized_filename,
                                        "title": filename,
                                        "collection_name": collection_name,
                                        "filename": filename,
                                        "content": (
                                            json.dumps(
                                                {
                                                    "tags": list(
                                                        map(
                                                            lambda name: {"name": name},
                                                            tags,
                                                        )
                                                    )
                                                }
                                            )
                                            if len(tags)
                                            else "{}"
                                        ),
                                    }
                                ),
                            )
                except Exception as e:
                    log.exception(e)
                    pass

        except Exception as e:
            log.exception(e)

    return True


class SafeWebBaseLoader(WebBaseLoader):
    """WebBaseLoader with enhanced error handling for URLs."""

    def lazy_load(self) -> Iterator[Document]:
        """Lazy load text from the url(s) in web_path with error handling."""
        for path in self.web_paths:
            try:
                soup = self._scrape(path, bs_kwargs=self.bs_kwargs)
                text = soup.get_text(**self.bs_get_text_kwargs)

                # Build metadata
                metadata = {"source": path}
                if title := soup.find("title"):
                    metadata["title"] = title.get_text()
                if description := soup.find("meta", attrs={"name": "description"}):
                    metadata["description"] = description.get(
                        "content", "No description found."
                    )
                if html := soup.find("html"):
                    metadata["language"] = html.get("lang", "No language found.")

                yield Document(page_content=text, metadata=metadata)
            except Exception as e:
                # Log the error and continue with the next URL
                log.error(f"Error loading {path}: {e}")


if ENV == "dev":
    @app.get("/ef")
    async def get_embeddings():
        return {"result": app.state.EMBEDDING_FUNCTION("hello world")}


    @app.get("/ef/{text}")
    async def get_embeddings_text(text: str):
        return {"result": app.state.EMBEDDING_FUNCTION(text)}

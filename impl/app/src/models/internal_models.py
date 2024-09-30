from pydantic import BaseModel
from typing import Any

# This module contains the several Pydantic "models" for objects
# passed internally within the app, and not externally via web services.
# Chris Joakim, Microsoft


class OwlInfo(BaseModel):
    ontology_file: str
    owl: str
    error: str | None


class SparqlGenerationResult(BaseModel):
    completion_id: str
    completion_model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: dict | None
    elapsed: float
    sparql: str
    error: str | None


class RAGStrategy(BaseModel):
    natural_language: str
    strategy: str  # db_search, graph_search, or vector_search
    libtype: str | None
    libname: str | None
    tokens: Any

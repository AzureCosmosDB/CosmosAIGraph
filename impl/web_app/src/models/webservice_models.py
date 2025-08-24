from pydantic import BaseModel
from typing import Any

# This module contains the several Pydantic "models" that define both the
# request and response payloads for the web endpoints in this application.
# Think of these models as "interfaces" that define the "shapes" of actual
# objects.  Pydantic models are an interesting feature of the FastAPI
# webframework.  Using these models, FastAPI can automatically generate
# OpenAPI/Swagger request/response endpoint documentation.
#
# See the correspondig Graph Microservice JSON models in the
# impl/graph_app/src/main/java/com/microsoft/cosmosdb/caig/models/ directory.
#
# See https://fastapi.tiangolo.com/tutorial/response-model/
# See https://fastapi.tiangolo.com/tutorial/body/
#
# Chris Joakim, Microsoft, 2025
# Aleksey Savateyev, Microsoft, 2025


class PingModel(BaseModel):
    epoch: float


class LivenessModel(BaseModel):
    epoch: float
    alive: bool
    rows_read: int


class OwlInfoModel(BaseModel):
    ontology_file: str
    owl: str
    epoch: float
    error: str | None


class SparqlQueryRequestModel(BaseModel):
    sparql: str

    # Corresponding Java code
    # private String sparql;


class SparqlQueryResponseModel(BaseModel):
    sparql: str
    results: Any = None
    elapsed: int
    row_count: int
    error: str | None
    start_time: int
    finish_time: int

    # Corresponding Java code
    # private String sparql;
    # private Map<String, Object> results = new HashMap<>();
    # private long elapsed;
    # private String error;
    # private long start_time;
    # private long finish_time;


class SparqlBomQueryRequestModel(BaseModel):
    libname: str
    max_depth: int

    # Corresponding Java code
    # private String libname;
    # private int max_depth;


class SparqlBomQueryResponseModel(BaseModel):
    libname: str
    max_depth: int
    actual_depth: int
    libs: dict | None
    error: str | None
    elapsed: float
    request_time: float

    # Corresponding Java code
    # private String libname;
    # private int max_depth;
    # private int actual_depth;
    # private HashMap<String, TraversedLib> libs;
    # private String error;
    # private long elapsed;
    # private long request_time;


class SparqlGenerationRequestModel(BaseModel):
    session_id: str | None
    natural_language: str
    owl: str


class SparqlGenerationResponseModel(BaseModel):
    session_id: str | None
    natural_language: str
    completion_id: str
    completion_model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    epoch: int
    elapsed: float
    sparql: str
    error: str | None


class AiConvFeedbackModel(BaseModel):
    conversation_id: str
    feedback_last_question: str
    feedback_user_feedback: str


class DocumentsVSResultsModel(BaseModel):
    libtype: str
    libname: str
    count: int
    doc: dict | None
    results: list
    elapsed: float
    error: str | None


class VectorizeRequestModel(BaseModel):
    session_id: str | None
    text: str


class VectorizeResponseModel(BaseModel):
    session_id: str | None
    text: str
    embeddings: list
    elapsed: float
    error: str | None


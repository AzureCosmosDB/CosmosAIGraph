# This is the entry-point for this web application, built with the
# FastAPI web framework.
#
# This implementation contains several 'FS.write_json(...)' calls
# to write out JSON files to the 'tmp' directory for understanding
# and debugging purposes.
#
# Chris Joakim, Aleksey Savateyev
 
import asyncio
import json
import logging
import sys
import textwrap
import time
import traceback

import httpx

from contextlib import asynccontextmanager

from dotenv import load_dotenv

from fastapi import FastAPI, Request, Response, Form, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markdown import markdown
from jinja2 import Environment

# next three lines for authentication with MSAL
from fastapi import Depends
from starlette.middleware.sessions import SessionMiddleware

# Pydantic models defining the "shapes" of requests and responses
from src.models.webservice_models import PingModel
from src.models.webservice_models import LivenessModel
from src.models.webservice_models import AiConvFeedbackModel

# Services with Business Logic
from src.services.ai_completion import AiCompletion
from src.services.ai_conversation import AiConversation
from src.services.ai_service import AiService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.config_service import ConfigService
from src.services.entities_service import EntitiesService
from src.services.logging_level_service import LoggingLevelService
from src.services.ontology_service import OntologyService
from src.services.rag_data_service import RAGDataService
from src.services.rag_data_result import RAGDataResult
from src.util.fs import FS
from src.util.sparql_formatter import SparqlFormatter
from src.util.sparql_query_response import SparqlQueryResponse
from typing import Optional

import debugpy
import os

if os.getenv("CAIG_WAIT_FOR_DEBUGGER") is not None:
    # Allow other computers to attach to debugpy at this IP address and port.
    debugpy.listen(("0.0.0.0", 5678))

    logging.info("CAIG_WAIT_FOR_DEBUGGER: " + os.getenv("CAIG_WAIT_FOR_DEBUGGER"))
    # This will ensure that the debugger waits for you to attach before running the code.
    if os.getenv("CAIG_WAIT_FOR_DEBUGGER").lower() == "true":
        print("Waiting for debugger attach...")
        debugpy.wait_for_client()
        print("Debugger attached, starting FastAPI app...")


# standard initialization
load_dotenv(override=True)
logging.basicConfig(
    format="%(asctime)s - %(message)s", level=LoggingLevelService.get_level()
)

if sys.platform == "win32":
    logging.warning("Windows platform detected, setting WindowsSelectorEventLoopPolicy")
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    logging.warning(
        "platform is {}, not Windows.  Not setting event_loop_policy".format(
            sys.platform
        )
    )

ai_svc = AiService()
nosql_svc = CosmosNoSQLService()
rag_data_svc = RAGDataService(ai_svc, nosql_svc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Automated startup and shutdown logic for the FastAPI app.
    See https://fastapi.tiangolo.com/advanced/events/#lifespan
    """
    try:
        ConfigService.log_defined_env_vars()
        logging.error(
            "FastAPI lifespan - application_version: {}".format(
                ConfigService.application_version()
            )
        )
        await OntologyService.initialize()
        logging.info(
            "FastAPI lifespan - OntologyService initialized, ontology length: {}".format(
                len(OntologyService.get_owl_content()) if OntologyService.get_owl_content() is not None else 0)
            )
        
        # logging.error("owl:\n{}".format(OntologyService.get_owl_content()))
        await ai_svc.initialize()
        logging.error("FastAPI lifespan - AiService initialized")
        await nosql_svc.initialize()
        logging.error("FastAPI lifespan - CosmosNoSQLService initialized")
        await EntitiesService.initialize()
        logging.error(
            "FastAPI lifespan - EntitiesService initialized, libraries_count: {}".format(
                EntitiesService.libraries_count()
            )
        )
        logging.error("ConfigService.graph_service_url():  {}".format(ConfigService.graph_service_url()))
        logging.error("ConfigService.graph_service_port(): {}".format(ConfigService.graph_service_port()))                  
                    
    except Exception as e:
        logging.error("FastAPI lifespan exception: {}".format(str(e)))
        logging.error(traceback.format_exc())

    yield

    logging.info("FastAPI lifespan, shutting down...")
    await nosql_svc.close()
    logging.info("FastAPI lifespan, pool closed")

def markdown_filter(text):
    return markdown(text)

def tojson_pretty(value):
    return json.dumps(value, indent=2, ensure_ascii=False)

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
views = Jinja2Templates(directory="views")
views.env.filters['markdown'] = markdown_filter
views.env.filters['tojson'] = tojson_pretty

# Enable server-side session to persist conversation_id across posts
try:
    session_secret = os.getenv("CAIG_SESSION_SECRET") or "change-me-dev"
    app.add_middleware(SessionMiddleware, secret_key=session_secret)
except Exception as e:
    logging.warning("Session middleware not added: {}".format(str(e)))

# web service authentication with shared secrets
websvc_auth_header = ConfigService.websvc_auth_header()
websvc_auth_value = ConfigService.websvc_auth_value()
websvc_headers = dict()
websvc_headers["Content-Type"] = "application/json"
websvc_headers[websvc_auth_header] = websvc_auth_value
logging.debug(
    "webapp.py websvc_headers: {}".format(json.dumps(websvc_headers, sort_keys=False))
)
logging.error("webapp.py started")


@app.get("/ping")
async def get_ping() -> PingModel:
    resp = dict()
    resp["epoch"] = str(time.time())
    return resp


@app.get("/liveness")
async def get_liveness(req: Request, resp: Response) -> LivenessModel:
    """
    Return a LivenessModel indicating the health of this web app.
    This endpoint is invoked by the Azure Container Apps (ACA) service.
    The implementation validates the environment variable and url configuration.
    """
    alive = True
    if graph_microsvc_sparql_query_url().startswith("http"):
        alive = True
    else:
        alive = False  # unable to reach the graph service due to url config

    if alive == True:
        resp.status_code = status.HTTP_200_OK
    else:
        resp.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    liveness_data = dict()
    liveness_data["alive"] = alive
    liveness_data["rows_read"] = 0
    liveness_data["epoch"] = time.time()
    logging.info("liveness_check: {}".format(liveness_data))
    return liveness_data


@app.get("/")
async def get_home(req: Request):
    global nosql_svc
    # Use the same logic as conv_ai_console to make it the default page
    conv = None
    conversation_id = None
    
    # Check if there's an existing conversation in the session
    try:
        conversation_id = str(req.session.get("conversation_id") or "").strip()
        if conversation_id:
            logging.info("Found existing conversation_id in session: {}".format(conversation_id))
            # Try to load the existing conversation
            try:
                conv = await nosql_svc.load_conversation(conversation_id)
                if conv:
                    logging.info("Loaded existing conversation with {} completions".format(len(conv.completions)))
                else:
                    # Try file-based storage fallback
                    import os
                    import json
                    conv_file_path = f"tmp/conv_{conversation_id}.json"
                    if os.path.exists(conv_file_path):
                        with open(conv_file_path, 'r') as f:
                            conv_data = json.load(f)
                        conv = AiConversation()
                        conv.conversation_id = conversation_id
                        conv.completions = conv_data.get("completions", [])
                        logging.info("Loaded conversation from file with {} completions".format(len(conv.completions)))
            except Exception as e:
                logging.warning("Failed to load existing conversation: {}".format(e))
                conv = None
    except Exception:
        pass
    
    # If no existing conversation found or loading failed, create a new one
    if not conv:
        conv = AiConversation()
        logging.info(
            "get_home (/) - new conversation_id: {}".format(conv.conversation_id)
        )
        # Store the new conversation_id in session
        try:
            req.session["conversation_id"] = conv.conversation_id
        except Exception:
            pass
    
    view_data = dict()
    view_data["conv"] = conv.get_data()
    view_data["conversation_id"] = conv.conversation_id
    view_data["conversation_data"] = ""
    view_data["prompts_text"] = "no prompts yet"
    view_data["last_user_question"] = ""
    view_data["rag_strategy"] = "auto"
    view_data["current_page"] = "conv_ai_console"  # Set active page for navbar
    return views.TemplateResponse(
        request=req, name="conv_ai_console.html", context=view_data
    )


@app.get("/about")
async def get_about(req: Request):
    view_data = dict()
    view_data["application_version"] = ConfigService.application_version()
    view_data["application_build"] = ConfigService.application_build()
    view_data["graph_source"] = ConfigService.graph_source()
    view_data["graph_source_db"] = ConfigService.graph_source_db()
    view_data["graph_source_container"] = ConfigService.graph_source_container()
    view_data["current_page"] = "about"  # Set active page for navbar
    return views.TemplateResponse(request=req, name="about.html", context=view_data)


@app.get("/sparql_console")
async def get_sparql_console(req: Request):
    view_data = get_sparql_console_view_data()
    view_data["current_page"] = "sparql_console"  # Set active page for navbar
    return views.TemplateResponse(
        request=req, name="sparql_console.html", context=view_data
    )


@app.post("/sparql_console")
async def post_sparql_console(req: Request):
    form_data = await req.form()  # <class 'starlette.datastructures.FormData'>
    logging.info("/sparql_console form_data: {}".format(form_data))
    view_data = post_libraries_sparql_console(form_data)
    view_data["current_page"] = "sparql_console"  # Set active page for navbar
    
    if (LoggingLevelService.get_level() == logging.DEBUG):
        try:
            FS.write_json(view_data, "tmp/sparql_console_view_data.json")
        except Exception as e:
            pass
    return views.TemplateResponse(
        request=req, name="sparql_console.html", context=view_data
    )


@app.get("/gen_sparql_console")
async def get_ai_console(req: Request):
    view_data = gen_sparql_console_view_data()
    view_data["natural_language"] = ""
    view_data["sparql"] = "SELECT * WHERE { ?s ?p ?o . } LIMIT 10"
    view_data["current_page"] = "gen_sparql_console"  # Set active page for navbar
    return views.TemplateResponse(
        request=req, name="gen_sparql_console.html", context=view_data
    )


@app.post("/gen_sparql_console_generate_sparql")
async def ai_post_gen_sparql(req: Request):
    form_data = await req.form()
    logging.info("/gen_sparql_console_generate_sparql form_data: {}".format(form_data))
    natural_language = form_data.get("natural_language").strip()
    view_data = gen_sparql_console_view_data()
    view_data["natural_language"] = natural_language
    view_data["generating_nl"] = natural_language
    sparql: str = ""

    resp_obj = dict()
    resp_obj["session_id"] = (
        ""  # Note: not currently used, populate with the HTTP session ID
    )
    resp_obj["natural_language"] = natural_language
    resp_obj["owl"] = OntologyService.get_owl_content()
    resp_obj["completion_id"] = ""
    resp_obj["completion_model"] = ""
    resp_obj["prompt_tokens"] = -1
    resp_obj["completion_tokens"] = -1
    resp_obj["total_tokens"] = -1
    resp_obj["sparql"] = ""
    resp_obj["error"] = ""

    try:
        resp_obj = ai_svc.generate_sparql_from_user_prompt(resp_obj)
        sparql = resp_obj["sparql"]
        view_data["sparql"] = SparqlFormatter().pretty(sparql)
    except Exception as e:
        resp_obj["error"] = str(e)
        logging.critical((str(e)))
        logging.exception(e, stack_info=True, exc_info=True)

    view_data["results"] = resp_obj#json.dumps(resp_obj, sort_keys=False, indent=2)
    view_data["results_message"] = "Generative AI Response"
    view_data["current_page"] = "gen_sparql_console"  # Set active page for navbar
    return views.TemplateResponse(
        request=req, name="gen_sparql_console.html", context=view_data
    )


@app.post("/gen_sparql_console_execute_sparql")
async def gen_sparql_console_execute_sparql(req: Request):
    form_data = await req.form()
    logging.info("/gen_sparql_console_execute_sparql form_data: {}".format(form_data))
    view_data = gen_sparql_console_view_data()
    sparql = form_data.get("sparql")
    view_data["sparql"] = sparql
    # Prefer the actual textarea value if present, else fallback to generating_nl
    nl_val = form_data.get("natural_language")
    if nl_val is not None and len(nl_val.strip()) > 0:
        view_data["natural_language"] = nl_val
    else:
        view_data["natural_language"] = form_data.get("generating_nl")

    sqr: SparqlQueryResponse = post_sparql_query_to_graph_microsvc(sparql)

    if sqr.has_errors():
        view_data["results"] = dict()
        view_data["results_message"] = "SPARQL Query Error"
    else:
        view_data["results"] = sqr.response_obj#json.dumps(sqr.response_obj, sort_keys=False, indent=2)
        view_data["count"] = sqr.count
        view_data["results_message"] = "SPARQL Query Results"
    view_data["current_page"] = "gen_sparql_console"  # Set active page for navbar
    return views.TemplateResponse(
        request=req, name="gen_sparql_console.html", context=view_data
    )


@app.get("/vector_search_console")
async def get_vector_search_console(req: Request):
    view_data = vector_search_view_data()
    
    # Test session functionality
    req.session["test_session"] = "session_working"
    test_value = req.session.get("test_session")
    logging.info(f"Session test - stored: 'session_working', retrieved: '{test_value}'")
    
    # Debug: Log session contents
    logging.info(f"Session keys: {list(req.session.keys())}")
    logging.info(f"Full session contents: {dict(req.session)}")
    
    # Restore previous search data from session if available
    try:
        last_entrypoint = str(req.session.get("vector_search_entrypoint") or "").strip()
        if last_entrypoint:
            view_data["entrypoint"] = last_entrypoint
            logging.info(f"Restored entrypoint from session: {last_entrypoint}")
        else:
            logging.info("No entrypoint found in session")
            
        # Restore search method
        last_search_method = str(req.session.get("vector_search_method") or "vector").strip()
        view_data["search_method"] = last_search_method
        logging.info(f"Restored search method from session: {last_search_method}")
        
        # Restore search limit
        last_search_limit = req.session.get("vector_search_limit")
        if last_search_limit is not None:
            try:
                search_limit = int(last_search_limit)
                if 1 <= search_limit <= 100:  # Validate bounds
                    view_data["search_limit"] = search_limit
                    logging.info(f"Restored search limit from session: {search_limit}")
                else:
                    view_data["search_limit"] = 4  # Default if out of bounds
            except (ValueError, TypeError):
                view_data["search_limit"] = 4  # Default if invalid
        else:
            view_data["search_limit"] = 4  # Default if not found
            
        # Restore previous results if available
        last_results = req.session.get("vector_search_results")
        logging.info(f"Session results type: {type(last_results)}, value: {last_results}")
        
        if last_results is not None and len(last_results) > 0:
            view_data["results"] = last_results
            view_data["results_message"] = "Vector Search Results (from session)"
            logging.info(f"Restored {len(last_results)} results from session")
        else:
            logging.info("No results found in session or results are empty")
            
        # Restore previous embedding if available
        last_embedding = req.session.get("vector_search_embedding")
        last_embedding_message = req.session.get("vector_search_embedding_message")
        if last_embedding:
            view_data["embedding"] = last_embedding
            view_data["embedding_message"] = last_embedding_message or "Embedding (from session)"
            logging.info(f"Restored embedding from session")
        else:
            logging.info("No embedding found in session")
            
    except Exception as e:
        logging.error(f"Error restoring vector search session data: {e}")
        import traceback
        logging.error(traceback.format_exc())
    
    view_data["current_page"] = "vector_search_console"  # Set active page for navbar
    return views.TemplateResponse(
        request=req, name="vector_search_console.html", context=view_data
    )


@app.post("/vector_search_console")
async def post_vector_search_console(req: Request):
    global nosql_svc
    form_data = await req.form()
    logging.info("/vector_search_console form_data: {}".format(form_data))
    
    # Safely get entrypoint and search method from form data
    entrypoint_raw = form_data.get("entrypoint")
    if entrypoint_raw is None:
        entrypoint = ""
    else:
        entrypoint = str(entrypoint_raw).strip()
    
    search_method_raw = form_data.get("search_method")
    if search_method_raw is None:
        search_method = "vector"  # Default to vector search
    else:
        search_method = str(search_method_raw).strip()
    
    # Safely get search limit from form data
    search_limit_raw = form_data.get("search_limit")
    if search_limit_raw is None or str(search_limit_raw).strip() == "":
        search_limit = 4  # Default limit
    else:
        try:
            search_limit = int(str(search_limit_raw).strip())
            # Ensure limit is within reasonable bounds
            if search_limit < 1:
                search_limit = 1
            elif search_limit > 100:
                search_limit = 100
        except ValueError:
            search_limit = 4  # Default if invalid
    
    logging.debug("vector_search_console; entrypoint: {}, search_method: {}, limit: {}".format(entrypoint, search_method, search_limit))
    view_data = vector_search_view_data()
    view_data["entrypoint"] = entrypoint
    view_data["search_method"] = search_method
    view_data["search_limit"] = search_limit

    if entrypoint and entrypoint.startswith("text:"):
        text = entrypoint[5:]
        logging.info(f"post_vector_search_console; text: {text}")
        
        nosql_svc.set_db(ConfigService.graph_source_db())
        nosql_svc.set_container(ConfigService.graph_source_container())
        
        if search_method == "fulltext":
            # Full-text search only
            results_obj = await nosql_svc.vector_search(search_text=text, search_method="fulltext", limit=search_limit)
            view_data["results_message"] = "Full-text Search Results"
        elif search_method == "rrf":
            # RRF search - need both vector and text
            try:
                logging.info("vectorize: {}".format(text))
                ai_svc_resp = ai_svc.generate_embeddings(text)
                vector = ai_svc_resp.data[0].embedding
                view_data["embedding_message"] = "Embedding from Text"
                view_data["embedding"] = json.dumps(vector, sort_keys=False, indent=2)
                logging.warning(f"post_vector_search_console; vector: {vector}")
                
                results_obj = await nosql_svc.vector_search(embedding_value=vector, search_text=text, search_method="rrf", limit=search_limit)
                view_data["results_message"] = "RRF (Hybrid) Search Results"
            except Exception as e:
                logging.critical((str(e)))
                logging.exception(e, stack_info=True, exc_info=True)
                results_obj = list()
        else:
            # Vector search (default)
            try:
                logging.info("vectorize: {}".format(text))
                ai_svc_resp = ai_svc.generate_embeddings(text)
                vector = ai_svc_resp.data[0].embedding
                view_data["embedding_message"] = "Embedding from Text"
                view_data["embedding"] = json.dumps(vector, sort_keys=False, indent=2)
                logging.warning(f"post_vector_search_console; vector: {vector}")
                
                results_obj = await nosql_svc.vector_search(embedding_value=vector, search_method="vector", limit=search_limit)
                view_data["results_message"] = "Vector Search Results"
            except Exception as e:
                logging.critical((str(e)))
                logging.exception(e, stack_info=True, exc_info=True)
                results_obj = list()
                
    elif entrypoint:
        nosql_svc.set_db(ConfigService.graph_source_db())
        nosql_svc.set_container(ConfigService.graph_source_container())
        docs = await nosql_svc.get_documents_by_name([entrypoint])
        logging.debug("vector_search_console - docs count: {}".format(len(docs)))

        if len(docs) > 0:
            doc = docs[0]
            if search_method == "fulltext":
                # For entity search with fulltext, use the entity name as search text
                results_obj = await nosql_svc.vector_search(search_text=entrypoint, search_method="fulltext", limit=search_limit)
                view_data["results_message"] = "Full-text Search Results"
            elif search_method == "rrf":
                # For RRF with entity, use both embedding and entity name
                results_obj = await nosql_svc.vector_search(embedding_value=doc["embedding"], search_text=entrypoint, search_method="rrf", limit=search_limit)
                view_data["results_message"] = "RRF (Hybrid) Search Results"
            else:
                # Vector search (default)
                results_obj = await nosql_svc.vector_search(embedding_value=doc["embedding"], search_method="vector", limit=search_limit)
                view_data["results_message"] = "Vector Search Results"
        else:
            results_obj = list()
    else:
        # Empty entrypoint - return empty results
        results_obj = list()

    # Set default results message if not already set
    if "results_message" not in view_data:
        view_data["results_message"] = "Search Results"
    
    view_data["results"] = results_obj
    view_data["current_page"] = "vector_search_console"  # Set active page for navbar
    
    # Store search data in session for persistence between navigations
    try:
        req.session["vector_search_entrypoint"] = entrypoint
        req.session["vector_search_method"] = search_method
        req.session["vector_search_limit"] = search_limit
        
        # Convert results to JSON serializable format
        if results_obj:
            # Convert to list if it's not already, and ensure it's JSON serializable
            serializable_results = list(results_obj) if results_obj else []
            req.session["vector_search_results"] = serializable_results
        else:
            req.session["vector_search_results"] = []
            
        logging.info(f"Stored entrypoint '{entrypoint}', method '{search_method}', limit '{search_limit}', and {len(results_obj) if results_obj else 0} results in session")
        
        if "embedding" in view_data and view_data["embedding"]:
            req.session["vector_search_embedding"] = view_data["embedding"]
            req.session["vector_search_embedding_message"] = view_data["embedding_message"]
            logging.info(f"Stored embedding data in session")
        else:
            # Clear embedding data if not present
            req.session.pop("vector_search_embedding", None)
            req.session.pop("vector_search_embedding_message", None)
            
    except Exception as e:
        logging.error(f"Error storing vector search session data: {e}")
        import traceback
        logging.error(traceback.format_exc())
    
    return views.TemplateResponse(
        request=req, name="vector_search_console.html", context=view_data
    )


def vector_search_view_data():
    view_data = dict()
    view_data["entrypoint"] = ""
    view_data["search_method"] = "vector"  # Default to vector search
    view_data["results_message"] = ""
    view_data["results"] = {}
    view_data["embedding_message"] = ""
    view_data["embedding"] = ""
    return view_data


@app.get("/conv_ai_console")
async def conv_ai_console(req: Request):
    global nosql_svc
    conv = None
    conversation_id = None
    
    # Check if there's an existing conversation in the session
    try:
        conversation_id = str(req.session.get("conversation_id") or "").strip()
        if conversation_id:
            logging.info("Found existing conversation_id in session: {}".format(conversation_id))
            # Try to load the existing conversation
            try:
                conv = await nosql_svc.load_conversation(conversation_id)
                if conv:
                    logging.info("Loaded existing conversation with {} completions".format(len(conv.completions)))
                else:
                    # Try file-based storage fallback
                    import os
                    import json
                    conv_file_path = f"tmp/conv_{conversation_id}.json"
                    if os.path.exists(conv_file_path):
                        with open(conv_file_path, 'r') as f:
                            conv_data = json.load(f)
                        conv = AiConversation()
                        conv.conversation_id = conversation_id
                        conv.completions = conv_data.get("completions", [])
                        logging.info("Loaded conversation from file with {} completions".format(len(conv.completions)))
            except Exception as e:
                logging.warning("Failed to load existing conversation: {}".format(e))
                conv = None
    except Exception:
        pass
    
    # If no existing conversation found or loading failed, create a new one
    if not conv:
        conv = AiConversation()
        logging.info(
            "conv_ai_console - new conversation_id: {}".format(conv.conversation_id)
        )
        # Store the new conversation_id in session
        try:
            req.session["conversation_id"] = conv.conversation_id
        except Exception:
            pass
    
    view_data = dict()
    view_data["conv"] = conv.get_data()
    view_data["conversation_id"] = conv.conversation_id
    view_data["conversation_data"] = ""
    view_data["prompts_text"] = "no prompts yet"
    view_data["last_user_question"] = ""
    view_data["rag_strategy"] = "auto"
    view_data["current_page"] = "conv_ai_console"  # Set active page for navbar
    return views.TemplateResponse(
        request=req, name="conv_ai_console.html", context=view_data
    )


@app.post("/conv_ai_console")
async def conv_ai_console_post(req: Request):
    global ai_svc
    global nosql_svc
    global ontology_svc
    global rag_data_svc

    form_data = await req.form()
    logging.info("/conv_ai_console form_data: {}".format(form_data))
    conversation_id = str(form_data.get("conversation_id") or "").strip()
    if not conversation_id:
        try:
            conversation_id = str(req.session.get("conversation_id") or "").strip()
            logging.info("conversation_id restored from session: {}".format(conversation_id))
        except Exception:
            pass
    user_text = str(form_data.get("user_text") or "").strip()
    rag_strategy_choice = str(form_data.get("rag_strategy") or '').strip().lower()
    print(f"[DEBUG] conversation_id: {conversation_id}, user_text: {user_text}")
    logging.info(
        "conversation_id: {}, user_text: {}".format(conversation_id, user_text)
    )
    
    # Try database first, fall back to file-based storage if database fails
    import os
    import json
    
    conv_file_path = f"tmp/conv_{conversation_id}.json"
    conv = None
    use_file_storage = False
    
    # Try to load from database first
    try:
        conv = await nosql_svc.load_conversation(conversation_id)
        if conv:
            print(f"[DEBUG] LOADED FROM DATABASE: {len(conv.completions)} completions")
        else:
            print(f"[DEBUG] NO DATABASE RECORD found for conversation_id: {conversation_id}")
    except Exception as e:
        print(f"[DEBUG] DATABASE LOAD FAILED: {e}")
        logging.warning(f"Database load failed, falling back to file storage: {e}")
        use_file_storage = True
    
    # If database failed or returned None, try file-based storage
    if conv is None:
        if os.path.exists(conv_file_path):
            try:
                with open(conv_file_path, 'r') as f:
                    conv_data = json.load(f)
                conv = AiConversation(conv_data)
                print(f"[DEBUG] LOADED FROM FILE (fallback): {len(conv.completions)} completions")
                use_file_storage = True
            except Exception as e:
                print(f"[DEBUG] FILE LOAD ALSO FAILED: {e}")
                conv = None
        else:
            print(f"[DEBUG] NO FILE found either for conversation_id: {conversation_id}")
            use_file_storage = True  # Use file storage for new conversations if DB failed

    # DEBUGGING: Log completions immediately after loading
    if conv:
        print(f"[DEBUG] LOADED CONVERSATION: {len(conv.completions)} completions")
        logging.info(f"LOADED CONVERSATION: {len(conv.completions)} completions")
        for i, c in enumerate(conv.completions):
            print(f"[DEBUG]   Loaded completion {i}: Index={c.get('index')}, User={c.get('user_text')}")
            logging.info(f"  Loaded completion {i}: ID={c.get('completion_id')}, Index={c.get('index')}, User={c.get('user_text')}")
    else:
        print(f"[DEBUG] LOADED CONVERSATION: None (new conversation)")
        logging.info("LOADED CONVERSATION: None (new conversation)")

    if conv is None:
        conv = AiConversation()
        # Only set the id if provided; otherwise keep the generated one
        if conversation_id is not None and len(conversation_id) > 0:
            conv.set_conversation_id(conversation_id)
        logging.info("new conversation created")
    else:
        logging.info(
            "conversation loaded: {} {}".format(conversation_id, conv.serialize())
        )

    if len(user_text) > 0:
        # Always record the user's message first so each turn shows in order
        conv.add_user_message(user_text)
        prompt_text = ai_svc.generic_prompt_template()

        override = None if rag_strategy_choice in ("", "auto") else rag_strategy_choice
        rdr: RAGDataResult = await rag_data_svc.get_rag_data(user_text, 20, override)
        if (LoggingLevelService.get_level() == logging.DEBUG):
            FS.write_json(rdr.get_data(), "tmp/ai_conv_rdr.json")

        completion: Optional[AiCompletion] = AiCompletion(conv.conversation_id, None)
        completion.set_user_text(user_text)
        completion.set_rag_strategy(rdr.get_strategy())
        content_lines = list()

        # Prepare context based on RAG strategy
        context = ""
        completion_context = conv.last_completion_content()
        
        if rdr.has_db_rag_docs() == True:
            for doc in rdr.get_rag_docs():
                logging.debug("doc: {}".format(doc))
                line_parts = list()
                for attr in ["id", "fileName", "text"]:
                    if attr in doc.keys():
                        value = doc[attr].strip()
                        if len(value) > 0:
                            line_parts.append("{}: {}".format(attr, value))
                content_lines.append(".  ".join(line_parts))
            
            # For DB RAG, set the context but don't set completion content yet
            conv.set_context(rdr.get_context())
            rag_data = "\n".join(content_lines)
            
            if conv.has_context():
                context = "Found context: {}\n{}\n{}".format(
                    conv.get_context(), completion_context, rag_data
                )
            else:
                context = "{}\n{}".format(completion_context, rag_data)
                
            try:
                logging.info("conv save (db path) completions: {}".format(len(conv.get_data().get("completions", []))))
            except Exception:
                pass
                
        elif rdr.has_graph_rag_docs() == True:
            for doc in rdr.get_rag_docs():
                content_lines.append(json.dumps(doc))
            
            # For Graph RAG, set the context but don't set completion content yet
            graph_content = ", ".join(content_lines)
            conv.set_context(graph_content)
            conv.add_diagnostic_message("sparql: {}".format(rdr.get_sparql()))

            if conv.has_context():
                context = "Found context: {}\n{}\n".format(
                    conv.get_context(), completion_context
                )
            else:
                context = "{}\n".format(completion_context)
        else:
            # No specific RAG docs, use system prompt
            rag_data = rdr.as_system_prompt_text()

            if conv.has_context():
                context = "Found context: {}\n{}\n{}".format(
                    conv.get_context(), completion_context, rag_data
                )
            else:
                context = "{}\n{}".format(completion_context, rag_data)

        # Always run AI inference to generate the actual response
        max_tokens = ConfigService.invoke_kernel_max_tokens()
        temperature = ConfigService.invoke_kernel_temperature()
        top_p = ConfigService.invoke_kernel_top_p()
        comp_result = await ai_svc.invoke_kernel(
            conv,
            prompt_text,
            user_text,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )
        if comp_result is not None:
            completion = comp_result
            completion.set_rag_strategy(rdr.get_strategy())
        else:
            completion.set_content("No results found")

        # Add completion exactly once at the end
        conv.add_completion(completion)
        
        print(f"[DEBUG] AFTER ADD_COMPLETION: {len(conv.completions)} completions")
        # DEBUGGING: Log completions immediately after adding
        logging.info(f"AFTER ADD_COMPLETION: {len(conv.completions)} completions")
        for i, c in enumerate(conv.completions):
            print(f"[DEBUG]   After add completion {i}: Index={c.get('index')}, User={c.get('user_text')}")
            logging.info(f"  After add completion {i}: ID={c.get('completion_id')}, Index={c.get('index')}, User={c.get('user_text')}")
        
        # Save conversation - try database first, fall back to file if database fails
        save_success = False
        
        # Try database save first (unless we're already using file storage)
        if not use_file_storage:
            try:
                await nosql_svc.save_conversation(conv)
                print(f"[DEBUG] SAVED TO DATABASE: {len(conv.completions)} completions")
                logging.info(f"SAVED TO DATABASE: {len(conv.completions)} completions")
                save_success = True
            except Exception as e:
                print(f"[DEBUG] DATABASE SAVE FAILED: {e}")
                logging.warning(f"Database save failed, falling back to file storage: {e}")
                use_file_storage = True
        
        # If database save failed or we're using file storage, save to file
        if not save_success or use_file_storage:
            try:
                with open(conv_file_path, 'w') as f:
                    json.dump(conv.get_data(), f, indent=2)
                print(f"[DEBUG] SAVED TO FILE: {len(conv.completions)} completions")
                logging.info(f"SAVED TO FILE: {len(conv.completions)} completions")
                save_success = True
            except Exception as e:
                print(f"[DEBUG] FILE SAVE ALSO FAILED: {e}")
                logging.error(f"Both database and file save failed: {e}")
        
        if not save_success:
            logging.error("CRITICAL: Conversation could not be saved to either database or file!")

        # DEBUGGING: Log completions immediately after save
        storage_type = "DATABASE" if not use_file_storage else "FILE"
        print(f"[DEBUG] AFTER SAVE_CONVERSATION ({storage_type}): {len(conv.completions)} completions")
        logging.info(f"AFTER SAVE_CONVERSATION ({storage_type}): {len(conv.completions)} completions")
        for i, c in enumerate(conv.completions):
            print(f"[DEBUG]   After save completion {i}: Index={c.get('index')}, User={c.get('user_text')}")
            logging.info(f"  After save completion {i}: ID={c.get('completion_id')}, Index={c.get('index')}, User={c.get('user_text')}")

        logging.info(f"Completions after add_completion: {len(conv.completions)}")
        save_method = "database" if not use_file_storage else "file"
        logging.info(f"Conversation saved successfully using {save_method} storage.")

    #textformat_conversation(conv)
    # Disable optional reload to prevent issues with conversation state
    # The in-memory conversation should be the source of truth after save
    logging.info(f"Final conversation has {len(conv.get_data().get('completions', []))} completions")

    if (LoggingLevelService.get_level() == logging.DEBUG):
        FS.write_json(conv.get_data(), "tmp/ai_conv_{}.json".format(
            conv.get_message_count()))

    view_data = dict()
    # Backfill indices for stable ordering in the UI
    try:
        conv.ensure_indices()
    except Exception:
        pass
    view_data["conv"] = conv.get_data()
    view_data["conversation_id"] = conv.conversation_id
    
    # DEBUGGING: Log completions before rendering template
    completions_data = conv.get_data().get("completions", [])
    logging.info(f"BEFORE TEMPLATE RENDER: {len(completions_data)} completions")
    for i, c in enumerate(completions_data):
        logging.info(f"  Template completion {i}: ID={c.get('completion_id')}, Index={c.get('index')}, User={c.get('user_text')}")
    
    try:
        req.session["conversation_id"] = conv.conversation_id
    except Exception:
        pass
    view_data["conversation_data"] = conv.serialize()
    view_data["prompts_text"] = conv.formatted_prompts_text()
    view_data["last_user_question"] = conv.get_last_user_message()
    view_data["rag_strategy"] = rag_strategy_choice or (rdr.get_strategy() if 'rdr' in locals() and rdr else "auto")
    view_data["current_page"] = "conv_ai_console"  # Set active page for navbar
    
    # Debugging: Log the state of completions before rendering the template
    logging.debug("Final completions before rendering: {}".format(conv.get_data().get("completions", [])))
    # Debugging: Log the final state of completions before rendering the template
    logging.debug("Final state of completions before rendering:")
    for c in conv.get_data().get("completions", []):
        logging.debug(f"Completion ID: {c.get('completion_id')}, Index: {c.get('index')}, Content: {c.get('content')}")

    return views.TemplateResponse(
        request=req, name="conv_ai_console.html", context=view_data
    )


@app.post("/conv_ai_feedback")
async def post_sparql_query(
    req_model: AiConvFeedbackModel,
) -> AiConvFeedbackModel:
    global nosql_svc
    conversation_id = req_model.conversation_id
    feedback_last_question = req_model.feedback_last_question
    feedback_user_feedback = req_model.feedback_user_feedback
    logging.info("/conv_ai_feedback conversation_id: {}".format(conversation_id))
    logging.info(
        "/conv_ai_feedback feedback_last_question: {}".format(feedback_last_question)
    )
    logging.info(
        "/conv_ai_feedback feedback_user_feedback: {}".format(feedback_user_feedback)
    )
    await nosql_svc.save_feedback(req_model)
    return req_model


@app.post("/clear_session")
async def clear_session(request: Request):
    """
    Clear server-side session; optionally delete a conversation document.
    Frontend may pass: { "conversation_id": "<id>", "ignore_missing": true }
    """
    global nosql_svc
    
    # Get current conversation_id from session before clearing
    conversation_id = None
    try:
        conversation_id = str(request.session.get("conversation_id") or "").strip()
    except Exception:
        pass
    
    # Attempt to parse JSON payload
    try:
        payload = await request.json()
    except Exception:
        payload = {}
        
    conv_id = (payload.get("conversation_id") or "").strip() or None
    ignore_missing = bool(payload.get("ignore_missing"))

    # Example: remove server-side stored conversation id (if using session)
    try:
        request.session.pop("conversation_id", None)
    except Exception:
        pass

    delete_status = "skipped"
    if conv_id:
        try:
            # Assuming conversations_container already initialized
            conversations_container.delete_item(item=conv_id, partition_key=conv_id)
            delete_status = "deleted"
        except CosmosResourceNotFoundError:
            if ignore_missing:
                delete_status = "not_found_ignored"
            else:
                delete_status = "not_found"
        except Exception as e:
            # Log and continue to return success flag=false
            logging.warning("Unexpected error deleting conversation %s: %s", conv_id, e)
            return JSONResponse({"success": False, "delete_status": "error", "error": str(e)})

    # Optionally clear any other in-memory caches here
    return JSONResponse({"success": True, "delete_status": delete_status})


@app.post("/api/save_ontology")
async def save_ontology(request: Request):
    data = await request.json()
    content = data.get("content", "")
    path = os.environ.get("CAIG_GRAPH_SOURCE_OWL_FILENAME")
    if not path:
        return JSONResponse({"success": False, "error": "Ontology path not configured."})
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


def gen_sparql_console_view_data():
    view_data = dict()
    view_data["natural_language"] = "What is the total count of nodes?"
    view_data["sparql"] = ""
    view_data["owl"] = OntologyService.get_owl_content()
    view_data["results_message"] = ""
    view_data["results"] = ""
    view_data["generating_nl"] = ""
    view_data["count"] = ""
    return view_data


def graph_microsvc_sparql_query_url():
    return "{}:{}/sparql_query".format(
        ConfigService.graph_service_url(), ConfigService.graph_service_port()
    )


def graph_microsvc_bom_query_url():
    return "{}:{}/sparql_bom_query".format(
        ConfigService.graph_service_url(), ConfigService.graph_service_port()
    )


def get_sparql_console_view_data() -> dict:
    """Return the view data for the libraries SPARQL console"""
    sparql = """SELECT * WHERE { ?s ?p ?o . } LIMIT 10"""
    view_data = dict()
    view_data["method"] = "get"
    view_data["sparql"] = sparql
    view_data["bom_query"] = ""
    view_data["results_message"] = ""
    view_data["results"] = {}
    view_data["visualization_message"] = ""
    view_data["bom_json_str"] = "{}"
    view_data["inline_bom_json"] = "{}"
    view_data["libtype"] = ""
    return view_data


def filter_numeric_nodes(bom_obj):
    """
    Filter out nodes that are purely numeric values, GUIDs, or other technical identifiers.
    These are likely properties/attributes rather than actual meaningful graph entities.
    """
    if not isinstance(bom_obj, dict) or "nodes" not in bom_obj:
        return bom_obj
    
    def is_technical_identifier(name):
        """Check if a node name represents a technical value that should be filtered out"""
        if not isinstance(name, str):
            return False
        
        name = name.strip()
        
        # Skip empty names
        if not name:
            return True
            
        # Check if it's a pure decimal number (like "1600.0", "0.28575", "301.0")
        try:
            float(name)
            return True
        except ValueError:
            pass
        
        # Check if it's a GUID/UUID (like "11AF48DE79124AED8210C92F7EF8DF36")
        # These are technical identifiers, not meaningful entities for visualization
        if len(name) >= 32 and all(c in '0123456789ABCDEFabcdef' for c in name):
            return True
            
        # Check if it's mostly numeric with minimal text (measurement values)
        if len(name) <= 15:  # Short strings that might be measurements
            numeric_chars = sum(1 for c in name if c.isdigit() or c in '.-')
            if numeric_chars / len(name) > 0.6:  # More than 60% numeric characters
                return True
        
        # Check for URI fragments that start with schema references
        if name.startswith("http://") or name.startswith("https://"):
            return True
            
        return False
    
    def is_meaningful_entity(name, node_data):
        """Determine if a node represents a meaningful engineering entity"""
        if not isinstance(name, str):
            return False
            
        name = name.strip()
        
        # Keep well-formed equipment tags (like "1011-VES-301")
        if "-" in name and len(name) > 5:
            return True
            
        # Keep descriptive names with spaces
        if " " in name and len(name) > 10:
            return True
            
        # Keep file paths (engineering drawings, symbols)
        if "\\" in name or "/" in name:
            return True
            
        # Keep short meaningful codes (like "VES", "Equipment")
        if len(name) <= 15 and name.isalpha():
            return True
            
        # Reject technical identifiers
        if is_technical_identifier(name):
            return False
            
        return True
    
    def should_keep_node(name, node_data):
        """Determine if a node should be kept in the graph"""
        # First check if it's a meaningful entity
        if not is_meaningful_entity(name, node_data):
            return False
            
        # Additional check: nodes with no dependencies and short names are likely values
        if isinstance(node_data, dict):
            dependencies = node_data.get("dependencies", [])
            if not dependencies and len(name) < 5:
                return False
                
        return True
    
    # Create filtered copy of the BOM object
    filtered_bom_obj = {
        key: value for key, value in bom_obj.items() 
        if key != "nodes"
    }
    
    # Filter the nodes
    filtered_nodes = {}
    original_nodes = bom_obj.get("nodes", {})
    
    # First pass: determine which nodes to keep
    nodes_to_keep = set()
    for node_name, node_data in original_nodes.items():
        if should_keep_node(node_name, node_data):
            nodes_to_keep.add(node_name)
    
    # Second pass: create filtered nodes with cleaned dependencies
    for node_name, node_data in original_nodes.items():
        if node_name in nodes_to_keep:
            # Filter the dependencies to only include meaningful entities
            if isinstance(node_data, dict) and "dependencies" in node_data:
                filtered_dependencies = [
                    dep for dep in node_data["dependencies"] 
                    if is_meaningful_entity(dep, {}) and not is_technical_identifier(dep)
                ]
                
                # Create a copy of node_data with filtered dependencies
                filtered_node_data = node_data.copy()
                filtered_node_data["dependencies"] = filtered_dependencies
                filtered_nodes[node_name] = filtered_node_data
            else:
                filtered_nodes[node_name] = node_data
    
    filtered_bom_obj["nodes"] = filtered_nodes
    return filtered_bom_obj


def post_libraries_sparql_console(form_data):
    global websvc_headers

    sparql = form_data.get("sparql").strip()
    bom_query = form_data.get("bom_query").strip()
    logging.info("sparql: {}".format(sparql))
    logging.info("bom_query: {}".format(bom_query))

    view_data = dict()
    view_data["method"] = "post"
    view_data["sparql"] = sparql
    view_data["bom_query"] = bom_query
    view_data["results_message"] = "Results"
    view_data["results"] = {}
    view_data["visualization_message"] = ""
    view_data["bom_json_str"] = "{}"
    view_data["inline_bom_json"] = "{}"
    view_data["libtype"] = ""
    if sparql == "count":
        view_data["sparql"] = (
            "SELECT (COUNT(?s) AS ?triples) WHERE { ?s ?p ?o } LIMIT 10"
        )
    elif sparql == "triples":
        view_data["sparql"] = "SELECT * WHERE { ?s ?p ?o . } LIMIT 10"
    else:
        # execute either a BOM query or a simple SPARQL query, per Form input
        if len(bom_query) > 0:
            tokens = bom_query.split()
            if len(tokens) > 1:
                bom_obj = None
                url = graph_microsvc_bom_query_url()
                logging.info("url: {}".format(url))
                postdata = dict()
                postdata["entrypoint"] = tokens[0]
                postdata["max_depth"] = tokens[1]
                logging.info("postdata: {}".format(postdata))
                r = httpx.post(
                    url,
                    headers=websvc_headers,
                    content=json.dumps(postdata),
                    timeout=120.0,
                )
                bom_obj = json.loads(r.text)
                
                # Filter out numeric nodes that are likely measurement values
                filtered_bom_obj = filter_numeric_nodes(bom_obj)
                
                view_data["results"] = filtered_bom_obj
                view_data["inline_bom_json"] = view_data["results"]
                view_data["visualization_message"] = "Graph Visualization"
                # Derive a count for the header if possible
                try:
                    count_val = 0
                    if isinstance(filtered_bom_obj, dict):
                        # Prefer 'nodes' map count (new format)
                        if "nodes" in filtered_bom_obj and isinstance(filtered_bom_obj["nodes"], dict):
                            count_val = len(filtered_bom_obj["nodes"].keys())
                        # Legacy 'libs' map count
                        elif "libs" in filtered_bom_obj and isinstance(filtered_bom_obj["libs"], dict):
                            count_val = len(filtered_bom_obj["libs"].keys())
                        # Fallbacks: actual_depth/max_depth don't reflect rows, skip
                    view_data["count"] = count_val
                except Exception:
                    # Don't break UI if counting fails
                    view_data["count"] = 0
                if (LoggingLevelService.get_level() == logging.DEBUG):
                    try:
                        FS.write_json(
                            view_data["inline_bom_json"], "tmp/inline_bom.json"
                        )
                    except Exception as e:
                        pass
            else:
                view_data["results"] = "Invalid BOM query: {}".format(bom_query)
        else:
            sqr: SparqlQueryResponse = post_sparql_query_to_graph_microsvc(sparql)
            if sqr.has_errors():
                view_data["results"] = dict()
                view_data["results_message"] = "SPARQL Query Error"
            else:
                view_data["results"] = sqr.response_obj# json.dumps(
                #     sqr.response_obj, sort_keys=False, indent=2
                # )
                view_data["count"] = sqr.count
                view_data["results_message"] = "SPARQL Query Results"
    return view_data


def post_sparql_query_to_graph_microsvc(sparql: str) -> SparqlQueryResponse:
    """
    Execute a HTTP POST to the graph microservice with the given SPARQL query.
    Return the HTTP response JSON object.
    """
    global websvc_headers
    try:
        url = graph_microsvc_sparql_query_url()
        postdata = dict()
        postdata["sparql"] = sparql
        r = httpx.post(
            url, headers=websvc_headers, content=json.dumps(postdata), timeout=120.0
        )
        resp_obj = json.loads(r.text)
        print(
            "POST SPARQL RESPONSE:\n" + json.dumps(resp_obj, sort_keys=False, indent=2)
        )
        sqr = SparqlQueryResponse(r)
        sqr.parse()
        return sqr
    except Exception as e:
        logging.critical((str(e)))
        logging.exception(e, stack_info=True, exc_info=True)
        sqr = SparqlQueryResponse(None)
        sqr.parse()
        return sqr


def textformat_conversation(conv: AiConversation) -> None:
    """
    do an in-place reformatting of the conversation text, such as completion content
    """
    try:
        for comp in conv.completions:
            if "content" in comp.keys():
                content = comp["content"]
                if content is not None and len(content) > 0:
                    stripped = content.strip()
                    if stripped.startswith("{") and stripped.endswith("}"):
                        obj = json.loads(stripped)
                        comp["content"] = json.dumps(
                            obj, sort_keys=False, indent=2
                        ).replace("\n", "")
                    elif stripped.startswith("[") and stripped.endswith("]"):
                        obj = json.loads(stripped)
                        comp["content"] = json.dumps(
                            obj, sort_keys=False, indent=2
                        ).replace("\n", "")
                    else:
                        content_lines = list()
                        wrapped_lines = textwrap.wrap(stripped, width=80)
                        for line in wrapped_lines:
                            content_lines.append(line)
                        comp["content"] = "\n".join(content_lines)
    except Exception as e:
        logging.critical((str(e)))
        logging.exception(e, stack_info=True, exc_info=True)

from azure.cosmos.exceptions import CosmosResourceNotFoundError
import os
from fastapi import Request
from fastapi.responses import JSONResponse

@app.post("/api/save_ontology")
async def save_ontology(request: Request):
    data = await request.json()
    content = data.get("content", "")
    path = os.environ.get("CAIG_GRAPH_SOURCE_OWL_FILENAME")
    if not path:
        return JSONResponse({"success": False, "error": "Ontology path not configured."})
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

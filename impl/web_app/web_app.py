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
    return views.TemplateResponse(
        request=req, name="gen_sparql_console.html", context=view_data
    )


@app.get("/vector_search_console")
async def get_vector_search_console(req: Request):
    view_data = vector_search_view_data()
    view_data["current_page"] = "vector_search_console"  # Set active page for navbar
    return views.TemplateResponse(
        request=req, name="vector_search_console.html", context=view_data
    )


@app.post("/vector_search_console")
async def post_vector_search_console(req: Request):
    global nosql_svc
    form_data = await req.form()
    logging.info("/vector_search_console form_data: {}".format(form_data))
    entrypoint = form_data.get("entrypoint").strip()
    logging.debug("vector_search_console; entrypoint: {}".format(entrypoint))
    view_data = vector_search_view_data()
    view_data["entrypoint"] = entrypoint

    if entrypoint.startswith("text:"):
        text = entrypoint[5:]
        logging.info(f"post_vector_search_console; text: {text}")
        try:
            logging.info("vectorize: {}".format(text))
            ai_svc_resp = ai_svc.generate_embeddings(text)
            vector = ai_svc_resp.data[0].embedding
            view_data["embedding_message"] = "Embedding from Text"
            view_data["embedding"] = json.dumps(vector, sort_keys=False, indent=2)
            logging.warning(f"post_vector_search_console; vector: {vector}")
        except Exception as e:
            logging.critical((str(e)))
            logging.exception(e, stack_info=True, exc_info=True)

        nosql_svc.set_db(ConfigService.graph_source_db())
        nosql_svc.set_container(ConfigService.graph_source_container())
        results_obj = await nosql_svc.vector_search(vector)
    else:
        nosql_svc.set_db(ConfigService.graph_source_db())
        nosql_svc.set_container(ConfigService.graph_source_container())
        docs = await nosql_svc.get_documents_by_name([entrypoint])
        logging.debug("vector_search_console - docs count: {}".format(len(docs)))
        #logging.debug("vector_search_console - docs: {}".format(json.dumps(docs)))

        if len(docs) > 0:
            doc = docs[0]
            nosql_svc.set_db(ConfigService.graph_source_db())
            nosql_svc.set_container(ConfigService.graph_source_container())
            results_obj = await nosql_svc.vector_search(doc["embedding"])
        else:
            results_obj = list()

    view_data["results_message"] = "Vector Search Results"
    view_data["results"] = results_obj#json.dumps(results_obj, sort_keys=False, indent=2)
    return views.TemplateResponse(
        request=req, name="vector_search_console.html", context=view_data
    )


def vector_search_view_data():
    view_data = dict()
    view_data["entrypoint"] = ""
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
                view_data["results"] = bom_obj#json.dumps(bom_obj, sort_keys=False, indent=2)
                view_data["inline_bom_json"] = view_data["results"]
                view_data["visualization_message"] = "Graph Visualization"
                # Derive a count for the header if possible
                try:
                    count_val = 0
                    if isinstance(bom_obj, dict):
                        # Prefer 'nodes' map count (new format)
                        if "nodes" in bom_obj and isinstance(bom_obj["nodes"], dict):
                            count_val = len(bom_obj["nodes"].keys())
                        # Legacy 'libs' map count
                        elif "libs" in bom_obj and isinstance(bom_obj["libs"], dict):
                            count_val = len(bom_obj["libs"].keys())
                        # Fallbacks: actual_depth/max_depth don't reflect rows, skip
                    view_data["count"] = count_val
                except Exception:
                    # Don't break UI if counting fails
                    view_data["count"] = 0
                if (LoggingLevelService.get_level() == logging.DEBUG):
                    try:
                        FS.write_json(
                            json.loads(view_data["inline_bom_json"]), "tmp/inline_bom.json"
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

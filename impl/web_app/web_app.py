# This is the entry-point for this web application, built with the
# FastAPI web framework.
#
# This implementation contains several 'FS.write_json(...)' calls
# to write out JSON files to the 'tmp' directory for understanding
# and debugging purposes.
#
# Chris Joakim, Microsoft, 2025
# Aleksey Savateyev, 2025
 
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


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
views = Jinja2Templates(directory="views")

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
    view_data = dict()
    return views.TemplateResponse(request=req, name="home.html", context=view_data)


@app.get("/about")
async def get_about(req: Request):
    view_data = dict()
    view_data["application_version"] = ConfigService.application_version()
    view_data["graph_source"] = ConfigService.graph_source()
    view_data["graph_source_db"] = ConfigService.graph_source_db()
    view_data["graph_source_container"] = ConfigService.graph_source_container()
    return views.TemplateResponse(request=req, name="about.html", context=view_data)


@app.get("/sparql_console")
async def get_sparql_console(req: Request):
    view_data = get_sparql_console_view_data()
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

    view_data["results"] = json.dumps(resp_obj, sort_keys=False, indent=2)
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
    view_data["natural_language"] = form_data.get("generating_nl")

    sqr: SparqlQueryResponse = post_sparql_query_to_graph_microsvc(sparql)

    if sqr.has_errors():
        view_data["results"] = dict()
        view_data["results_message"] = "SPARQL Query Error"
    else:
        view_data["results"] = json.dumps(sqr.response_obj, sort_keys=False, indent=2)
        view_data["count"] = sqr.count
        view_data["results_message"] = "SPARQL Query Results"
    return views.TemplateResponse(
        request=req, name="gen_sparql_console.html", context=view_data
    )


@app.get("/vector_search_console")
async def get_vector_search_console(req: Request):
    view_data = vector_search_view_data()
    return views.TemplateResponse(
        request=req, name="vector_search_console.html", context=view_data
    )


@app.post("/vector_search_console")
async def post_vector_search_console(req: Request):
    global nosql_svc
    form_data = await req.form()
    logging.info("/vector_search_console form_data: {}".format(form_data))
    libname = form_data.get("libname").strip()
    logging.debug("vector_search_console; libname: {}".format(libname))
    view_data = vector_search_view_data()
    view_data["libname"] = libname

    if libname.startswith("text:"):
        text = libname[5:]
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
        docs = await nosql_svc.get_documents_by_name([libname])
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
    view_data["results"] = json.dumps(results_obj, sort_keys=False, indent=2)
    return views.TemplateResponse(
        request=req, name="vector_search_console.html", context=view_data
    )


def vector_search_view_data():
    view_data = dict()
    view_data["libname"] = ""
    view_data["results_message"] = ""
    view_data["results"] = ""
    view_data["embedding_message"] = ""
    view_data["embedding"] = ""
    return view_data


@app.get("/conv_ai_console")
async def conv_ai_console(req: Request):
    conv = AiConversation()
    logging.info(
        "conv_ai_console - new conversation_id: {}".format(conv.conversation_id)
    )
    view_data = dict()
    view_data["conv"] = conv
    view_data["conversation_id"] = conv.conversation_id
    view_data["conversation_data"] = ""
    view_data["prompts_text"] = "no prompts yet"
    view_data["last_user_question"] = ""
    return views.TemplateResponse(
        request=req, name="conv_ai_console.html", context=view_data
    )


@app.post("/conv_ai_console")
async def conv_ai_console(req: Request):
    global ai_svc
    global nosql_svc
    global ontology_svc
    global rag_data_svc

    form_data = await req.form()
    logging.info("/conv_ai_console form_data: {}".format(form_data))
    conversation_id = form_data.get("conversation_id").strip()
    user_text = form_data.get("user_text").strip()
    logging.info(
        "conversation_id: {}, user_text: {}".format(conversation_id, user_text)
    )
    conv = await nosql_svc.load_conversation(conversation_id)

    if conv is None:
        conv = AiConversation()
        conv.set_conversation_id(conversation_id)
        await nosql_svc.save_conversation(conv)
        logging.info("new conversation saved: {}".format(conversation_id))
    else:
        logging.info(
            "conversation loaded: {} {}".format(conversation_id, conv.serialize())
        )

    if len(user_text) > 0:
        
        prompt_text = ai_svc.generic_prompt_template()

        rdr: RAGDataResult = await rag_data_svc.get_rag_data(user_text, 20)
        if (LoggingLevelService.get_level() == logging.DEBUG):
            FS.write_json(rdr.get_data(), "tmp/ai_conv_rdr.json")

        completion: Optional[AiCompletion] = AiCompletion(conv.conversation_id, None)
        completion.set_user_text(user_text)
        completion.set_rag_strategy(rdr.get_strategy())
        content_lines = list()
        
        if rdr.has_db_rag_docs() == True:
            conv.add_user_message(user_text)
            for doc in rdr.get_rag_docs():
                logging.debug("doc: {}".format(doc))
                line_parts = list()
                for attr in ["id", "fileName", "text"]:
                    if attr in doc.keys():
                        value = doc[attr].strip()
                        if len(value) > 0:
                            line_parts.append("{}: {}".format(attr, value))
                content_lines.append(".  ".join(line_parts))
            completion.set_content("\n".join(content_lines))
            conv.add_completion(completion)
            conv.set_context(rdr.get_context())
            await nosql_svc.save_conversation(conv)
        else:
            context = ""
            completion_context = conv.last_completion_content()
            if rdr.has_graph_rag_docs() == True:
                for doc in rdr.get_rag_docs():
                    content_lines.append(json.dumps(doc))
                completion.set_content(", ".join(content_lines))
                #conv.add_completion(completion)
                conv.set_context(completion.get_content())
                conv.add_diagnostic_message("sparql: {}".format(rdr.get_sparql()))

                if conv.has_context():
                    context = "Found context: {}\n{}\n".format(
                        conv.get_context(), completion_context
                    )
                else:
                    context = "{}\n".format(completion_context)
                    
                #await nosql_svc.save_conversation(conv)
            else:
                rag_data = rdr.as_system_prompt_text()

                if conv.has_context():
                    context = "Found context: {}\n{}\n{}".format(
                        conv.get_context(), completion_context, rag_data
                    )
                else:
                    context = "{}\n{}".format(completion_context, rag_data)

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
                #conv.add_completion(completion)         
            else: 
                completion.set_content("No results found")
                
            #await nosql_svc.save_conversation(conv)

    #textformat_conversation(conv)
    if (LoggingLevelService.get_level() == logging.DEBUG):
        FS.write_json(conv.get_data(), "tmp/ai_conv_{}.json".format(
            conv.get_message_count()))

    view_data = dict()
    view_data["conv"] = conv
    view_data["conversation_id"] = conv.conversation_id
    view_data["conversation_data"] = conv.serialize()
    view_data["prompts_text"] = conv.formatted_prompts_text()
    view_data["last_user_question"] = conv.get_last_user_message()
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
    view_data["results"] = ""
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
    view_data["results"] = "{}"
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
                postdata["libname"] = tokens[0]
                postdata["max_depth"] = tokens[1]
                logging.info("postdata: {}".format(postdata))
                r = httpx.post(
                    url,
                    headers=websvc_headers,
                    content=json.dumps(postdata),
                    timeout=120.0,
                )
                bom_obj = json.loads(r.text)
                view_data["results"] = json.dumps(bom_obj, sort_keys=False, indent=2)
                view_data["inline_bom_json"] = view_data["results"]
                view_data["visualization_message"] = "D3.js Graph Visualization"
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
                view_data["results"] = json.dumps(
                    sqr.response_obj, sort_keys=False, indent=2
                )
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

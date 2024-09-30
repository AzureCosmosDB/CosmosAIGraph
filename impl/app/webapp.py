# This is the entry-point for this web application, built with the
# FastAPI web framework
#
# Chris Joakim

import asyncio
import json
import logging
import textwrap
import time
import uuid

import httpx

from dotenv import load_dotenv

from fastapi import FastAPI, Request, Response, Form, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# next three lines for authentication with MSAL
from fastapi import Depends
from starlette.middleware.sessions import SessionMiddleware
from fastapi_msal import MSALAuthorization, UserInfo, MSALClientConfig

# Pydantic models defining the "shapes" of requests and responses
from src.models.webservice_models import PingModel
from src.models.webservice_models import LivenessModel
from src.models.webservice_models import AiConvFeedbackModel

# Services with Business Logic
from src.services.ai_completion import AiCompletion
from src.services.ai_conversation import AiConversation
from src.services.ai_service import AiService
from src.services.db_service import DBService
from src.services.config_service import ConfigService
from src.services.logging_level_service import LoggingLevelService
from src.services.rag_data_service import RAGDataService
from src.services.rag_data_result import RAGDataResult
from src.util.sparql_formatter import SparqlFormatter
from src.services.ontology_service import OntologyService


# standard initialization
load_dotenv(override=True)
logging.basicConfig(
    format="%(asctime)s - %(message)s", level=LoggingLevelService.get_level()
)
ConfigService.print_defined_env_vars()

ai_svc = AiService()
db_svc = DBService()


async def initialize_async_services():
    global ai_svc
    global db_svc
    await ai_svc.initialize()
    logging.error("initialize_async_services - AiService initialized in webapp.py")
    await db_svc.initialize()
    logging.error("initialize_async_services - DBService initialized in webapp.py")


# See https://www.slingacademy.com/article/python-error-asynciorun-cannot-be-called-from-a-running-event-loop/
event_loop = None
try:
    event_loop = asyncio.get_running_loop()
except:
    pass
logging.error("event_loop: {}".format(event_loop))

if event_loop is not None:
    # this path is for running in a Docker container with uvicorn
    logging.error("asyncio event_loop is not None")
    task = asyncio.create_task(initialize_async_services())
else:
    # this path is for running as a Python script
    logging.error("asyncio event_loop is None")
    asyncio.run(ai_svc.initialize())
    logging.error("AiService initialized in webapp.py")
    asyncio.run(db_svc.initialize())
    logging.error("DBService initialized in webapp.py")

logging.error("code_version: {}".format(ConfigService.code_version()))
logging.error("graph_source: {}".format(ConfigService.graph_source()))

logging.error(
    "ConfigService.graph_source is {} in webapp.py".format(ConfigService.graph_source())
)

ontology_svc = OntologyService()
owl_xml = ontology_svc.get_owl_content()
if owl_xml is None:
    logging.error("owl_xml is empty")
else:
    logging.info("owl_xml loaded; length: {}".format(len(owl_xml)))

rag_data_svc = RAGDataService(ai_svc, db_svc)
logging.error("RAGDataService created")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
views = Jinja2Templates(directory="views")

# web app authentication with MSAL
msal_client_config, msal_auth = None, None
if ConfigService.use_msal_auth():
    # See https://github.com/dudil/fastapi_msal
    # See https://learn.microsoft.com/en-us/python/api/overview/azure/active-directory?view=azure-python
    msal_client_config: MSALClientConfig = MSALClientConfig()
    msal_client_config.client_id = ConfigService.msal_client_id()
    msal_client_config.client_credential = ConfigService.msal_client_credential()
    msal_client_config.tenant = ConfigService.msal_tenant()
    app.add_middleware(SessionMiddleware, secret_key=ConfigService.msal_ssh_key())
    msal_auth = MSALAuthorization(client_config=msal_client_config)
    app.include_router(msal_auth.router)
    logging.info(
        "msal auth enabled, client_id: {}".format(ConfigService.msal_client_id())
    )
else:
    logging.info("msal auth disabled")

# web service authentication with shared secrets
websvc_auth_header = ConfigService.websvc_auth_header()
websvc_auth_value = ConfigService.websvc_auth_value()
websvc_headers = dict()
websvc_headers["Content-Type"] = "application/json"
websvc_headers[websvc_auth_header] = websvc_auth_value
logging.debug(
    "webapp.py websvc_headers: {}".format(json.dumps(websvc_headers, sort_keys=False))
)

if ConfigService.use_msal_auth():

    @app.get(
        "/users/me",
        response_model=UserInfo,
        response_model_exclude_none=True,
        response_model_by_alias=False,
    )
    async def read_users_me(
        current_user: UserInfo = Depends(msal_auth.scheme),
    ) -> UserInfo:
        return current_user


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
    view_data["code_version"] = ConfigService.code_version()
    view_data["graph_source"] = ConfigService.graph_source()
    view_data["graph_source_db"] = ConfigService.graph_source_db()
    view_data["graph_source_container"] = ConfigService.graph_source_container()
    return views.TemplateResponse(request=req, name="about.html", context=view_data)


@app.get("/config")
async def get_config(req: Request):
    view_data = dict()
    return views.TemplateResponse(request=req, name="config.html", context=view_data)


@app.get("/sparql_console")
async def get_sparql_console(req: Request):
    if ConfigService.use_alt_sparql_console():
        view_data = get_alt_sparql_console(req)
        return views.TemplateResponse(
            request=req, name="alt_sparql_console.html", context=view_data
        )
    else:
        view_data = get_libraries_sparql_console(req)
        return views.TemplateResponse(
            request=req, name="sparql_console.html", context=view_data
        )


@app.post("/sparql_console")
async def post_sparql_console(req: Request):
    form_data = await req.form()  # <class 'starlette.datastructures.FormData'>
    logging.info("/sparql_console form_data: {}".format(form_data))
    if ConfigService.use_alt_sparql_console():
        view_data = post_alt_sparql_console(form_data)
        return views.TemplateResponse(
            request=req, name="alt_sparql_console.html", context=view_data
        )
    else:
        view_data = post_libraries_sparql_console(form_data)
        return views.TemplateResponse(
            request=req, name="sparql_console.html", context=view_data
        )


# cj - /gen_graph and /gen_graph_generate have been disabled in the UI; see layout.html


@app.get("/gen_graph")
async def get_graph(req: Request):
    view_data = gen_graph_view_data()
    return views.TemplateResponse(request=req, name="gen_graph.html", context=view_data)


@app.post("/gen_graph_generate")
async def gen_graph_execute(req: Request):
    """This endpoint is not used at this time; this functionality may be revisited."""
    form_data = await req.form()

    ontologyFile = form_data["fileOntology"].filename
    ontology = await form_data["fileOntology"].read()
    f = open(ontologyFile, "wb")
    f.write(ontology)
    f.close()

    view_data = gen_graph_view_data()
    view_data["results_message"] = ""
    view_data["owl"] = ontology.decode("utf-8")

    # read the contents of the uploaded files from req parameter
    entitiesFiles = []
    if (form_data["fileEntities"] == None) or (
        form_data["fileEntities"].filename == ""
    ):
        view_data["results_message"] += "No entity files uploaded\n"
    else:
        for entityUpload in form_data.getlist("fileEntities"):
            entitiesFile = entityUpload.filename
            entitiesFiles.append(entitiesFile)
            f = open(entitiesFile, "wb")
            entities = await entityUpload.read()
            f.write(entities)
            f.close()

    relationshipsFiles = []
    if (form_data["fileRelationships"] == None) or (
        form_data["fileRelationships"].filename == ""
    ):
        view_data["results_message"] += "No relationship files uploaded\n"
    else:
        for relationshipUpload in form_data.getlist("fileRelationships"):
            relationshipsFile = relationshipUpload.filename
            relationshipsFiles.append(relationshipsFile)
            f = open(relationshipsFile, "wb")
            relationships = await relationshipUpload.read()
            f.write(relationships)
            f.close()

    try:
        pass
        # cj - revisit this and use DBService, instead of CosmosVCoreService, when we re-implement
        # opts = dict()
        # opts["conn_string"] = ConfigService.mongo_vcore_conn_str()
        # logging.info("opts: {}".format(opts))
        # vcore = CosmosVCoreService(opts)
        # vcore.set_db(ConfigService.graph_source_db())
        # if vcore.insert_docs_from_files(entitiesFiles, relationshipsFiles, ontologyFile):
        #     f = open("results.nt", "r")
        #     view_data["results"] = f.read()
        #     view_data["results_message"] += "Generated graph successfully: \n"
    except Exception as e:
        logging.critical((str(e)))
        logging.exception(e, stack_info=True, exc_info=True)
        view_data["results_message"] += "\nCouldn't generate graph"
    return views.TemplateResponse(request=req, name="gen_graph.html", context=view_data)


@app.get("/gen_sparql_console")
async def get_ai_console(req: Request):
    view_data = gen_sparql_console_view_data()
    view_data["natural_language"] = (
        "What are the dependencies of the pypi type of library named flask ?"
    )
    view_data["sparql"] = "SELECT * WHERE { ?s ?p ?o . } LIMIT 10"
    return views.TemplateResponse(
        request=req, name="gen_sparql_console.html", context=view_data
    )


@app.post("/gen_sparql_console_generate_sparql")
async def ai_post_gen_sparql(req: Request):
    global owl_xml
    form_data = await req.form()
    logging.info("/gen_sparql_console_generate_sparql form_data: {}".format(form_data))
    natural_language = form_data.get("natural_language")
    view_data = gen_sparql_console_view_data()
    view_data["natural_language"] = natural_language
    sparql: str = ""

    resp_obj = dict()
    resp_obj["session_id"] = (
        ""  # Note: not currently used, populate with the HTTP session ID
    )
    resp_obj["natural_language"] = natural_language
    resp_obj["owl"] = owl_xml
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

    resp_obj = post_sparql_query_to_graph_microsvc(sparql)
    view_data["results"] = json.dumps(resp_obj, sort_keys=False, indent=2)
    view_data["results_message"] = "SPARQL Query Results"
    return views.TemplateResponse(
        request=req, name="gen_sparql_console.html", context=view_data
    )


@app.get("/vector_search_console")
async def get_vector_search_console(req: Request):
    view_data = dict()
    view_data["libtype"] = "pypi"
    view_data["libname"] = "flask"
    view_data["results_message"] = ""
    view_data["results"] = ""
    return views.TemplateResponse(
        request=req, name="vector_search_console.html", context=view_data
    )


@app.post("/vector_search_console")
async def post_vector_search_console(req: Request):
    global db_svc
    form_data = await req.form()
    logging.info("/vector_search_console form_data: {}".format(form_data))
    libtype = form_data.get("libtype")
    libname = form_data.get("libname").strip()
    logging.debug(
        "vector_search_console - libtype: {}, libname: {}".format(libtype, libname)
    )

    if libname.startswith("text:"):
        text = libname[5:]
        logging.info(f"post_vector_search_console; text: {text}")
        try:
            logging.info("vectorize: {}".format(text))
            ai_svc_resp = ai_svc.generate_embeddings(text)
            vector = ai_svc_resp.data[0].embedding
            logging.warning(f"post_vector_search_console; vector: {vector}")
        except Exception as e:
            logging.critical((str(e)))
            logging.exception(e, stack_info=True, exc_info=True)

        db_svc.set_db(ConfigService.graph_source_db())
        db_svc.set_container(ConfigService.graph_source_container())
        results_obj = await db_svc.rag_vector_search(vector)
    else:
        db_svc.set_db(ConfigService.graph_source_db())
        db_svc.set_container(ConfigService.graph_source_container())
        docs = await db_svc.get_documents_by_libtype_and_names("pypi", [libname])
        logging.debug("vector_search_console - docs count: {}".format(len(docs)))

        if len(docs) > 0:
            doc = docs[0]
            db_svc.set_db(ConfigService.graph_source_db())
            db_svc.set_container(ConfigService.graph_source_container())
            results_obj = await db_svc.rag_vector_search(doc["embedding"])
        else:
            results_obj = list()

    view_data = dict()
    view_data["libtype"] = libtype
    view_data["libname"] = libname
    view_data["results_message"] = "Vector Search Results"
    view_data["results"] = json.dumps(results_obj, sort_keys=False, indent=2)
    return views.TemplateResponse(
        request=req, name="vector_search_console.html", context=view_data
    )


@app.get("/conv_ai_console")
async def conv_ai_console(req: Request):
    # conv = FS.read_json("static/sample_ai_conversation.json")
    conv = AiConversation()
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
    global db_svc
    global ontology_svc
    global owl_xml
    global rag_data_svc

    form_data = await req.form()
    logging.info("/conv_ai_console form_data: {}".format(form_data))
    conversation_id = form_data.get("conversation_id").strip()
    user_text = form_data.get("user_text").strip().lower()
    logging.info(
        "conversation_id: {}, user_text: {}".format(conversation_id, user_text)
    )
    conv = await db_svc.load_conversation(conversation_id)

    if conv.conversation_id == "":
        conv.set_conversation_id(str(uuid.uuid4()))  # this is a new conversation
        await db_svc.save_conversation(conv)
        logging.info("new conversation saved: {}".format(conversation_id))
    else:
        logging.info(
            "conversation loaded: {} {}".format(conversation_id, conv.serialize())
        )

    if len(user_text) > 0:
        conv.add_user_message(user_text)
        prompt_text = ai_svc.generic_prompt_template()

        rdr: RAGDataResult = await rag_data_svc.get_rag_data(user_text, 3)
        if rdr.has_db_rag_docs() == True:
            completion = AiCompletion(conv.conversation_id, None)
            completion.set_user_text(user_text)
            completion.set_rag_strategy(rdr.get_strategy())
            content_lines = list()
            for doc in rdr.get_rag_docs():
                line_parts = list()
                for attr in ["name", "summary", "documentation_summary"]:
                    if attr in doc.keys():
                        value = doc[attr].strip()
                        if len(value) > 0:
                            line_parts.append("{}: {}".format(attr, value))
                content_lines.append(".  ".join(line_parts))
            completion.set_content("\n".join(content_lines))
            conv.add_completion(completion)
            await db_svc.save_conversation(conv)
        else:
            if rdr.has_graph_rag_docs() == True:
                # Add a pseudo-completion to the conversation with the
                # names of the returned libraries/documents returned
                # from the graph SPARQL query.
                completion = AiCompletion(conv.conversation_id, None)
                completion.set_user_text(user_text)
                completion.set_rag_strategy(rdr.get_strategy())
                content_lines = list()
                for doc in rdr.get_rag_docs():
                    if "name" in doc.keys():
                        value = doc["name"].strip()
                        if len(value) > 0:
                            content_lines.append(value)
                completion.set_content(", ".join(content_lines))
                conv.add_completion(completion)
                conv.add_diagnostic_message("sparql: {}".format(rdr.get_sparql()))
                await db_svc.save_conversation(conv)

            completion_context = conv.last_completion_content()
            rag_data = rdr.as_system_prompt_text()
            context = "{}\n{}".format(completion_context, rag_data)

            max_tokens = ConfigService.invoke_kernel_max_tokens()
            temperature = ConfigService.invoke_kernel_temperature()
            top_p = ConfigService.invoke_kernel_top_p()
            completion: AiCompletion = await ai_svc.invoke_kernel(
                conv,
                prompt_text,
                user_text,
                context=context,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            completion.set_rag_strategy(rdr.get_strategy())
            await db_svc.save_conversation(conv)

    textformat_conversation(conv)

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
    global db_svc
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
    await db_svc.save_feedback(req_model)
    return req_model


# non-endpoint methods:
def gen_graph_view_data():
    global owl_xml

    view_data = dict()

    view_data["owl"] = owl_xml
    view_data["results_message"] = ""
    view_data["results"] = ""
    return view_data


def gen_sparql_console_view_data():
    global owl_xml

    view_data = dict()
    view_data["natural_language"] = (
        "What are the dependencies of the pypi type of library named flask ?"
    )
    view_data["sparql"] = ""
    view_data["owl"] = owl_xml
    view_data["results_message"] = ""
    view_data["results"] = ""
    return view_data


def graph_microsvc_sparql_query_url():
    return "{}:{}/sparql_query".format(
        ConfigService.graph_service_url(), ConfigService.graph_service_port()
    )


def graph_microsvc_bom_query_url():
    return "{}:{}/sparql_bom_query".format(
        ConfigService.graph_service_url(), ConfigService.graph_service_port()
    )


# At this time the web application can support up to two different
# SPARQL console views, the libraries view and an alternative view.
# But the UI will show only one of these.
# The logic to handle these two cases is below.


def get_libraries_sparql_console(req: Request) -> dict:
    """Return the view data for the libraries SPARQL console"""
    sparql = """
PREFIX c: <http://cosmosdb.com/caig#>
SELECT ?used_lib
WHERE {
    <http://cosmosdb.com/caig/pypi_flask> c:uses_lib ?used_lib .
}
LIMIT 10
"""
    view_data = dict()
    view_data["method"] = "get"
    view_data["sparql"] = sparql
    view_data["bom_query"] = ""
    view_data["results_message"] = ""
    view_data["results"] = ""
    view_data["bom_json_str"] = "{}"
    view_data["inline_bom_json"] = "{}"
    view_data["libtype"] = ""
    return view_data


def get_alt_sparql_console(req: Request):
    """Return the view data for the alternative SPARQL console"""
    sparql = """
SELECT * WHERE { ?s ?p ?o . } LIMIT 10
"""
    view_data = dict()
    view_data["method"] = "get"
    view_data["sparql"] = sparql
    view_data["results_message"] = ""
    view_data["results"] = ""
    return view_data


def post_libraries_sparql_console(form_data):
    global websvc_headers

    sparql = form_data.get("sparql")
    bom_query = form_data.get("bom_query").strip()
    logging.info("sparql: {}".format(sparql))
    logging.info("bom_query: {}".format(bom_query))

    view_data = dict()
    view_data["method"] = "post"
    view_data["sparql"] = sparql
    view_data["bom_query"] = bom_query
    view_data["results_message"] = "Results"
    view_data["results"] = ""
    view_data["bom_json_str"] = "{}"
    view_data["inline_bom_json"] = "{}"
    view_data["libtype"] = ""

    # execute either a BOM query or a simple SPARQL query, per Form input

    if len(bom_query) > 0:
        tokens = bom_query.split()
        if len(tokens) > 1:
            view_data["libtype"] = tokens[0]
            bom_obj = None
            url = graph_microsvc_bom_query_url()
            logging.info("url: {}".format(url))
            postdata = dict()
            postdata["libtype"] = "pypi"
            postdata["libname"] = tokens[0]
            postdata["max_depth"] = tokens[1]
            logging.info("postdata: {}".format(postdata))
            r = httpx.post(
                url,
                headers=websvc_headers,
                data=json.dumps(postdata),
                timeout=120.0,
            )
            bom_obj = json.loads(r.text)
            view_data["results"] = json.dumps(bom_obj, sort_keys=False, indent=2)
            view_data["inline_bom_json"] = view_data["results"]
        else:
            view_data["results"] = "Invalid BOM query: {}".format(bom_query)
    else:
        response_obj = post_sparql_query_to_graph_microsvc(sparql)
        view_data["results"] = json.dumps(response_obj, sort_keys=False, indent=2)
    return view_data


def post_alt_sparql_console(form_data):
    sparql = form_data.get("sparql")
    view_data = dict()
    view_data["method"] = "post"
    view_data["sparql"] = sparql
    view_data["results_message"] = ""
    view_data["results"] = ""
    logging.info("sparql: {}".format(sparql))

    if len(sparql) > 0:
        response_obj = post_sparql_query_to_graph_microsvc(sparql)
        view_data["results"] = json.dumps(response_obj, sort_keys=False, indent=2)
    return view_data


def post_sparql_query_to_graph_microsvc(sparql: str) -> None:
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
            url, headers=websvc_headers, data=json.dumps(postdata), timeout=120.0
        )
        obj = json.loads(r.text)
        return obj
    except Exception as e:
        logging.critical((str(e)))
        logging.exception(e, stack_info=True, exc_info=True)
        return {}


def textformat_conversation(conv: AiConversation) -> None:
    """
    do an in-place reformatting of the conversaton text, such as completion content
    """
    try:
        for comp in conv.completions:
            if "content" in comp.keys():
                content = comp["content"]
                if content is not None:
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
                        wrapped_lines = textwrap.wrap(stripped, width=120)
                        for line in wrapped_lines:
                            content_lines.append(line)
                        comp["content"] = "\n".join(content_lines)
    except Exception as e:
        logging.critical((str(e)))
        logging.exception(e, stack_info=True, exc_info=True)


def remove_mongo_id_attr(mongo_doc) -> None:
    """
    Remove the '_id' attribute from the Mongo object because
    ObjectId values are not JSON serializable
    """
    if mongo_doc is not None:
        if "_id" in mongo_doc.keys():
            del mongo_doc["_id"]

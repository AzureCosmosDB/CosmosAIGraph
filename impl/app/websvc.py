import asyncio
import logging
import time
import traceback

from dotenv import load_dotenv

from fastapi import FastAPI, Request, Response, status

# from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates

# Pydantic models defining the "shapes" of requests and responses
from src.models.webservice_models import PingModel
from src.models.webservice_models import LivenessModel
from src.models.webservice_models import OwlInfoModel
from src.models.webservice_models import SparqlQueryRequestModel
from src.models.webservice_models import SparqlQueryResponseModel
from src.models.webservice_models import SparqlBomQueryRequestModel
from src.models.webservice_models import SparqlBomQueryResponseModel

# Services with Business Logic
from src.services.config_service import ConfigService
from src.services.graph_builder import GraphBuilder
from src.services.graph_service import GraphService
from src.services.logging_level_service import LoggingLevelService

# standard initialization
load_dotenv(override=True)
logging.basicConfig(
    format="%(asctime)s - %(message)s", level=LoggingLevelService.get_level()
)
ConfigService.print_defined_env_vars()

app = FastAPI()

opts = {}
opts["iterate_graph"] = True
gb = GraphBuilder(opts)
gs = GraphService(opts)


async def initialize_async_services():
    global gb
    global gs
    await gb.initialize()
    logging.error("initialize_async_services - GraphBuilder initialized in websvc.py")
    await gs.initialize(gb)
    logging.error("initialize_async_services - GraphService initialized in websvc.py")


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
    asyncio.run(gb.initialize())
    asyncio.run(gs.initialize(gb))
    logging.error("GraphService initialized in websvc.py")

logging.error("code_version: {}".format(ConfigService.code_version()))
logging.error("graph_source: {}".format(ConfigService.graph_source()))

logging.error(
    "ConfigService.graph_source is {} in websvc.py".format(ConfigService.graph_source())
)

# begin middleware for authentication,
# see https://fastapi.tiangolo.com/tutorial/middleware/
defined_auth_header = ConfigService.websvc_auth_header()
defined_auth_value = ConfigService.websvc_auth_value()
defined_noauth_paths = ["/", "/liveness"]
logging.debug("defined_auth_header:  {}".format(defined_auth_header))
logging.debug("defined_auth_value:   {}".format(defined_auth_value))
logging.debug("defined_noauth_paths: {}".format(defined_noauth_paths))


@app.middleware("http")
async def check_auth_header(request: Request, call_next):
    logging.debug(f"middleware - path: {request.url.path} headers: {request.headers}")

    if request.url.path in defined_noauth_paths:
        return await call_next(request)
    else:
        if defined_auth_header is not None:
            if defined_auth_header not in request.headers:
                logging.error(
                    f"middleware - missing auth header: {defined_auth_header}"
                )
                return Response(content="missing auth header", status_code=401)
            elif request.headers[defined_auth_header] != defined_auth_value:
                logging.error(
                    f"middleware - invalid auth header: {defined_auth_header}"
                )
                return Response(content="invalid auth header", status_code=401)
            else:
                return await call_next(request)
        else:
            return await call_next(request)


@app.get("/")
async def get_index() -> PingModel:
    resp = dict()
    resp["epoch"] = str(time.time())
    return resp


@app.get("/liveness")
async def get_liveness(req: Request, resp: Response) -> LivenessModel:
    """
    Return a LivenessModel indicating the health of this microservice.
    This endpoint is invoked by the Azure Container Apps (ACA) service.
    The implementation invokes the liveness_check() method on the
    GraphService object to check that the graph is populated in-memory.
    """
    # See https://learn.microsoft.com/en-us/azure/container-apps/health-probes
    global gs
    liveness_data = dict()
    liveness_data["alive"] = False
    liveness_data["rows_read"] = -1
    liveness_data["epoch"] = time.time()
    try:
        liveness_data = gs.liveness_check()
    except:
        pass
    if liveness_data["alive"] == True:
        resp.status_code = status.HTTP_200_OK
    else:
        resp.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    logging.info("liveness_check: {}".format(liveness_data))
    return liveness_data


@app.get("/owl_info")
async def get_owl_info() -> OwlInfoModel:
    global gs
    owl_info = gs.owl_info()
    owl_info["epoch"] = time.time()
    return owl_info


@app.post("/sparql_query")
async def post_sparql_query(
    req_model: SparqlQueryRequestModel,
) -> SparqlQueryResponseModel:
    global gs
    resp_obj = dict()
    resp_obj["sparql"] = "??"
    resp_obj["results"] = None
    resp_obj["elapsed"] = -1.0
    resp_obj["error"] = None
    t1 = time.perf_counter()
    try:
        logging.warn("/sparql_query: {}".format(req_model.sparql))
        resp_obj["sparql"] = req_model.sparql
        rqr = gs.query(req_model.sparql)  # returns a RdfQueryResult object
        rqr.prune_data()
        resp_obj["results"] = rqr.get_data()
    except Exception as e:
        resp_obj["error"] = str(e)
        logging.critical((str(e)))
        logging.exception(e, stack_info=True, exc_info=True)

    resp_obj["elapsed"] = time.perf_counter() - t1
    return resp_obj


@app.post("/sparql_bom_query")
async def post_sparql_bom_query(
    req_model: SparqlBomQueryRequestModel,
) -> SparqlBomQueryResponseModel:
    global gs
    resp_obj = dict()
    resp_obj["libtype"] = "?"
    resp_obj["libname"] = "?"
    resp_obj["max_depth"] = -1
    resp_obj["actual_depth"] = -1
    resp_obj["bom_libs"] = None
    resp_obj["elapsed"] = -1.0
    resp_obj["error"] = None
    t1 = time.perf_counter()
    try:
        libtype = req_model.libtype
        libname = req_model.libname
        max_depth = int(req_model.max_depth)
        logging.warn("/sparql_bom_query: {} {} {}".format(libtype, libname, max_depth))
        bqr = gs.bom_query(
            libtype, libname, max_depth
        )  # returns a BomQueryResult object
        resp_obj["libtype"] = libtype
        resp_obj["libname"] = libname
        resp_obj["max_depth"] = max_depth
        resp_obj["actual_depth"] = bqr.get_actual_depth()
        resp_obj["bom_libs"] = bqr.get_bom_libs()
    except Exception as e:
        resp_obj["error"] = str(e)
        logging.critical((str(e)))
        logging.exception(e, stack_info=True, exc_info=True)

    resp_obj["elapsed"] = time.perf_counter() - t1
    return resp_obj

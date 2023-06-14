import datetime
import json
import logging
import os
from typing import Dict, List, Union
from uuid import UUID, uuid4

import aiohttp
from app import Finder, Parser
from app.utils import Encoder, setLogger, writeFile
from database import Database
from fastapi import FastAPI, File, Request, Response, UploadFile, status
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_utils.tasks import repeat_every
from pydantic import BaseModel, Field

# Setup
setLogger(3)
basePath = os.getcwd()

## Setup Database
db = Database(os.path.join(basePath, "database"))

## Create comparison module
finder = Finder(db)

## Create parsing module
suiteReaderPath = os.path.join(basePath, "res", "SuiteReader.jar")
parser = Parser(basePath=basePath, suiteReaderPath=suiteReaderPath)

## Make tmp folder
if not (os.path.isdir(os.path.join(basePath, "tmp"))):
    os.mkdir(os.path.join(basePath, "tmp"))

app = FastAPI()

# # Mount frontend HTML file
# templatesPath = os.path.join(basePath, "build")
# staticPath = os.path.join(templatesPath, "static")
# app.mount("/static", StaticFiles(directory=staticPath), name="static")
# templates = Jinja2Templates(directory=templatesPath)


# @app.get("/")
# async def mainPage(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})


class tclFilterItem(BaseModel):
    testCase: str
    items: list


class findConfigItem(BaseModel):
    topk: int
    testCaseBoolean: Union[List[tclFilterItem], None] = None
    testCaseString: Union[List[tclFilterItem], None] = None


class Item(BaseModel):
    uid: UUID = Field(default_factory=uuid4)
    status: str = "Waiting"  # ['Waiting', 'Reading', 'Parsing', 'Finding', 'Complete']
    filePath: str = None
    steData: dict = None
    topk: dict = None
    time: datetime.datetime = datetime.datetime.now()


ParsedSteData: Dict[UUID, Item] = {}


@app.on_event("startup")
@repeat_every(seconds=60 * 20)  # 20 minutes
def removeExpiredSteData() -> None:
    """repeat_every
    Goes through ParsedSteData dictionary every 20 minutes
    and delete items that are overdated(20min).
    """
    logging.info("Cleaing unused parsed STE data")
    currentTime = datetime.datetime.now()
    delta = 20 * 60
    toDelete = [
        uid
        for uid, item in ParsedSteData.items()
        if datetime.datetime.now() + datetime.timedelta(seconds=delta) > currentTime
    ]
    for uid in toDelete:
        del ParsedSteData[uid]
    logging.info("Removed %d items from ParsedSteData", len(toDelete))
    logging.info("%d items in ParsedSteData", len(ParsedSteData))


@app.on_event("startup")
@repeat_every(seconds=7 * 24 * 60 * 60)  # every week
def update() -> None:
    """
    Updates test sessions with registered TAS.
    It will add new test sessions to database
    """
    if db.last_update == datetime.date.today():
        return
    logging.info("Updating database")
    updated = db.updateTestSession()
    if updated == -1:
        logging.error("Failed to update database")
        return
    logging.info("Updated %d test sessions", updated)


@app.on_event("startup")
@repeat_every(seconds=24 * 60 * 60)  # every day
# caveat : investigate server performance impact on repeat_every tasks
def validate() -> None:
    """
    Validates test sessions with registered TAS.
    It will check if TAS RESTful API is running at given time
    It will check if test session exist in TAS at given time.
    """
    if db.last_validated == datetime.date.today():
        return
    logging.info("Validating database")
    db.updateDatabaseStatus()


@app.post("/Input")
async def parseInput(file: UploadFile = File(...)):
    """Reads *.ste file from client and parse file.
    Parsed items include name, keywords, description, tclData('boolean', 'string').

    Args:
        file (UploadFile, optional): Uploaded *.ste file from client. Defaults to File(...).

    Returns:
        json_string: returns json string that includes parsed item with UUID4
    """
    logging.info("Got client data. Processing...")
    item = Item()
    ParsedSteData[item.uid] = item
    item.status = "Reading"
    item.filePath = os.path.join(basePath, "tmp", os.path.basename(file.filename))
    isWriteSuccess = await writeFile(file, item.filePath)
    if not isWriteSuccess:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="There was an error uploading the file",
        )
    item.status = "Parsing"
    item.steData = await parser.parseSte(item.filePath)
    if not item.steData:
        logging.error("Failed to parse uploaded file")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse given input",
        )

    try:
        logging.debug("Removing client uploadfile at %s", item.filePath)
        os.remove(item.filePath)
    except:
        logging.error("Failed to remove uploaded file")

    itemToSend = {"key": item.uid}
    itemToSend.update(item.steData)
    return json.dumps(itemToSend, indent=4, cls=Encoder)


@app.post("/Result/{uid}")
def result(uid: UUID, findConfig: findConfigItem):
    """Find similar CI B2B test suite to given uid. It will search inside scope of
    findConfig which includes topk, and certain TCL variables for such testCase.

    Args:
        uid (UUID): UUID for parsed data
        findConfig (findConfigItem): Configuration about topk and TCL constraints on search

    Returns:
        json_string: returns json string that includes name, top score, and similarity analysis
    """
    if uid not in ParsedSteData:
        logging.error("No data found with UUID %s", uid)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No data found with UUID {uid}",
        )

    logging.info("Creating result for UUID %s", uid)
    findConfig = findConfig.dict()
    topk = findConfig["topk"]
    filterConfigBoolean = {
        item["testCase"]: item["items"] for item in findConfig["testCaseBoolean"]
    }
    filterConfigString = {
        item["testCase"]: item["items"] for item in findConfig["testCaseString"]
    }
    logging.debug("filterConfig - Boolean: %s", str(filterConfigBoolean))
    logging.debug("filterConfig - String: %s", str(filterConfigString))

    item = ParsedSteData[uid]
    item.status = "Finding"
    scores = finder.find(item.steData, filterConfigBoolean, filterConfigString)
    if not scores:
        logging.error("Failed to find simillar CI Tests to given input")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find similar CI Tests to given input",
        )
    logging.info("Found similar CI test suites from Database")

    topkResult, topScore = finder.getTopk(scores, topk)
    metadata = {"name": item.steData["name"], "topScore": topScore, "info": []}
    for testSessionId, score in topkResult.items():
        targetTestSession = db.getTestSessionDetail(testSessionId)
        analysis = finder.analyzeTclDifference(
            item.steData["tclData"], targetTestSession["tclData"]
        )
        targetTestSession.update({"score": score, "testCase": analysis})
        metadata["info"].append(targetTestSession)

    item.status = "Complete"
    return json.dumps(metadata, indent=4, cls=Encoder)


@app.post("/Download")
async def downloadSte(address: str, libraryId: int, name: str, deleteSte: bool = True):
    """returns binary data of given STE

    Args:
        address (str): Address to TAS
        libraryId (int): ID of library
        name (str): name of test suite
        deleteSte (bool, optional): Delete metadata in TAS server. Defaults to True.

    Raises:
        HTTPException: Raised when there is no matching items

    Returns:
        Response: Binary data of ste file
    """
    logging.info("Downloading STE")

    url = f"http://{address}:8080/api/testSuites?action=export"
    headers = {"Authorization": "Basic c21zOmExYjJjM2Q0"}
    params = {
        "library": libraryId,
        "name": name,
        "deleteSte": str(deleteSte),
    }
    try:
        async with aiohttp.ClientSession(
            headers=headers, raise_for_status=True
        ) as session:
            async with session.post(url, params=params) as response:
                steData = await response.read()
    except aiohttp.ClientError:
        logging.error("Failed to generate download link for ste %s", name)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download link",
        )
    return Response(content=steData, media_type="application/binary")

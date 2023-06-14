import datetime
import logging
import sys

from .dbBase import DbBase


class DbTestSession(DbBase):
    def __init__(self, connection, userInfo):
        super().__init__(connection, userInfo)
        self.itemCount = -1
        self.setup()

    def setup(self) -> None:
        """Initial setup for TestSession table. If table
        doesn't exist, it will create a new table.
        """
        logging.info("Setting up TestSession Table")
        if not super().isTableExist("TestSession"):
            if not self.create():
                logging.error("Failed to create TestSession table. Aborting...")
                sys.exit()
        self.itemCount = super().getItemCount("TestSession")
        if self.itemCount == -1:
            logging.warning("Failed to get item count of TestSession table")
        logging.info("Setup Finished | %d items in TestSession", self.itemCount)

    # CREATE
    def create(self) -> bool:
        """Creates TestSession table.

        Returns:
            bool: Result of create query
        """
        logging.debug("Creating TestSession table")
        query = """CREATE TABLE TestSession (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tasId INT NOT NULL,
                name TEXT NOT NULL,
                keywords TEXT ,
                description TEXT,
                status TEXT,
                last_update DATE
            );"""
        super().execute(query)
        if not super().isTableExist("TestSession"):
            logging.error("Failed to create TestSession table")
            return False
        logging.debug("Success")
        return True

    # READ
    def getInfo(self, testSessionId: int) -> dict:
        """Fetch information about given test session.

        Args:
            testSessionId (int): ID for test session

        Returns:
            dict: Information about test session
        """
        logging.debug("Fetching data of test session with id %d", testSessionId)
        query = f"SELECT * FROM TestSession WHERE id={testSessionId};"
        item = super().select(query)
        if not item:
            logging.debug("Failed to find item with id %d", testSessionId)
            return {}
        item = item[0]
        testSession = {
            "id": item[0],
            "tasId": item[1],
            "name": item[2],
            "keywords": eval(item[3]),
            "description": item[4],
            "status": item[5],
            "last_update": item[6],
        }
        logging.debug("Fetched test session information")
        return testSession

    def getValidTestSessionIds(self) -> list:
        """Fetch test sessions that are able to download from TAS.

        Returns:
            list: List of test session IDs
        """
        logging.debug("Fetching valid test sessions")
        query = "SELECT id FROM TestSession WHERE status=1;"
        items = super().select(query)
        if not items:
            logging.debug("No items available for download")
            return []
        logging.debug("Fetched %d items", len(items))
        return [item[0] for item in items]

    # UPDATE (INSERT)
    def insert(self, tasInfo: dict, testSessionInfo: dict) -> int:
        """Adds new TestSession item to database

        Args:
            tasInfo (dict): Information about TAS. Should include
            id, address, libraryId.
            testSessionInfo (dict): Information about testSession.
            Should include name, keywords, descriptions of test session.

        Returns:
            int: ID of added item
        """
        logging.debug("Adding new TestSession item")
        name = testSessionInfo.get("name", None)
        keywords = testSessionInfo.get("keywords", None)
        description = testSessionInfo.get("description, None")
        if name is None:
            logging.error("Name should be specified")
            return -1

        # Check for duplicates
        testSessionId = self.isExist(tasInfo["id"], name)
        if testSessionId != -1:
            logging.error("Same data exist. Aborting")
            return testSessionId

        query = "INSERT INTO TestSession ('tasId', 'name', 'keywords', 'description', 'status', 'last_update') VALUES (?, ?, ?, ?, ?, ?);"

        # Create item
        keywords = str(keywords.strip().split(" ")) if keywords is not None else None
        status = self.isAlive(tasInfo, name)
        item = (
            tasInfo["id"],
            name,
            keywords,
            description,
            status,
            datetime.date.today(),
        )

        super().insert(query, item)
        testSessionId = self.isExist(tasInfo["id"], name)
        if testSessionId == -1:
            logging.error("Failed to insert new data")
            return -1

        logging.debug("Success | ID : %d", testSessionId)
        self.itemCount = super().getItemCount("TestSession")
        return testSessionId

    # UPDATE
    def update(self):
        return NotImplementedError

    def updateStatus(self, id: int, status: int) -> bool:
        """Update status of TestSession with given ID and status.
        Status will used to validate if download is available.

        Args:
            id (int): ID of TestSession item
            status (int): Status to change. 1 for alive, 0 for down

        Returns:
            bool: Result of update action. True if success, else False
        """
        logging.debug("Updating status to %s", "True" if status else "False")
        query = f"UPDATE TestSession SET status={status} WHERE id={id};"
        if super().execute(query) == -1:
            logging.error("Failed to update status")
            return False
        logging.debug("Success")
        return True

    def validate(self, tasItems: dict) -> tuple:
        """Checks for registered Test Sessions that is is alive

        Args:
            tasItems (dict): Dictionary of TAS items including address
            and libraryId.

        Returns:
            tuple: Status changed items
        """
        logging.debug("Validating TestSession table")
        avail2unavail = 0
        unavail2avail = 0

        testSessionItems = super().select(
            "SELECT id, tasId, name, status FROM TestSession"
        )
        if not testSessionItems:
            logging.error("Failed to fetch TestSession items")
            return -1

        for tsId, tasId, name, status in testSessionItems:
            logging.debug("Checking testSession %s", name)
            if self.isAlive(tasItems[tasId], name) == status:
                if status:
                    avail2unavail += self.updateStatus(tsId, 0)
                else:
                    unavail2avail += self.updateStatus(tsId, 1)

        logging.debug("Available -> Unavailable : %d", avail2unavail)
        logging.debug("Unavailable -> Available : %d", unavail2avail)
        return avail2unavail, unavail2avail

    # DELETE
    def delete(self):
        return NotImplementedError

    # Utility
    def isExist(self, tasId: int, name: str) -> int:
        """Checks if item already exist in database

        Args:
            tasId (int): ID of source TAS
            name (str): Name of test session

        Returns:
            int: ID of existing item. -1 if doesn't exist.
        """
        logging.debug("Checking if item exist")
        query = f"SELECT id FROM TestSession WHERE tasId={tasId} AND name='{name}';"
        item = super().select(query)
        if not item:
            logging.debug("Item doesn't exist")
            return -1
        logging.debug("Item exist. ID : %d", item[0][0])
        return item[0][0]

    def isAlive(self, tasInfo: dict, name: str) -> bool:
        """Checks if test session exist in TAS

        Args:
            tasInfo (dict): Information to TAS. Should include
            address and libraryId.
            name (str): name of test session

        Returns:
            bool: True if exists, else False
        """
        logging.debug("Checking if test session %s exist in TAS", name)
        address = tasInfo.get("address", None)
        libraryId = tasInfo.get("libraryId", None)
        if address is None or libraryId is None:
            logging.error("TAS address and library ID should be specified")
            return False

        url = f"http://{address}:8080/api/libraries/{libraryId}/testSessions/{name}"
        status, _ = super().syncSendGetRequest(url)
        if not status:
            logging.debug("Test session doesn't exist")
            return False
        logging.debug("Test session %s is alive", name)
        return True

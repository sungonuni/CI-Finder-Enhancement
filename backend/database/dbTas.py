import datetime
import logging
import sys

from .dbBase import DbBase


class DbTAS(DbBase):
    def __init__(self, connection, userInfo):
        super().__init__(connection, userInfo)
        self.itemCount = -1
        self.setup()

    def setup(self) -> None:
        """Initial setup for TAS table. If table doesn't
        exist, it will create a new table.
        """
        logging.info("Setting up TAS table")
        if not super().isTableExist("TAS"):
            if not self.create():
                logging.error("Failed to create TAS table. Aborting...")
                sys.exit()
        self.itemCount = super().getItemCount("TAS")
        if self.itemCount == -1:
            logging.warning("Failed to get item count of TAS table")
        logging.info("Setup Finished | %d items in TAS", self.itemCount)

    # CREATE
    def create(self) -> bool:
        """Creates TAS table.

        Returns:
            bool: Result of create query
        """
        logging.debug("Creating TAS table")
        query = """CREATE TABLE TAS (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL,
                library TEXT NOT NULL,
                libraryID INTEGER NOT NULL,
                status INTEGER NOT NULL,
                source TEXT NOT NULL,
                last_update DATE NOT NULL
            );"""
        super().execute(query)
        if not super().isTableExist("TAS"):
            logging.error("Failed to create TAS table")
            return False
        logging.debug("Success")
        return True

    # READ
    def getInfo(self, id: int) -> dict:
        """Fetches information about TAS with given ID.

        Args:
            id (int): ID for TAS item:w

        Returns:
            dict: TAS information including address[str], library[str],
            libraryId[int], status[int, {0,1}], source[str, {'stable', 'unstable'}],
            last_update[date].
        """
        logging.debug("Fetching TAS informatio with id %d", id)
        query = f"SELECT * FROM TAS WHERE id={id};"
        item = super().select(query)
        if not item:
            logging.error("No TAS with id %d found", id)
            return {}
        item = item[0]
        tasInfo = {
            "id": item[0],
            "address": item[1],
            "library": item[2],
            "libraryId": item[3],
            "status": item[4],
            "source": item[5],
            "last_update": item[6],
        }
        logging.debug("Found TAS item")
        return tasInfo

    def getEveryItem(self) -> dict:
        """Fetch every TAS item(id, address, libraryId) from TAS table.

        Returns:
            dict: dictionary of TAS items
        """
        logging.debug("Fetching every registered TAS items")
        query = "SELECT id, address, libraryId FROM TAS;"
        items = super().select(query)
        if not items:
            logging.error("Failed to fetch items in TAS table")
            return {}
        tas = {}
        for tasId, address, libraryId in items:
            tas[tasId] = {"address": address, "libraryId": libraryId}
        logging.debug("Fetched %d items", len(tas))
        return tas

    # UPDATE (INSERT)
    def insert(self, tasInfo: dict) -> int:
        """Adds new TAS item to database.

        Args:
            tasInfo (dict): Information about TAS. Shoud include address and
            library name.

        Returns:
            int: ID of added item
        """
        logging.debug("Adding new TAS item")
        address = tasInfo.get("address", None)
        library = tasInfo.get("library", None)
        if address is None or library is None:
            logging.error("Address and Library should be specified")
            return -1

        # Check for duplicates
        tasId = self.isExist(address, library)
        if tasId != -1:
            logging.error("Same data exist. Aborting")
            return tasId

        query = "INSERT INTO TAS ('address', 'library', 'libraryId', 'status', 'source', 'last_update') VALUES (?, ?, ?, ?, ?, ?);"

        # Create item
        libraryId = self.getTASLibraryId(address, library)
        if libraryId == -1:
            logging.error("LibraryId invalid")
            return -1
        status = self.isAlive(address)
        source = "stable" if "CIPhase" in library else "Unstable"
        item = (
            address,
            library,
            libraryId,
            status,
            source,
            datetime.date.today(),
        )

        super().insert(query, item)
        tasId = self.isExist(address, library)
        if tasId == -1:
            logging.error("Failed to insert new data")
            return -1

        logging.debug("Success | ID : %d", tasId)
        self.itemCount = super().getItemCount("TAS")
        return tasId

    # UPDATE
    def update(self) -> int:
        return NotImplementedError

    def updateStatus(self, id: int, status: int) -> bool:
        """Update status of TAS with given ID and status.
        Status will used to validate if download is available.

        Args:
            id (int): ID of TAS item
            status (int): Status to change. 1 for alive, 0 for down

        Returns:
            bool: Result of update action. True if success, else False
        """
        logging.debug("Updating status to %s", "True" if status else "False")
        query = f"UPDATE TAS SET status={status} WHERE id={id};"
        if super().execute(query) == -1:
            logging.error("Failed to update status")
            return False
        logging.debug("Success")
        return True

    def validate(self) -> tuple:
        """Checks for registered TAS that is is alive

        Returns:
            tuple: Status changed items
        """
        logging.debug("Validating TAS table")
        avail2unavail = 0
        unavail2avail = 0

        tasItems = super().select("SELECT id, address, status FROM TAS")
        if not tasItems:
            logging.error("No items in TAS")
            return -1

        checked = []
        for tasId, address, status in tasItems:
            logging.debug("Checking TAS %s", address)
            if address in checked:
                continue
            checked.append(address)
            if self.isAlive(address) == status:
                if status:
                    avail2unavail += self.updateStatus(tasId, 0)
                else:
                    unavail2avail += self.updateStatus(tasId, 1)

        logging.debug("Available -> Unavailable : %d", avail2unavail)
        logging.debug("Unavailable -> Available : %d", unavail2avail)
        return avail2unavail, unavail2avail

    # DELETE
    def delete(self) -> bool:
        return NotImplementedError

    # Utility
    def isExist(self, address: str, library: str) -> int:
        """Checks if item already exist in database

        Args:
            address (str): Address of TAS
            library (str): Name of library

        Returns:
            int: ID of existing item. -1 if doesn't exist.
        """
        logging.debug("Checking if item exist")
        query = f"SELECT id FROM TAS WHERE address='{address}' AND library='{library}';"
        item = super().select(query)
        if not item:
            logging.debug("Item doesn't exist")
            return -1
        logging.debug("Item exist. ID : %d", item[0][0])
        return item[0][0]

    def isAlive(self, address: str) -> bool:
        """Checks if TAS is alive

        Args:
            address (str): Address to TAS

        Returns:
            bool: True if alive, else False.
        """
        logging.debug("Checking if TAS %s is alive", address)
        url = f"http://{address}:8080/api"
        status, _ = super().syncSendGetRequest(url)
        if not status:
            logging.error("Failed to access TAS %s", address)
            return False
        logging.debug("TAS %s is alive", address)
        return True

    def getTASLibraryId(self, address: str, library: str) -> int:
        """Get library ID from with address and library name.

        Args:
            address (str): Address to TAS
            library (str): Name of library

        Returns:
            int: Library ID of given data. -1 if library doens't exist.
        """
        logging.debug("Fetching TAS library id of %s at %s", library, address)
        url = f"http://{address}:8080/api/libraryIds"
        status, libraries = super().syncSendGetRequest(url)
        if not status:
            logging.error("Failed to fetch library id")
            return -1
        if library not in libraries:
            logging.error("Library %s doesn't exist")
            return -1
        logging.debug("Fetched success. ID : %d", libraries[library])
        return libraries[library]

    def getTestSessionList(
        self, address: str, library: str = None, libraryId: int = None
    ) -> list:
        """Get test session list in given TAS. Used for populating initial
        database.

        Args:
            address (str): Address to TAS
            library (str): Name of library

        Returns:
            list: list of test sessions
        """
        logging.debug("Fetching test session list from TAS")
        if libraryId is None:
            libraryId = self.getTASLibraryId(address, library)
            if libraryId == -1:
                return []
        url = f"http://{address}:8080/api/libraries/{libraryId}/testSessions"
        logging.debug("URL : %s", url)
        status, item = super().syncSendGetRequest(url)
        if not status:
            logging.error("Failed to fetch test sessions")
            return []
        testSessions = item["testSessions"]
        logging.debug("Fetched %d test sessions", len(testSessions))
        return testSessions

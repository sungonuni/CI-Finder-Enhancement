import datetime
import logging
import os
import sqlite3
import sys

from .dbTas import DbTAS
from .dbTestCase import DbTestCase
from .dbTestSession import DbTestSession


class Database:
    def __init__(self, dbPath):
        userInfo = {"id": "sms", "pw": "a1b2c3d4"}
        dbPath = os.path.join(dbPath, "Finder.db")
        self.connection = sqlite3.connect(dbPath, check_same_thread=False)
        self.TAS = DbTAS(self.connection, userInfo)
        self.TESTCASE = DbTestCase(self.connection, userInfo)
        self.TESTSESSION = DbTestSession(self.connection, userInfo)
        self.setup()
        self.last_update = datetime.date.today()
        self.last_validated = datetime.date.today()

    def __del__(self):
        self.connection.close()

    def setup(self) -> None:
        """Initial setup of database. If there is no item at database, it will
        fetch test session list from default TAS(CIPhase2Assemble) and add
        every test session to database.
        """
        logging.info("Setting up database module")
        if (
            self.TAS.itemCount > 0
            and self.TESTCASE.itemCount > 0
            and self.TESTSESSION.itemCount > 0
        ):
            logging.info("Set up finished")
            return None

        logging.info("Adding default TAS")
        defaultTAS = {
            "address": "10.71.13.50",
            "library": "CIPhase2Assemble",
        }
        testSessions = self.TAS.getTestSessionList(
            defaultTAS["address"], defaultTAS["library"]
        )
        if not testSessions:
            logging.error("Failed to get test sessions in TAS. Aborting...")
            sys.exit()

        addedTestSession = 0
        for testSession in testSessions:
            testSessionId = self.insertTestSession(defaultTAS, testSession)
            if testSessionId != -1:
                addedTestSession += 1
        logging.info(
            "Added %d test sessions. Success rate : %2.2f",
            addedTestSession,
            addedTestSession / len(testSessions),
        )

        logging.info(
            "Set up finished.\nCurrent Status\n- TAS : %d item\n- Test Session : %d\n- Test Case : %d",
            self.TAS.itemCount,
            self.TESTSESSION.itemCount,
            self.TESTCASE.itemCount,
        )

    # CREATE

    # READ
    def getTestCaseData(self, testCase: str, downloadAvailOnly: bool = True) -> list:
        """Reads every item in TestCase table that has given testcase.
        It reads boolean, numeric, string type TCL variables and values.

        Args:
            testCase (str): testCase to read
            downloadAvailOnly(bool): Choose only test cases where test session
            is able to download. Defaults to True.

        Returns:
            list: list of dictionary(testSessionId[int], boolean[dict],
            numeric[dict], string[dict])
        """
        logging.info("Reading every test session with test case %s", testCase)
        logging.debug("Fetching test case data")
        testCaseData = self.TESTCASE.getTestCase(testCase)
        if not testCaseData:
            logging.error("Failed to read test case data")
            return []

        if downloadAvailOnly:
            logging.debug("Filtering test sessions that are valid")
            validTestSessions = self.TESTSESSION.getValidTestSessionIds()
            testCaseData = [
                data for data in testCaseData if data[0] in validTestSessions
            ]

        logging.info("Read %d items", len(testCaseData))
        return testCaseData

    def getTestSessionDetail(self, testSessionId: int) -> dict:
        """Reads test session information with related test case data.

        Args:
            testSessionId (int): ID for test session

        Returns:
            dict: Information about given test session ID. Includes
            name[str], description[str], keywords[list], testCase[dict].
        """
        logging.info("Reading detail about test session")
        testSessionData = self.TESTSESSION.getInfo(testSessionId)
        if not testSessionData:
            logging.error("Failed to read test session data")
            return {}
        testCaseData = self.TESTCASE.getTestCaseByTestSessionId(testSessionId)
        if not testCaseData:
            logging.error("Failed to read test case data")
            return {}
        tasData = self.TAS.getInfo(testSessionData["tasId"])
        testSessionData["tclData"] = testCaseData
        testSessionData["TAS"] = tasData
        logging.info("Reading success")
        return testSessionData

    # UPDATE
    def insertTestSession(self, tasInfo: dict, testSessionInfo: dict) -> bool:
        """Adds new test session data to database.
        It requires TAS information and Test Session information.
        For TAS information, address and library should be specified.
        For Test Session information, name should be specified.
        It will check for duplicates, and if not, will be inserted.

        Args:
            tasInfo (dict): Information about TAS. Should include
            address and library name.
            testSessionInfo (dict): Information about test session.
            Should include test session name.

        Returns:
            bool: Result of INSERT query
        """
        logging.info("Adding test session data to database")

        # Add TAS to database
        tasId = self.TAS.insert(tasInfo)
        if tasId == -1:
            logging.error("Failed to add new TAS data. Aborting...")
            return False
        logging.debug("TAS exist at id %d", tasId)

        # Update TAS information
        tasInfo = self.TAS.getInfo(tasId)
        if not tasInfo:
            logging.error("Failed to fetch TAS information. Something big went wrong")
            sys.exit()

        testSessionId = self.TESTSESSION.insert(tasInfo, testSessionInfo)
        if testSessionId == -1:
            logging.error("Failed to add new test session data. Aborting...")
            return False

        testCaseIds = self.TESTCASE.insert(testSessionId, testSessionInfo["url"])
        if not testCaseIds:
            logging.error("Failed to add new test case data. Aborting...")
            return False

        logging.info("Success")
        logging.info("TAS : %d", tasId)
        logging.info("Test Session : %d", testSessionId)
        logging.info("Test Case : %s", str(testCaseIds))
        return True

    def updateTestSession(self) -> int:
        """Updates new test sessions from TAS

        Returns:
            int: Number of added items
        """
        logging.info("Updating test sessions")
        self.TAS.validate()
        tasInfos = self.TAS.getEveryItem()
        if not tasInfos:
            logging.error("Failed to get TAS items. Aborting update")
            return -1
        for tasId, tasInfo in tasInfos.items():
            testSessions = self.TAS.getTestSessionList(
                tasInfo["address"], libraryId=tasInfo["libraryId"]
            )

            if not testSessions:
                logging.error("Failed to get test sessions in TAS. Moving to next...")
                continue

            tasInfo.update({"id": tasId})
            addedTestSession = 0
            for testSession in testSessions:
                testSessionId = self.TESTSESSION.insert(tasInfo, testSession)
                if testSessionId != -1:
                    addedTestSession += 1
        logging.info("Updated %d items", addedTestSession)
        self.last_update = datetime.date.today()
        return addedTestSession

    def updateDatabaseStatus(self) -> None:
        """Iterate through every items in TAS table and TestSession table.
        Check if TAS is alive and test session is able to download.
        """
        logging.info("Updating database status")
        updatedTASCount = self.TAS.validate()
        tasItems = self.TAS.getEveryItem()
        if not tasItems:
            logging.error("Failed to get TAS item. Aborting status validation")
            return
        updatedTestSessionCount = self.TESTSESSION.validate(tasItems)
        logging.debug("Updated TAS items : %d", updatedTASCount)
        logging.debug("Updated Test Session items : %d", updatedTestSessionCount)
        self.last_validated = datetime.date.today()

    # DELETE
    def deleteTestSession(self, tasInfo: dict, testSessionInfo: dict) -> bool:
        return NotImplementedError

    # Utility
    def checkIntegrity(self) -> int:
        """Checks if database is not corrupted. Checks for duplicate items
        or broken links with related items.

        Returns:
            int: Score of integrity testing
        """
        return NotImplementedError
        # logging.info("Checking integrity")

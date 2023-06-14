import logging
import sys

from .dbBase import DbBase


class DbTestCase(DbBase):
    def __init__(self, connection, userInfo):
        super().__init__(connection, userInfo)
        self.itemCount = -1
        self.setup()

    def setup(self) -> None:
        """Initial setup for TestCase table. If table doesn't
        exist, it will create a new table.
        """
        logging.info("Setting up TestCase table")
        if not super().isTableExist("TestCase"):
            if not self.create():
                logging.error("Failed to create TestCase table. Aborting...")
                sys.exit()
        self.itemCount = super().getItemCount("TestCase")
        if self.itemCount == -1:
            logging.warning("Failed to get item count of TestCase table")
        logging.info("Setup Finished | %d items in TestCase", self.itemCount)

    # CREATE
    def create(self) -> bool:
        """Creates TestCase table.

        Returns:
            bool: Result of create query
        """
        logging.debug("Creating TestCase table")
        query = """CREATE TABLE TestCase (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                testSessionId INT NOT NULL,
                testcase TEXT,
                boolean TEXT,
                numeric TEXT,
                string TEXT
            );"""
        super().execute(query)
        if not super().isTableExist("TestCase"):
            logging.error("Failed to create TestCase table")
            return False
        logging.debug("Success")
        return True

    # READ
    def getTestCase(self, testCase: str) -> list:
        logging.debug("Fetching test case %s", testCase)
        query = f"SELECT * FROM TestCase WHERE testcase='{testCase}';"
        items = super().select(query)
        if not items:
            logging.error("No items found with test case %s", testCase)
            return {}

        testCaseData = []
        for _, testSessionId, _, boolean, numeric, string in items:
            testCaseData.append(
                (testSessionId, eval(boolean), eval(numeric), eval(string))
            )
        logging.debug("Fetched %d items", len(testCaseData))
        return testCaseData

    def getTestCaseByTestSessionId(self, testSessionId: int) -> dict:
        logging.debug("Fetching test case data with test session id %d", testSessionId)
        query = f"SELECT testcase, boolean, numeric, string FROM TestCase WHERE testSessionId={testSessionId};"
        items = super().select(query)
        if not items:
            logging.debug("Failed to fetch test case data from database")
            return {}
        testCaseData = {}
        for testcase, boolean, numeric, string in items:
            testCaseData[testcase] = {
                "boolean": eval(boolean),
                "numeric": eval(numeric),
                "string": eval(string),
            }
        logging.debug("Fetched %d test cases", len(testCaseData))
        return testCaseData

    # UPDATE (INSERT)
    def insert(self, testSessionId: int, testSessionUrl: str) -> list:
        logging.debug("Adding new test case data")
        status, data = super().syncSendGetRequest(testSessionUrl)
        if not status:
            logging.error("Unable to fetch data from TAS")
            return []

        testCaseIds = self.isExist(testSessionId)
        if testCaseIds:
            logging.error("Same data exist. Aborting")
            return testCaseIds

        query = "INSERT INTO TestCase ('testSessionId', 'testcase', 'boolean', 'numeric', 'string') VALUES (?, ?, ?, ?, ?);"

        testSuiteData = self.parseTestSuiteData(testSessionId, data["tsGroups"])
        super().insert(query, testSuiteData, many=True)
        testCaseIds = self.isExist(testSessionId)
        if not testCaseIds:
            logging.error("Failed to insert new data")
            return []

        logging.debug("Success | IDs : %s", str(testCaseIds))
        self.itemCount = super().getItemCount("TestCase")
        return testCaseIds

    def update(self):
        return NotImplementedError

    # DELETE
    def delete(self):
        return NotImplementedError

    # Utility
    def isExist(self, testSessionId: int) -> list:
        logging.debug("Checking if item exist")
        query = f"SELECT id FROM TestCase WHERE testSessionId={testSessionId};"
        item = super().select(query)
        if not item:
            logging.debug("Item doesn't exist")
            return []
        ids = [_id[0] for _id in item]
        logging.debug("Item exist. ID : %s", str(ids))
        return ids

    def parseTestSuiteData(self, testSessionId: int, tsGroups: dict) -> list:
        tclData = {}

        for tsGroup in tsGroups:
            for tc, item in self.parseTestServerGroup(tsGroup).items():
                if tc not in tclData:
                    tclData[tc] = item
                else:
                    origTclData = tclData[tc]["boolean"]
                    newTclData = item["boolean"]
                    for tcl, value in newTclData.items():
                        if tcl not in origTclData:
                            tclData[tc]["boolean"][tcl] = value
                        else:
                            origValue = origTclData[tcl]
                            newValue = origValue or value
                            tclData[tc]["boolean"][tcl] = newValue

        result = []
        for testCase in tclData.keys():
            result.append(
                (
                    testSessionId,
                    testCase,
                    str(tclData[testCase]["boolean"]),
                    str(tclData[testCase]["numeric"]),
                    str(tclData[testCase]["string"]),
                )
            )

        return result

    def parseTestServerGroup(self, tsGroupData) -> dict:
        tsData = {}
        for testCase in tsGroupData["testCases"]:
            boolean, numeric, string = self.parseDict(testCase["parameters"])

            if testCase["type"] not in tsData:
                tsData[testCase["type"]] = {
                    "boolean": boolean,
                    "numeric": numeric,
                    "string": string,
                }
            else:
                # Merge boolean values of same testcase
                # newValue = origValue OR newValue
                for tcl, value in boolean.items():
                    if tcl not in tsData[testCase["type"]]:
                        tsData[testCase["type"]][tcl] = value
                    else:
                        origValue = tsData[testCase["type"]][tcl]
                        newValue = origValue or value
                        tsData[testCase["type"]][tcl] = newValue
        return tsData

    def parseDict(self, data, parent: str = None) -> tuple:
        boolean = {}
        numerical = {}
        string = {}
        for k, v in data.items():
            if parent is not None:
                k = "_".join([parent, k])
            v = self.typeEncoder(v)
            if isinstance(v, bool):
                boolean[k] = v
            elif isinstance(v, int) or isinstance(v, float):
                numerical[k] = v
            elif isinstance(v, str):
                string[k] = v if v != "" else None
            elif isinstance(v, dict):
                _b, _n, _s = self.parseDict(v, parent=k)
                boolean.update(_b)
                numerical.update(_n)
                string.update(_s)
            elif isinstance(v, list):
                for _v in v:
                    if isinstance(_v, dict):
                        _b, _n, _s = self.parseDict(_v, parent=k)
                        boolean.update(_b)
                        numerical.update(_n)
                        string.update(_s)
        return boolean, numerical, string

    def typeEncoder(self, value):
        if value in ["true", "Enabled"]:
            return True
        if value in ["false", "Disabled"]:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            try:
                value = int(value)
                return value
            except:
                pass
            try:
                value = float(value)
                return value
            except:
                pass
        return value

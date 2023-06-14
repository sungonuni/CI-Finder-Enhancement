import asyncio
import logging
import os
from platform import system
from zipfile import ZipFile

import aiofiles
import xmltodict


class Parser:
    def __init__(self, basePath: str = None, suiteReaderPath: str = None) -> None:
        # Path
        self.basePath = basePath
        self.suiteReaderPath = suiteReaderPath
        self.__check__()

    def __check__(self) -> None:
        """Checks if suite reader is valid. If valid, save suiteReaderPath
        as absolute path.

        Raises:
            FileNotFoundError: Raised when SuiteReader.jar doesn't exist.
        """
        if not os.path.isabs(self.suiteReaderPath):
            self.suiteReaderPath = os.path.abspath(self.suiteReaderPath)
        if not os.path.exists(self.suiteReaderPath):
            logging.error("Suite Reader does not exist at %s", self.suiteReaderPath)
            raise FileNotFoundError

    def parseKeywords(self, repository_item: dict) -> list:
        """Parses keywords from parsed STE file.

        Args:
            repository_item (dict): Repository item from parsed STE file

        Returns:
            list: list of keywords
        """
        if "ks" not in repository_item:
            return []
        if "k" not in repository_item["ks"]:
            return []
        if isinstance(repository_item["ks"]["k"], dict):
            repository_item["ks"]["k"] = [repository_item["ks"]["k"]]
        keywords = [item["@value"] for item in repository_item["ks"]["k"]]
        return keywords

    def parseTcl(self, tcTcls: dict) -> dict:
        """Parse TCL variables from parsed STE file.

        Args:
            tcTcls (dict): TCL variables inside such test case

        Returns:
            dict: Parsed tcl variables of boolean, numeric, string
        """
        if "nv" not in tcTcls:
            return {}, {}, {}
        if isinstance(tcTcls["nv"], dict):
            tcTcls["nv"] = [tcTcls["nv"]]
        return self.__parseDict__(tcTcls["nv"])

    def parseTestServerGroup(self, tsGroupData) -> list:
        """Parse test server group data from parsed STE.

        Args:
            tsGroupData (dict or list): Data of test cases and it's tcls inside
            same test server

        Returns:
            list: Parsed TCL data of such test server's test cases
        """
        tsData = []
        if isinstance(tsGroupData, dict):
            tsGroupData = [tsGroupData]
        for testCase in tsGroupData:
            logging.debug("Working with TestCase %s", testCase["@root_name"])
            boolean = {}
            numeric = {}
            string = {}

            _b, _n, _s = self.parseTcl(testCase["p2s"])
            boolean.update(_b)
            numeric.update(_n)
            string.update(_s)

            tsData.append([testCase["@root_name"], boolean, numeric, string])
        return tsData

    def parseXml(self, xmlData: dict) -> dict:
        """Core part of parsing Sessions.xml. It generates same data schema
        as TAS RESTful API, in convience for comparing with test sessions
        inside TAS.
        * Caveats
        If same test cases exist in single test suite, for boolean type
        tcl variables, it will merge configuration value with OR method.
        If any test case has TRUE for such TCL variable, it will be parsed
        as TRUE. For string / numeric data, it will fetch FIRST test case
        data.

        Args:
            xmlData (dict): XML data of input STE

        Returns:
            dict: Parsed item of input STE
        """
        # Create DataFrame
        steData = {}
        # Parse basic information
        logging.debug("Extracting basic information")
        item = xmlData["sessions"]["master_session"]["repository_item"]
        steData["name"] = item["@name"]
        steData["description"] = item["d"]
        steData["keywords"] = self.parseKeywords(item)

        # Parse Testcase/TCL information
        logging.debug("Extracting tcl information")
        steData["tclData"] = {}
        scenario = xmlData["sessions"]["master_session"]["ts_sessions"]["scenario"]
        if isinstance(scenario, dict):
            scenario = [scenario]
        for tsItem in scenario:
            tsData = self.parseTestServerGroup(tsItem["scripts"]["ssecoast_script"])
            for tc, boolean, numeric, string in tsData:
                if tc not in steData["tclData"]:
                    steData["tclData"][tc] = {
                        "boolean": boolean,
                        "numeric": numeric,
                        "string": string,
                    }
                else:
                    # Merge boolean values of same testcase
                    # newValue = origValue OR newValue
                    for tcl, value in boolean.items():
                        if tcl not in steData["tclData"][tc]["boolean"]:
                            steData["tclData"][tc]["boolean"][tcl] = value
                        else:
                            origValue = steData["tclData"][tc]["boolean"][tcl]
                            newValue = origValue or value
                            steData["tclData"][tc]["boolean"][tcl] = newValue
        return steData

    async def parseSte(self, steFile: str, tmpDir: str = "tmp") -> dict:
        """Core part of parsing *.ste file. It creates a temporary folder
        named as "ste_{name}", and will run SuiteReader.jar as subprocess.
        It's non-blocking. After subprocess is over, it will parse XML file.

        When it's done parsing and retrieving test suite data, it will delete
        temporary folder from server.

        Args:
            steFile (str): Path to steFile
            tmpDir (str, optional): Path to temporary folder. Defaults to "tmp".

        Returns:
            dict: Parsed STE data
        """
        logging.info("Parsing STE at %s", steFile)

        # parse ste file
        logging.debug("Current working directory : %s", self.basePath)

        # create temp directory
        steName = os.path.split(steFile)[-1][:-4]
        parsedPath = os.path.join(self.basePath, tmpDir, f"ste_{steName}")
        os.mkdir(parsedPath)
        os.chdir(parsedPath)
        logging.debug("Parsing working directory : %s", parsedPath)

        # run SuiteReader for this ste file
        logging.debug("Running SuiteReader")
        cmd = f'echo -ne | java -jar {self.suiteReaderPath} "{steFile}"'
        process = await asyncio.create_subprocess_shell(
            cmd, stderr=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE
        )
        await process.wait()
        stdout, stderr = await process.communicate()
        logging.info(f"SuiteReader exited with {process.returncode}]")
        if stdout:
            logging.debug(f"[SuiteReader]\n{stdout.decode()}")
        if stderr:
            logging.error(f"[SuiteReader]\n{stderr.decode()}")

        logging.debug("Reading 'Sessions.xml' at %s", parsedPath)
        sessionFilePath = os.path.join(parsedPath, "Sessions.xml")
        async with aiofiles.open(sessionFilePath, "r") as f:
            xml = await f.read()
        xmlData = xmltodict.parse(xml)

        logging.debug("Parsing xml data")
        steData = self.parseXml(xmlData)

        # change dir to the temp dir
        os.chdir(self.basePath)
        logging.debug("Current working directory : %s", self.basePath)

        logging.debug("Deleting temporary file")
        isDeleted = await self.__deleteDir__(parsedPath)
        if not isDeleted:
            logging.warning("Path %s is not deleted", parsedPath)

        return steData

    async def __deleteDir__(self, path: str) -> bool:
        """Deletes folder at given path.

        Args:
            path (str): Path to folder you want to delete.

        Returns:
            bool: True if successfully removed. Else False.
        """
        logging.debug("Deleting %s", path)
        if system() == "Windows":
            cmd = f'RD /S /Q "{path}"'
        else:
            cmd = f'rm -rf "{path}"'

        proc = await asyncio.create_subprocess_shell(
            cmd, stderr=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            logging.debug(f"{stdout.decode()}")
        if stderr:
            logging.error(f"{stderr.decode()}")

        if proc.returncode != 0:
            logging.debug("Deleting %s Failed", path)
            return False
        logging.debug("Deteting %s Success", path)
        return True

    def __parseDict__(self, data: dict, parent: str = None) -> tuple:
        """Utility to parse dictionary. Separates TCL variables
        into boolean, numeric, and string type. If parent is given,
        it will parse tcl name as parent_tclName.

        Args:
            data (dict): TCL data to parse
            parent (dict, optional): If parent name is given, it will
            parse tcl name as parent_tclName. Defaults to None.

        Returns:
            tuple: tuple of dictionarys for boolean, numeric, string type TCL variables.
        """
        boolean = {}
        numerical = {}
        string = {}
        for pair in data:
            k = pair["@n"]
            v = pair["@v"]
            if parent is not None:
                k = "_".join([parent, k])
            v = self.__typeEncoder__(v)
            if isinstance(v, bool):
                boolean[k] = v
            elif isinstance(v, int) or isinstance(v, float):
                numerical[k] = v
            else:
                string[k] = v if v != "" else None
        return boolean, numerical, string

    def __typeEncoder__(self, value):
        """Encodes string data to native python values.

        Args:
            value (str): string value

        Returns:
            _type_ : Encoded value for correct type.
        """
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

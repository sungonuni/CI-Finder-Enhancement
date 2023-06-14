import logging
import re
from heapq import nlargest

import numpy as np


class Finder:
    def __init__(self, db) -> None:
        self.db = db

    def find(
        self, inputSte, filterConfigBoolean: dict = {}, filterConfigString: dict = {}
    ) -> dict:
        """Calculates test suite score using inputSTE.
        It uses filterConfigBoolean and filerConfigString to constraint search results
        to "MUST" include TCLs inside filters.
        It also enforces search results to have every test case that is mentioned in filters.
        For example, if filterConfigBoolean has {"MME Nodal" : ["VolteEn"], "MME Node" : ["S1MmeIpsecEn"]},
        search results must include "MME Nodal" AND "MME Node".

        Args:
            inputSte (dict): client's parsed STE data
            filterConfigBoolean (dict, optional): Filter for boolean type TCL variables. Defaults to {}.
            filterConfigString (dict, optional): Filter for string type TCL variables. Defaults to {}.

        Returns:
            dict: dictionary of key[testSessionId] : value[Score] accumulated for each test case.
        """
        logging.info(f"Finding similar test suites with {inputSte['name']}")
        scores = {}
        ensureTestCase = []
        compareString = False
        for idx, (testCase, inputTcData) in enumerate(inputSte["tclData"].items()):
            logging.debug(f"Calculating testcase {testCase}")
            dbData = self.db.getTestCaseData(testCase)
            if not dbData:
                logging.error("%s has no items in database", testCase)
                continue

            inputStrData = inputTcData["string"]
            inputTclData = inputTcData["boolean"]
            inputTcls = set(inputTclData.keys())
            compareString = "TestActivity" in inputStrData
            logging.debug("Compare string - %s", compareString)

            filterTcls = filterConfigBoolean.get(testCase, None)
            filterStrs = filterConfigString.get(testCase, None)
            if filterTcls is not None or filterStrs is not None:
                ensureTestCase.append(testCase)

            for testSessionId, targetTclData, targetNumData, targetStrData in dbData:
                targetTcls = set(targetTclData.keys())
                if filterTcls is not None:
                    if not set(filterTcls).issubset(targetTcls):
                        continue
                    if not self.isMatch(filterTcls, inputTclData, targetTclData):
                        continue

                targetStrs = set(targetStrData.keys())
                if filterStrs is not None:
                    if not set(filterStrs).issubset(targetStrs):
                        continue
                    if not self.isMatch(filterStrs, inputStrData, targetStrData):
                        continue

                # Calculate String TCL matching score
                strScore = 0
                if compareString:
                    strScore = self.compareStrData(inputStrData, targetStrData)
                    if strScore == -1:
                        continue

                # Calculate score
                intersectTcls = list(inputTcls.intersection(targetTcls))
                inputVector = self.vectorize(intersectTcls, inputTclData)
                targetVector = self.vectorize(intersectTcls, targetTclData)
                score = np.sum(inputVector == targetVector)

                # Accumulate score
                if testSessionId not in scores:
                    scores[testSessionId] = {
                        "testCase": [testCase],
                        "boolean": score,
                        "string": strScore,
                    }
                else:
                    scores[testSessionId]["testCase"].append(testCase)
                    scores[testSessionId]["boolean"] += score
                    scores[testSessionId]["string"] += strScore
        if ensureTestCase:
            logging.debug(
                "Ensuring search result to include %s testcases", str(ensureTestCase)
            )
            newScores = {}
            for ciTest, item in scores.items():
                if set(ensureTestCase).issubset(set(item["testCase"])):
                    newScores[ciTest] = item
            scores = newScores

        return scores

    def compareStrData(self, inputStrData: dict, targetStrData: dict) -> int:
        """Compares string type TCL variables form input and target STE.
        Will return -1 if either input or target doens't have "TestActivity".

        Args:
            inputStrData (dict): String type TCL variables from InputSte
            targetStrData (dict): String type TCL variables from TargetSte

        Returns:
            int: Number of matching TCL variables
        """
        logging.debug("Comparing String TCL variables")
        try:
            inputTestActivity = inputStrData["TestActivity"]
        except KeyError:
            return -1

        try:
            targetTestActivity = targetStrData["TestActivity"]
        except KeyError:
            return -1

        if inputTestActivity != targetTestActivity:
            return -1

        logging.debug("Found target test suite with matching test activity")
        inputStrData = self.stringFilter(inputStrData)
        targetStrData = self.stringFilter(targetStrData)

        score = 0
        for tcl, value in inputStrData.items():
            if tcl not in targetStrData:
                continue
            if value == targetStrData[tcl]:
                score += 1
        logging.debug("Score : %d", score)

        return score

    def analyzeTclDifference(self, inputTclData: dict, targetTclData: dict) -> dict:
        """Analyze difference between input and target STE data.
        Compares matching / mismatching / onlyInput / onlyTarget cases.
        It compares boolean and string tcl variables.

        Args:
            inputTclData (dict): TCL data from input
            targetTclData (dict): TCL data from client

        Returns:
            _type_ (dict): analysis result of matching, mismatching, onlyInput,
            onlyTarget tcl variables.
        """
        logging.debug("Analyzing difference between input and target CI test suite")

        def analyzeTcData(inputTcl, targetTcl):
            difference = {}
            intersection = list(set(inputTcl.keys()).intersection(targetTcl.keys()))

            difference["match"] = {}
            difference["mismatch"] = {}
            for tcl in intersection:
                if inputTcl[tcl] == targetTcl[tcl]:
                    difference["match"][tcl] = inputTcl[tcl]
                else:
                    difference["mismatch"][tcl] = {
                        "input": inputTcl[tcl],
                        "target": targetTcl[tcl],
                    }
            difference["onlyInput"] = {}
            for tcl in set(inputTcl.keys()).difference(intersection):
                difference["onlyInput"][tcl] = inputTcl[tcl]
            difference["onlyCI"] = {}
            for tcl in set(targetTcl.keys()).difference(intersection):
                difference["onlyCI"][tcl] = targetTcl[tcl]
            return difference

        # Compare test cases
        inputTestCases = set(inputTclData.keys())
        targetTestCases = set(targetTclData.keys())
        matchTestCases = inputTestCases.intersection(targetTestCases)

        analysis = {}
        for testCase in matchTestCases:
            analysis[testCase] = {
                "boolean": analyzeTcData(
                    inputTclData[testCase]["boolean"],
                    targetTclData[testCase]["boolean"],
                ),
                "string": {},
            }
            inputStrData = inputTclData[testCase]["string"]
            targetStrData = targetTclData[testCase]["string"]
            if "TestActivity" not in inputStrData:
                continue
            logging.debug(
                "Found TestActivity inside input data : %s",
                inputStrData["TestActivity"],
            )
            if "TestActivity" not in targetStrData:
                continue
            logging.debug(
                "Found TestActivity inside target data : %s",
                targetStrData["TestActivity"],
            )
            analysis[testCase]["string"] = analyzeTcData(
                self.stringFilter(inputStrData), self.stringFilter(targetStrData)
            )

            analysis[testCase]["string"]["TestActivity"] = {
                "input": targetStrData["TestActivity"],
                "target": targetStrData["TestActivity"],
            }

        return analysis

    def vectorize(self, tcls: list, data: dict) -> np.ndarray:
        """Vectorize data(dict) using index of tcls(list). If same tcls
        are given, resulting vectors should have same index.

        Args:
            tcls (list): list of tcl variables
            data (dict): dictionary of tcl variables including name and value

        Returns:
            np.ndarray: vectorized item of data
        """
        return np.array([data[tcl] for tcl in tcls])

    def isMatch(self, filterTargets: list, inputData: dict, targetData: dict) -> bool:
        for filterTarget in filterTargets:
            inputValue = inputData[filterTarget]
            targetValue = targetData[filterTarget]
            if inputValue != targetValue:
                return False
        return True

    def getTopk(self, scores: dict, topk: int = 5) -> dict:
        """Selects top K items from scores(dict). When multiple items
        have same score, then it will acknowledge those items also.
        First, we sort the scores in ascending manner, cuts at topk,
        get score from that index, and get all items over given threshold.

        Args:
            scores (dict): Dictionary of {testSessionId : Score}
            topk (int, optional): Top K value. Defaults to 5.

        Returns:
            dict: Resulting top k items from scores(dict). Could be larger than
            topk value since we include every items that is higer than threshold.
        """
        logging.debug("Calculating top %d CI tests", topk)

        scores = {
            name: score["boolean"] + score["string"] for name, score in scores.items()
        }

        topkScores = list(set(nlargest(topk, scores.values())))
        topScore = max(topkScores)
        topkItems = {
            name: score for name, score in scores.items() if score in topkScores
        }
        logging.debug("Found %d items in top %d", len(topkItems), topk)

        return topkItems, topScore

    def stringFilter(self, data: dict) -> dict:
        """Filter out unnecessary string from string TCL dictionary.
        It filters out BYTE(4 digits), BYTES(0x...), address(www.sprient.com),
        ipv4, ipv6 and port(#(N000)) and number(#(000)) patterns.

        Args:
            data (dict): string TCL dictionary

        Returns:
            dict: Filtered string TCL dictionary
        """
        finalDict = {}
        # Filter out bytes data
        bytesPattern = re.compile(r"^0x[a-fA-F0-9_]+")  # 0x0000...
        bytePattern = re.compile(r"^[a-fA-F0-9_]{4}")  # i.e., FFFF
        addressPattern = re.compile(
            r"[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
        )
        ipv6Pattern = re.compile(
            r"(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))"
        )
        ipv4Pattern = re.compile(
            r"((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])"
        )
        portPattern = re.compile(r"[a-zA-Z]*#\(N[a-zA-Z0-9 /]+\)")
        numberPattern = re.compile(r"[a-zA-Z]*#\([a-zA-Z0-9 /]+\)")
        for tcl, tclString in data.items():
            if tclString in ["none", None]:
                continue
            elif tcl in ["TestType", "CommandSequence", "TestActivity"] or "_" in tcl:
                continue
            elif bytesPattern.match(tclString):
                continue
            elif bytePattern.match(tclString):
                continue
            elif addressPattern.match(tclString):
                continue
            elif portPattern.match(tclString):
                continue
            elif numberPattern.match(tclString):
                continue
            elif ipv4Pattern.match(tclString):
                continue
            elif ipv6Pattern.match(tclString):
                continue
            finalDict[tcl] = tclString
        return finalDict

import logging
import sqlite3

import aiohttp
import requests


class DbBase:
    """
    Base Class for Database
    """

    def __init__(self, connection: sqlite3.Connection, userInfo: dict) -> None:
        self.connection = connection
        self.userInfo = userInfo

    def select(self, query: str) -> list:
        """select
        Executes select query with error handling

        Args:
            query (str): SELECT query to execute

        Returns:
            list: fetched list. Returns empty list when no items exist
        """
        logging.debug("Executing SELECT query : %s", query)
        try:
            with self.connection:
                item = self.connection.execute(query).fetchall()
        except sqlite3.Error:
            logging.error(f"Error while select query.\nQuery : {query}")
            return []
        logging.debug("Success")
        return item

    def insert(self, query: str, item: tuple, many=False) -> int:
        """insert
        Executes INSERT query with error handling

        Args:
            query (str): INSERT query to execute
            item (tuple): value(s) used for INSERT query
            many (bool, optional): runs 'executemany' when set to True. Defaults to False.

        Returns:
            int: Affected number of rows
        """
        logging.debug("Executing INSERT query : %s", query)
        try:
            with self.connection:
                if many:
                    count = self.connection.executemany(query, item).rowcount
                else:
                    count = self.connection.execute(query, item).rowcount
        except sqlite3.Error:
            logging.error(f"Error while insert query.\nQuery : {query}")
            return -1
        logging.debug("Success")
        return count

    def execute(self, query: str) -> int:
        """execute
        Executes query with error handling

        Args:
            query (str): query to execute

        Returns:
            int: Affected number of rows
        """
        logging.debug("Executing query")
        try:
            with self.connection:
                count = self.connection.execute(query).rowcount
        except sqlite3.Error:
            logging.error(f"Error while execute query.\nQuery : {query}")
            return -1
        logging.debug("Success")
        return count

    def isTableExist(self, tableName: str) -> bool:
        """isTableExist
        Checks if table named 'tableName' exist in Database

        Args:
            tableName (str): Name of table

        Returns:
            bool: True if exist, False if doesn't exist.
        """
        logging.debug("Checking if table exist")
        query = (
            f"SELECT name FROM sqlite_master WHERE type='table' and name='{tableName}';"
        )
        try:
            with self.connection:
                item = self.connection.execute(query).fetchone()
        except sqlite3.Error:
            logging.error(f"Error while checking table exist.\nQuery : {query}")
            return -1
        if not item:
            logging.debug("Table %s doens't exist", tableName)
            return False
        logging.debug("Table %s exist", tableName)
        return True

    def getItemCount(self, tableName: str) -> int:
        """getItemCount

        Args:
            tableName (str): Name of table

        Returns:
            int: number of items in table 'tableName'
        """
        logging.debug("Fetching item count from table %s", tableName)
        query = f"SELECT id FROM {tableName}"
        try:
            with self.connection:
                item = self.connection.execute(query).fetchall()
        except sqlite3.Error:
            logging.error(f"Error while fetching item count.\nQuery : {query}")
            return -1
        logging.debug("Success : %d", len(item))
        return len(item)

    def syncSendGetRequest(self, url: str) -> tuple:
        """sendGetRequest
        Sends GET request to given URL with error handling

        Args:
            url (str): URL to get request

        Returns:
            tuple: Status and JSON item.
        """
        logging.debug("Sending HTTP GET request")
        auth = (self.userInfo["id"], self.userInfo["pw"])
        try:
            r = requests.get(url, auth=auth)
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            logging.error("HTTP Error : %s [URL: %s]", r.status_code, url)
            return False, {}
        return True, r.json()

    async def asyncSendGetRequest(self, url: str) -> tuple:
        """asyncSendGetRequest
        Send asynchronous GET request to given URL with error handling

        Args:
            url (str): URL to get request

        Returns:
            tuple: Status and JSON item
        """
        logging.debug("Sending HTTP GET request")
        auth = (self.userInfo["id"], self.userInfo["pw"])
        try:
            async with aiohttp.ClientSession(
                headers={"Authorization": "Basic c21zOmExYjJjM2Q0"},
                raise_for_status=True,
            ) as session:
                async with session.post(url) as response:
                    item = await response.read()
        except aiohttp.ClientError as e:
            logging.error("HTTP Error : %s [URL: %s]", e.status, url)
            return False, None
        return True, item

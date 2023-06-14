import json
import logging
from uuid import UUID

import aiofiles
import numpy as np
from fastapi import UploadFile

CHUNK_SIZE = 1024 * 1024


class Encoder(json.JSONEncoder):
    """
    Encodes numpy types to native python types.
    """

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, UUID):
            return obj.hex
        return super(Encoder, self).default(obj)


def setLogger(verbose=0):
    """Set logging format and level.
    verbose = 0 : Error. Default.
    verbose = 1 : Warning.
    verbose = 2 : Info.
    verbose = 3 : Debug

    Args:
        verbose (int, optional): Logging level. Defaults to 0.
    """
    FORMAT = (
        "%(asctime)s | %(filename)15s | %(funcName)20s | %(levelname)10s | %(message)s"
    )
    LEVEL = logging.ERROR
    if verbose == 1:
        LEVEL = logging.WARNING
    elif verbose == 2:
        LEVEL = logging.INFO
    elif verbose == 3:
        LEVEL = logging.DEBUG
    logging.basicConfig(
        format=FORMAT,
        level=LEVEL,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def writeFile(file: UploadFile, filePath: str) -> bool:
    """Write file from client to file system asynchronously.

    Args:
        file (UploadFile): STE file
        filePath (str): Path to STE file

    Returns:
        bool: True if no error occurred.
    """
    try:
        async with aiofiles.open(filePath, "wb") as f:
            while chunk := await file.read(CHUNK_SIZE):
                await f.write(chunk)
    except Exception:
        logging.error("Failed reading client STE file.")
        return False
    finally:
        await file.close()

    return True

from enum import Enum
from glob import iglob
from pathlib import Path
from typing import Iterable, Literal, NotRequired, Optional
from random import random
import asyncio
import aiohttp
import json
import orjson
import aiofiles
from datetime import datetime
import os, io
from tabulate import tabulate
from typing import TypedDict

from back.app.services.utils import read_last_line


URL = "https://api-krs.ms.gov.pl/api/krs/OdpisPelny/{id}?rejestr={registry}&format=json"
Registry = Literal["P", "S"]


class Status(Enum):
    OK = "OK"
    LIQ = "LIQ"
    ERR = "ERR"
    NOT_FOUND = "NOT_FOUND"


class IndexOrderInterface(TypedDict):
    start: NotRequired[int]
    end: NotRequired[int]
    indexes: NotRequired[Iterable[str]]


class FileLogger:
    def __init__(self, file_name: str):
        file_path = Path(file_name)
        if not file_path.parent.exists():
            os.system(f"mkdir -p {file_path.parent}")
        if not Path(file_name).exists():
            os.system(f"touch {file_name}")
        self.file_name = file_name

    async def log(self, index, status: Status, msg=""):
        async with aiofiles.open(self.file_name, "a") as ff:
            await ff.write(f"[{datetime.now()}] - {index} - {status.value} - {msg}\n")


async def process_response(index, session, registry, dump_path, logger: FileLogger):
    try:
        url = URL.format(id=index, registry=registry)
        async with session.get(url) as response:
            resp_text = await response.text()
            if response.status == 200:
                data = orjson.loads(resp_text)
                try:
                    entries = data["odpis"]["naglowekP"]["wpis"]
                except KeyError:  # Catching potential KeyError if the keys don't exist
                    await logger.log(
                        index,
                        Status.ERR,
                        f"KeyError in JSON response structure: {resp_text}",
                    )
                    return
                except orjson.JSONDecodeError:  # Catching JSON decoding errors
                    await logger.log(index, Status.ERR, f"JSONDecodeError: {resp_text}")
                    return

                if entries and "WYKREŚLENIE" in entries[-1]["opis"]:
                    return await logger.log(index, Status.LIQ)
                else:
                    async with aiofiles.open(
                        f"{dump_path}/{index}.json", mode="w"
                    ) as new_json:
                        await new_json.write(orjson.dumps(data).decode())
                    return await logger.log(index, Status.OK)
            return await logger.log(index, Status.NOT_FOUND)

    except aiohttp.ClientError as e:
        await logger.log(index, Status.ERR, f"ClientError: {str(e)}")
    except Exception as exc:
        await logger.log(index, Status.ERR, f"UnexpectedError: {str(exc)}")


def get_summary_from_log(log_file: str):
    ok_indexes = []
    missing_indexes = []
    liquidated_indexes = []
    errored_indexes: list[str] = []

    print("* Parsing logs...")
    for line in io.open(log_file, "r").readlines():
        dt, idx, status, msg = line.split(" - ", 3)
        if status == Status.OK:
            ok_indexes.append(idx)
        elif status == Status.NOT_FOUND:
            missing_indexes.append(idx)
        elif status == Status.LIQ:
            liquidated_indexes.append(idx)
        elif status == Status.ERR:
            errored_indexes.append(idx)

    return ok_indexes, missing_indexes, liquidated_indexes, errored_indexes


async def verify_post_run_integrity(log_file: str, dump_folder: Path):
    """Read all lines from the log file, tally up the OK statuses and ensure they match the output count.
    In case of discrepancies, flag them and re-run them.
    """
    dump_pat = dump_folder / "*.json"
    all_output_indexes = {Path(file).stem for file in iglob(str(dump_pat))}

    ok_indexes, missing_indexes, liquidated_indexes, errored_indexes = (
        get_summary_from_log(log_file)
    )
    ok_indexes_set = set(ok_indexes)  # Convert list to set for efficient lookup

    _, min_file, max_file = dump_folder.stem.split("-")
    min_file_idx = int(min_file) * 1000
    max_file_idx = int(max_file) * 1000 + 1000

    print("* Verifying output...")

    # Check for any missing files that were marked as OK in the logs
    missing_files = ok_indexes_set - all_output_indexes
    if missing_files:
        print(
            f"* Warning: Missing files for indexes marked as OK in logs: {missing_files}"
        )

    # retry the errored records
    if errored_indexes:
        print(f"* Found {len(errored_indexes)} errored indexes. Retrying...")
        err_run_logger = FileLogger(
            f"/tmp/logs/err-rerun-{min_file_idx}-{max_file_idx}.log"
        )
        await run({"indexes": errored_indexes}, dump_folder, err_run_logger)
        ok_indexes, missing_indexes, liquidated_indexes, new_errors = (
            get_summary_from_log(err_run_logger.file_name)
        )
        if new_errors:
            # suspend the run, analyze the errors manually
            print(
                f"* Found {len(new_errors)} errored indexes after rerun. View them at {err_run_logger.file_name}. Suspending run..."
            )
            return

    table = [
        ["OK", len(ok_indexes)],
        ["Missing", len(missing_indexes)],
        ["Liquidated", len(liquidated_indexes)],
        ["Errored", len(errored_indexes)],
        [
            "Total",
            total := len(ok_indexes)
            + len(missing_indexes)
            + len(liquidated_indexes)
            + len(errored_indexes),
        ],
        ["Missing Files", len(missing_files)]
    ]
    print(
        f"* Intended range was {min_file_idx} - {max_file_idx}, which is {max_file_idx - min_file_idx} indexes."
    )
    print(tabulate(table))


async def run(
    config: IndexOrderInterface,
    dump_path: Path,
    logger: FileLogger,
    registry: Registry = "P",
):
    async with aiohttp.ClientSession() as session:
        tasks = []
        if (start := config.get("start")) is not None and (end := config.get("end")):
            iterable = range(start, end)
        elif not (iterable := config.get("indexes")):
            iterable = []
        for index in iterable:
            task = asyncio.create_task(
                process_response(index, session, registry, dump_path, logger)
            )
            tasks.append(task)
            await asyncio.sleep(random() * 0.2 + 0.2)

        await asyncio.gather(*tasks)
        print("Finished! Verifying now...")
    await verify_post_run_integrity(logger.file_name, dump_path)


async def run_full(
    registry: Registry = "P", start=500000, end=600000, dump_folder: Path = Path("/tmp")
):
    dump_path = dump_folder / f"raw-{int(start/1000)}-{int(end/1000)}"
    logger = FileLogger(f"/tmp/logs/log-{start}-{end}.log")

    if not Path(dump_path).exists():
        os.system(f"mkdir -p {dump_path}")

    await run({"start": start, "end": end}, dump_path, logger, registry)

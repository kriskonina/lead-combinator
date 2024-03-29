from datetime import datetime
from enum import Enum
import os
import asyncio
from random import random
from glob import glob
from pathlib import Path

from back.app.services.krs import FileLogger, process_response


def get_gap_files(folder: Path):
    files = [
        int(f.rsplit("/", 1)[1].split(".")[0]) for f in glob(str(folder / "*.json"))
    ]
    _, min_file, max_file = folder.stem.split("-")
    min_file_idx = int(min_file) * 1000
    max_file_idx = int(max_file) * 1000 + 1000
    for idx in range(min_file_idx, max_file_idx):
        if idx not in files:
            yield idx


async def verify(folder_name: str):
    folder = Path(folder_name)
    if not folder.exists():
        raise ValueError(f"Folder {folder} does not exist")
    _, min_file, max_file = folder.stem.split("-")

    log_file = f"/tmp/missing/logs/verif-{min_file}-{max_file}.log"
    os.system("mkdir -p /tmp/missing")

    dump_path = f"/tmp/missing/{min_file}-{max_file}"
    logger = FileLogger(log_file)

    if not Path(dump_path).exists():
        os.mkdir(dump_path)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for index in get_gap_files(folder):
            print(f'\rProcessing missing: {index}.json', end='')
            task = asyncio.create_task(process_response(index, session, 'P', dump_path, logger))
            tasks.append(task)
            await asyncio.sleep(random() * 0.1 + 0.03)  # Simulate variable delay

        await asyncio.gather(*tasks)

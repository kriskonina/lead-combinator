from pathlib import Path
from typing import Literal
from random import random
import asyncio
import aiohttp
import json
import orjson
import aiofiles
from datetime import datetime
import os

MAIN_PATH = "/Users/joekavalieri/git/kappados/lead-combinator/krs/"
URL = 'https://api-krs.ms.gov.pl/api/krs/OdpisPelny/{id}?rejestr={registry}&format=json'
Registry = Literal['P', 'S']


class FileLogger:
    def __init__(self, file_name: str):
        self.file_name = file_name
        if Path(file_name).exists():
            os.system(f"touch {file_name}")

    async def log(self, index, msg):
        async with aiofiles.open(self.file_name, "a") as ff:
            await ff.write(
                f"[{datetime.now()}] - {index} - {msg}\n"
            )


async def process_response(index, session, registry, dump_path, logger: FileLogger):
    url = URL.format(id=index, registry=registry)
    try:
        async with session.get(url) as response:
            resp_text = await response.text()
            if response.status == 200:
                data = orjson.loads(resp_text)
                try:
                    entries = data['odpis']['naglowekP']['wpis']
                except Exception:
                    await logger.log(index, f'IndexError: {data}')
                    return

                if entries and 'WYKREŚLENIE' in entries[-1]['opis']:
                    return await logger.log(index, 'LIQ')
                else:
                    async with aiofiles.open(f'{dump_path}/{index}.json', mode='w') as new_json:
                        await new_json.write(orjson.dumps(data).decode())
                    return await logger.log(index, 'OK')
            return await logger.log(index, 'NOT_FOUND')
    except Exception as exc:
        await logger.log(index, f"ERR: {exc}")


async def main(registry: Registry='P', start=500000, end=600000):
    dump_path = f'{MAIN_PATH}raw-{start/1000}-{end/1000}'
    logger = FileLogger('/tmp/log-{start}-{end}.log')

    if not Path(dump_path).exists():
        os.mkdir(dump_path)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for index in range(start, end):
            task = asyncio.create_task(process_response(index, session, registry, dump_path, logger))
            tasks.append(task)
            await asyncio.sleep(random() * 0.1 + 0.03)  # Simulate variable delay

        await asyncio.gather(*tasks)
        print("Finished!")

from typing import Literal
from random import random
import asyncio
import aiohttp
import json
import orjson
import aiofiles
from datetime import datetime
# Currently from 200-160000
MAIN_PATH = './'
URL = 'https://api-krs.ms.gov.pl/api/krs/OdpisPelny/{id}?rejestr={registry}&format=json'
Registry = Literal['P', 'S']



async def process_response(index, session, registry, dump_path, err_path):
    url = URL.format(id=index, registry=registry)
    async with session.get(url) as response:
        resp_text = await response.text()
        status = 'valid'
        if response.status == 200:
            data = orjson.loads(resp_text)

            try:
                entries = data['odpis']['naglowekP']['wpis']
            except Exception:
                json.dump(data, open(f'{err_path}/{index}.json', 'w'))
                return

            if entries and 'WYKREŚLENIE' in entries[-1]['opis']:
                status = 'deleted'
            else:
                async with aiofiles.open(f'{dump_path}/{index}.json', mode='w') as new_json:
                    await new_json.write(orjson.dumps(data).decode())
        else:
            status = 'not found'

        print(f"\rRequested {index}.json @ {datetime.now()} --> {status}", end='', flush=True)

async def main(registry: Registry='P', start=400000, end=500000):
    dump_path = f'{MAIN_PATH}raw'
    err_path = f'{MAIN_PATH}err'

    async with aiohttp.ClientSession() as session:
        tasks = []
        for index in range(start, end):
            task = asyncio.create_task(process_response(index, session, registry, dump_path, err_path))
            tasks.append(task)
            await asyncio.sleep(random() * 0.1 + 0.03)  # Simulate variable delay

        await asyncio.gather(*tasks)
        print("Finished!")

asyncio.run(main())
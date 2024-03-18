import asyncio
from pathlib import Path

from app.services.krs import run_full

asyncio.run(
    run_full(
        "P",
        0,
        99_999,
        Path("/tmp/ubuntu/"),
    )
)
# asyncio.run(verify("/Users/joekavalieri/git/kappados/lead-combinator/krs/raw-200-299"))

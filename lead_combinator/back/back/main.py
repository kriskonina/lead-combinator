import asyncio
from pathlib import Path

from app.services.krs import run_full

asyncio.run(
    run_full(
        "P",
        700_000,
        799_999,
        Path("/Users/joekavalieri/git/kappados/lead-combinator/krs/"),
    )
)
# asyncio.run(verify("/Users/joekavalieri/git/kappados/lead-combinator/krs/raw-200-299"))

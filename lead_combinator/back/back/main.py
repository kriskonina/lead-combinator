import asyncio
from pathlib import Path

from app.services.krs import run_full

asyncio.run(
    run_full(
        "P",
        100000,
        199_999,
        Path("/tmp/ubuntu/"),
    )
)
# asyncio.run(verify("/Users/joekavalieri/git/kappados/lead-combinator/krs/raw-200-299"))

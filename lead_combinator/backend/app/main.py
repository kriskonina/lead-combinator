import asyncio
from services.business_retriever.pl.verif import main


DIR = "/Users/joekavalieri/git/kappados/lead-combinator/krs/raw-0-99"
asyncio.run(
    main(DIR)
)

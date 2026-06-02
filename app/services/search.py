import aiohttp
from typing import List
import os
from exa_py import Exa
from dotenv import load_dotenv

load_dotenv()

exa = Exa(api_key=os.getenv("EXA_API_KEY"))

# =========================================================
# SEARCH FUNCTION
# =========================================================


from typing import List


async def exa_search_snippets(
    queries: List[str],
    max_results: int = 3
) -> List[str]:

    all_snippets = []

    for q in queries:

        result = exa.search(
            q,
            type="auto",
            num_results=max_results,
            contents={"text":True}
        )

        for item in result.results:

            if not item.text:
                continue

            snippet = item.text.strip()

            if snippet:
                # hard compression for reasoning stability
                all_snippets.append(snippet[:300])

    # enforce strict retrieval budget (prevents context drift)
    return all_snippets[:6]
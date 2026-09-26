import asyncio
import os
from app.routers.tools import _llm_json

async def test_llm():
    try:
        messages = [{"role": "user", "content": "Respond with JSON: {\"test\": \"hello\"}"}]
        res = await _llm_json(messages)
        print("Success:", res)
    except Exception as e:
        print("Error:", type(e).__name__, str(e))

if __name__ == "__main__":
    asyncio.run(test_llm())

import asyncio
from crawl4ai import *
import json  

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://huggingface.co/docs/smolagents/index",
        )
        with open("data.json" , "w" , encoding="utf-8") as f : 
            json.dump(result.markdown , f )
        print(result.markdown)

if __name__ == "__main__":
    asyncio.run(main())
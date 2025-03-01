import asyncio
from crawl4ai import *
import json  
from crawl4ai import AsyncWebCrawler


async def main():
    async with AsyncWebCrawler() as crawler:
        # config = CrawlerRunConfig(
        # scraping_strategy=LXMLWebScrapingStrategy()  # Faster alternative to default BeautifulSoup
        # )
    
        url = "https://www.sandipuniversity.edu.in/academics/"
     
        result = await crawler.arun(
            url=url,
        )
        with open("data.json" , "w" , encoding="utf-8") as f : 
            json.dump(result.markdown, f )
        print(result.markdown) 
        

if __name__ == "__main__":
    docs = asyncio.run(main())
    print(docs)  
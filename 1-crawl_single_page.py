import asyncio
from crawl4ai import *
import json  
from crawl4ai import AsyncWebCrawler


async def main():
    async with AsyncWebCrawler() as crawler:
        
        # config = CrawlerRunConfig(
        # scraping_strategy=LXMLWebScrapingStrategy()  # Faster alternative to default BeautifulSoup
        # )
    
        url = "https://www.sandipuniversity.edu.in/engineering-technology/school-of-engineering-technology.php"
     
        result = await crawler.arun(
            url=url,
        )
        with open("data.json" , "w" , encoding="utf-8") as f : 
            json.dump(result.links, f )
        print(result.links) 

if __name__ == "__main__":
    docs = asyncio.run(main())
    print(docs)  
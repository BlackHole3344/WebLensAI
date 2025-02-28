import asyncio
from typing import List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from xml.etree import ElementTree
from site_map_extractor import get_all_urls 
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode  
import json 
from typing import List , Dict 
from datetime import datetime 
from urllib.parse import urlparse   


class Crawler : 
    
    def __init__(self , path_ : str , crawl_config : CrawlerRunConfig = None  ) : 
        self.browser_config = BrowserConfig(
            headless=True , 
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
        )
        self.crawl_config = crawl_config 
        self.path = path_  
        self.crawler = AsyncWebCrawler(config=self.browser_config) 
        
    async def crawl_urls(self , urls : List[str]) : 
          await self.crawler.start() 
          crawled_data : Dict[str , Dict] = {}
          try :
              session_id = "session1" 
              crawled = 0
              for url in urls : 
                  result = await self.crawler.arun(
                      url = url , 
                      config  = self.crawl_config ,
                      session_id = session_id   
                  )
                  if result.success:
                            print(f"Successfully crawled: {url}") 
                            crawled += 1              
                  else:
                     print(f"Failed: {url} - Error: {result.error_message}")
                     crawled_data[url] = {
                        "metadata": {
                            "crawl_timestamp": datetime.now().isoformat(),
                            "session_id": session_id,
                            "status": "failed",
                            "error": result.error_message
                        },
                        "page_data": {
                            "url": url,
                            "path": urlparse(url).path,
                            "domain": urlparse(url).netloc
                        }
                    }
                    
          finally:
                # After all URLs are done, close the crawler (and the browser)
                with open(self.path , "w" , encoding="utf-8") as f : 
                    json.dump(
                {
                    "crawl_metadata": {
                        "total_urls": len(urls),
                        "successful_crawls": crawled,
                        "session_id": session_id
                    },
                    "crawled_pages": crawled_data
                },
                f,
                indent=2,
                ensure_ascii=False
            )    
                await self.crawler.close()
                
                
               
               
if __name__ == "__main__" : 
    
    # config = CrawlerRunConfig(
    #     css_selector="main.content", 
    #     word_count_threshold=10,
    #     excluded_tags=["nav", "footer"],
    #     exclude_external_links=True,
    #     exclude_social_media_links=True,
    #     exclude_domains=["ads.com", "spammytrackers.net"],
    #     exclude_external_images=True,
    #     cache_mode=CacheMode.BYPASS
    # )
    web_crawler = Crawler("data.json" ) 
    urls = get_all_urls("https://ai.pydantic.dev/")
    print(urls[:10])
    asyncio.run(web_crawler.crawl_urls(urls))                 
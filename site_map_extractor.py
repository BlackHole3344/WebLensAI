from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests
import xml.etree.ElementTree as ET
import logging
import asyncio 
import aiohttp   
from collections import deque
from crawl4ai import AsyncWebCrawler      
#
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

sitemap_locations = [
    '/sitemap.xml',
    '/sitemap_index.xml',
    '/wp-sitemap.xml'
]

ignore_urls = [
    "login", "signup", "whatsapp", 
    "facebook", "twitter", "linkedin", 
    "instagram", "youtube", "mailto:",
    "tel:", "#" , "javascript:"
]




def is_content_url(url):
    """Enhanced filter for content-rich pages"""
    
    content_indicators = [
        '/article/', '/post/', '/blog/',
        '/guide/', '/tutorial/',
        '/about/', '/page/', '/content/',
        '/courses/', '/faculty/', '/department/',
        '/research/', '/publication/',
        '/news/', '/events/',
        '/academics/', '/admission/',
        '/programs/', '/curriculum/',
        '/syllabus/', '/handbook/',
        '/contact/', '/location/',
        '/careers/', '/jobs/',
        '/faq/', '/help/', '/support/',
        '/policy/', '/terms/', '/privacy/',
        '/press/', '/media/', '/announcements/',
        '/projects/', '/portfolio/',
        '/services/', '/solutions/',
        '/team/', '/staff/', '/people/',
        '/overview/', '/details/', '/description/'
    ]
    
    exclude_paths = [
        # CMS and Admin
        '/tag/', '/category/', '/author/',
        '/search/', '/page/', '/wp-content/',
        '/feed/', '/rss/', '/sitemap/',
        '/cart/', '/checkout/', '/account/',
        '/login/', '/register/', '/signup/',
        '/wp-admin/', '/wp-includes/',
        '/wp-json/', '/wp-cron/', '/wp-login/',
        '/administrator/', '/admin/', '/cpanel/',
        '/dashboard/', '/manage/', '/control/',
        
        # Assets and Resources
        '/assets/', '/images/', '/css/', '/js/',
        '/api/', '/cdn-cgi/', '/comment/',
        '/archive/', '/month/', '/date/',
        '/shop/', '/product/', '/cart/',
        '/fonts/', '/dist/', '/build/',
        '/temp/', '/tmp/', '/cache/',
        '/uploads/', '/download/', '/files/',
        '/thumb/', '/thumbnail/', '/preview/',
        '/banner/', '/slider/', '/carousel/',
        '/static/', '/media/', '/resources/',
        
        # User Interaction
        '/comment/', '/reply/', '/responses/',
        '/like/', '/share/', '/favorite/',
        '/rating/', '/review/', '/feedback/',
        '/submit/', '/form/', '/contact-form/',
        
        # Social and External
        '/social/', '/community/', '/forum/',
        '/chat/', '/message/', '/notification/',
        '/profile/', '/user/', '/member/',
        '/auth/', '/oauth/', '/sso/',
        
        # Temporary and System
        '/temp/', '/cache/', '/backup/',
        '/log/', '/logs/', '/status/',
        '/test/', '/testing/', '/debug/',
        '/demo/', '/sample/', '/example/',
        
        # eCommerce
        '/cart/', '/basket/', '/checkout/',
        '/order/', '/payment/', '/transaction/',
        '/invoice/', '/receipt/', '/shipping/',
        
        # Tracking and Analytics
        '/track/', '/analytics/', '/stats/',
        '/pixel/', '/beacon/', '/tracking/',
        '/counter/', '/hit/', '/click/'
    ]
    
    exclude_extensions = [
        # Documents
        '.pdf', '.doc', '.docx', '.txt', '.rtf',
        '.ppt', '.pptx', '.xls', '.xlsx', '.csv',
        '.odt', '.ods', '.odp', '.pages', '.numbers',
        '.key', '.epub', '.mobi',
        
        # Images
        '.jpg', '.jpeg', '.png', '.gif', '.bmp',
        '.svg', '.webp', '.tiff', '.ico', '.psd',
        '.ai', '.eps',
        
        # Audio/Video
        '.mp3', '.wav', '.ogg', '.m4a', '.wma',
        '.mp4', '.avi', '.mov', '.wmv', '.flv',
        '.webm', '.mkv', '.m4v',
        
        # Archives
        '.zip', '.rar', '.7z', '.tar', '.gz',
        '.bz2', '.iso',
        
        # Web Assets
        '.css', '.js', '.jsx', '.ts', '.tsx',
        '.json', '.xml', '.yaml', '.yml',
        '.woff', '.woff2', '.ttf', '.eot',
        '.map', '.min.js', '.min.css',
        
        # Configuration
        '.conf', '.config', '.ini', '.env',
        '.htaccess', '.htpasswd',
    ]
    
    exclude_params = [
        'page=', 'sort=', 'filter=', 'tag=',
        'category=', 'lang=', 'ref=', 'source=',
        'utm_', 'fbclid=', 'gclid=', 'sid=',
        'session=', 'token=', 'auth=', 'key=',
        'id=', 'date=', 'version=', 'v=',
        'format=', 'view=', 'layout=', 'type=',
        'redirect=', 'return=', 'callback=',
        'query=', 'search=', 'keywords=',
        'limit=', 'offset=', 'start=', 'end=',
        'from=', 'to=', 'dir=', 'order=',
        'print=', 'download=', 'preview='
    ]

    url_lower = url.lower()
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()

    # Check file extensions (more thorough check)
    if any(url_lower.endswith(ext) for ext in exclude_extensions):
        return False
    
    # Check if the URL contains any excluded parameters
    if any(param in url_lower for param in exclude_params):
        return False
        
    # Check if URL contains excluded paths
    if any(path in url_lower for path in exclude_paths):
        return False
        
    # Reject numeric-only paths
    if path.strip('/').isdigit():
        return False
        
    # Reject paths that are too deep
    if len(path.split('/')) > 4:  # Reduced from 5 to 4 for stricter filtering
        return False
        
    # Check for content indicators
    has_content_indicator = any(indicator in url_lower for indicator in content_indicators)
    
    if not has_content_indicator:
        # If no content indicators found, only accept very simple paths
        path_segments = [s for s in path.split('/') if s]
        return len(path_segments) <= 2
        
    return True

def filter_urls_for_knowledge_base(urls):
    """Filter and prioritize URLs for knowledge base creation"""
    filtered_urls = set()
    for url in urls:
        if is_content_url(url):
            filtered_urls.add(url)
    
    return list(filtered_urls)




def get_domain(link):
    try:
        url_ = urlparse(link)
        domain = url_.netloc.replace('www.', '')
        return domain
    except Exception as e:
        logging.error(f"Domain extraction error: {e}")
        return None

def is_same_domain(base_link, href):
    base_domain = get_domain(base_link)
    href_domain = get_domain(href)
    return base_domain and href_domain and base_domain == href_domain

def extract_urls_from_xml(xml_content):
    """Extract URLs from sitemap XML content"""
    try:
        urls = set()
        root = ET.fromstring(xml_content)
        
      
        if 'sitemapindex' in root.tag:
            logging.info("Found sitemap index, processing sub-sitemaps...")
            for sitemap in root.findall('.//{*}loc'):
                try:
                    sub_response = requests.get(sitemap.text)
                    if sub_response.status_code == 200:
                        sub_urls = extract_urls_from_xml(sub_response.content)
                        urls.update(sub_urls)
                except Exception as e:
                    logging.warning(f"Failed to process sub-sitemap {sitemap.text}: {e}")
    
        else:
            for url in root.findall('.//{*}loc'):
                urls.add(url.text)
        
        return urls
    except ET.ParseError as e:
        logging.error(f"XML parsing error: {e}")
        return set()

def try_default_sitemaps(base_url):
    """Try to fetch URLs from default sitemap locations"""
    logging.info("Attempting to fetch sitemap from default locations...")
    
    for location in sitemap_locations:
        sitemap_url = urljoin(base_url, location)
        logging.info(f"Trying sitemap at: {sitemap_url}")
        
        try:
            response = requests.get(sitemap_url)
            if response.status_code == 200:
                logging.info(f"Successfully found sitemap at {sitemap_url}")
                return extract_urls_from_xml(response.content)
        except Exception as e:
            logging.warning(f"Failed to fetch sitemap from {sitemap_url}: {e}")
    
    logging.info("No sitemap found in default locations")
    return set()

def try_robots_txt(base_url):
    """Try to find sitemap URL in robots.txt"""
    logging.info("Attempting to find sitemap in robots.txt...")
    
    try:
        robots_url = urljoin(base_url, '/robots.txt')
        response = requests.get(robots_url)
        
        if response.status_code == 200:
            for line in response.text.split('\n'):
                if 'sitemap:' in line.lower():
                    sitemap_url = line.split(': ')[1].strip()
                    logging.info(f"Found sitemap URL in robots.txt: {sitemap_url}")
                    try:
                        sitemap_response = requests.get(sitemap_url)
                        if sitemap_response.status_code == 200:
                            return extract_urls_from_xml(sitemap_response.content)
                    except Exception as e:
                        logging.warning(f"Failed to fetch sitemap from robots.txt URL: {e}")
    except Exception as e:
        logging.warning(f"Failed to fetch robots.txt: {e}")
    
    logging.info("No valid sitemap found in robots.txt")
    return set()


async def extract_urls_crawl(base_url):
    with AsyncWebCrawler() as crawler: 
        result = await crawler.arun(
            url = base_url 
        )  
        if not result.success() :
            raise RuntimeError
        valid_links = []
        for url in result.links : 
            if url.get("text") and url.get("text").strip():  
                links_info  = {
                    "href" : url.get("href") , 
                    "text" : url.get("text")
                } 
                if url.get("title") : 
                    links_info["title"] = url.get("title")          
                valid_links.append(links_info)                      
        valid_links 
        
def extract_hrefs(base_url , current_depth , max_depth : int = 3 ):
    """Extract URLs from href attributes"""
    logging.info("Falling back to href extraction...")
    urls = set()
    if current_depth > max_depth: 
        return set()
    
    try:
        possibile_divs = [
        'menu', 'nav', 'navigation', 'sidebar',
        'header', 'footer', 'main-menu', 'sub-menu',
        'navbar', 'top-menu', 'side-menu', 'main-nav',
        'sitemap', 'content-menu'
        ]
        response = requests.get(base_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # links = soup.find_all(['a' , 'link'] , href = True) 
            # links.extend(soup.find_all('script' , src = True))  
            target_divs = soup.find_all('div', class_=possibile_divs)  
            target_elements = soup.find_all(['nav', 'header', 'footer', 'aside'])
            
            for element in target_elements + target_divs:  
                href = element.get('href')
                if href:
                    full_url = urljoin(base_url, href)         
                    if (href.startswith(('https://', 'http://')) and
                        not any(url in href.lower() for url in ignore_urls) and
                        base_url in full_url):
                        urls.add(href)
        
        logging.info(f"Found {len(urls)} URLs from href extraction")
        return urls
    except Exception as e:
        logging.error(f"Error during href extraction: {e}")
        return set()

def get_all_urls(base_url):
    """Main function to get all URLs using different methods"""
    logging.info(f"Starting URL extraction for: {base_url}")
    urls = set()
    
    urls = try_default_sitemaps(base_url)
    if urls:
        logging.info(f"Successfully found {len(urls)} URLs from default sitemap")
        return list(urls)
    

    urls = try_robots_txt(base_url)
    if urls:
        logging.info(f"Successfully found {len(urls)} URLs from robots.txt sitemap")
        return list(urls)
    
  
    urls = extract_hrefs(base_url)
    logging.info(f"Final URL count: {len(urls)}")
    
    urls = filter_urls_for_knowledge_base(urls=urls)
    return list(urls)


if __name__ == "__main__":
    test_url = "https://example.com"  # Replace with your target website
    urls = get_all_urls("https://ai.pydantic.dev/")
    print(f"Found {len(urls)} URLs to crawl") 
    print(urls[:100])
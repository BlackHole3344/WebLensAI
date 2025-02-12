from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests
import xml.etree.ElementTree as ET
import logging

# Configure logging
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
    "tel:", "#"
]




def is_content_url(url):
    """Filter for likely content-rich pages"""
    
    # Paths that likely contain actual content
    content_indicators = [
        '/article/', '/post/', '/blog/', 
        '/guide/', '/tutorial/',
        '/about/', '/page/', '/content/',
        '/courses/', '/faculty/', '/department/',
        '/research/', '/publication/',
        '/news/', '/events/'
    ]
    
    # Paths to exclude (typically non-content pages)
    exclude_paths = [
        '/tag/', '/category/', '/author/',
        '/search/', '/page/', '/wp-content/',
        '/feed/', '/rss/', '/sitemap/',
        '/cart/', '/checkout/', '/account/',
        '/login/', '/register/', '/signup/',
        '/wp-admin/', '/wp-includes/',
        '/assets/', '/images/', '/css/', '/js/',
        '/api/', '/cdn-cgi/', '/comment/',
        '/archive/', '/month/', '/date/',
        '/shop/', '/product/', '/cart/'
    ]
    
    # File extensions to exclude
    exclude_extensions = [
        '.jpg', '.jpeg', '.png', '.gif', '.pdf',
        '.doc', '.docx', '.ppt', '.pptx',
        '.zip', '.rar', '.css', '.js', '.xml',
        '.ico', '.svg', '.woff', '.ttf'
    ]
    
    # Parameters to exclude
    exclude_params = [
        'page=', 'sort=', 'filter=', 'tag=',
        'category=', 'lang=', 'ref=', 'source='
    ]

    url_lower = url.lower()
    
    # Check for excluded file extensions
    if any(url_lower.endswith(ext) for ext in exclude_extensions):
        return False
        
    # Check for excluded parameters
    if any(param in url_lower for param in exclude_params):
        return False
        
    # Check for excluded paths
    if any(path in url_lower for path in exclude_paths):
        return False
        
    # Additional filters
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()
    
    # Exclude if path is just a number (likely pagination)
    if path.strip('/').isdigit():
        return False
    
    # Exclude paths with too many segments (likely deep navigation)
    if len(path.split('/')) > 5:
        return False
    
    # Check for content indicators
    has_content_indicator = any(indicator in url_lower for indicator in content_indicators)
    
    # If no content indicators found, check if it's a potential main section
    if not has_content_indicator:
        # Count path segments (excluding empty ones)
        path_segments = [s for s in path.split('/') if s]
        # Accept URLs with 0-2 path segments (like main sections)
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
        
        # Handle sitemap index
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
        # Handle regular sitemap
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

def extract_hrefs(base_url):
    """Extract URLs from href attributes"""
    logging.info("Falling back to href extraction...")
    urls = set()
    
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for link in soup.find_all('a'):
                href = link.get('href')
                if href:
                    # Convert relative URLs to absolute
                    if not href.startswith(('http://', 'https://')):
                        href = urljoin(base_url, href)
                    # Filter unwanted URLs
                    if (href.startswith(('https://', 'http://')) and
                        not any(url in href.lower() for url in ignore_urls) and
                        is_same_domain(base_url, href)):
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
    
    # Step 1: Try default sitemap locations
    urls = try_default_sitemaps(base_url)
    if urls:
        logging.info(f"Successfully found {len(urls)} URLs from default sitemap")
        return list(urls)
    
    # Step 2: Try robots.txt
    urls = try_robots_txt(base_url)
    if urls:
        logging.info(f"Successfully found {len(urls)} URLs from robots.txt sitemap")
        return list(urls)
    
    # Step 3: Fall back to href extraction
    urls = extract_hrefs(base_url)
    logging.info(f"Final URL count: {len(urls)}")
    
    urls = filter_urls_for_knowledge_base(urls=urls)
    return list(urls)

# Usage example
if __name__ == "__main__":
    test_url = "https://example.com"  # Replace with your target website
    urls = get_all_urls("https://www.redhenlab.org/")
    
    print(f"\nFound {len(urls)} unique URLs:")
    for url in sorted(urls):
        print(url)
from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re

app = Flask(__name__)


def get_word_count(url):
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Initialize an empty string to store all text
        all_text = ""

        # Extract text from specified tags
        for tag in ['span','p'] + [f'h{i}' for i in range(1, 7)]:
            elements = soup.find_all(tag)
            for element in elements:
                # Check if the element is not part of a script or style
                if not element.find_parents(['script', 'style']):
                    all_text += ' ' + element.get_text()

        # Replace non-word characters (except apostrophes in words) with spaces
        all_text = re.sub(r"[^\w\s']|(?<!\w)'|'(?!\w)", ' ', all_text)

        # Split into words and count
        words = re.findall(r'\b\w+\'?\w*\b', all_text)
        word_count = len(words)

        return word_count

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the webpage: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return 0



def extract_page_details(url):
    """
    Fetch HTML content from the given URL and extract specific details.
    
    :param url: The URL to fetch HTML content from
    :return: A dictionary containing the title, description, URL, canonical link, word count, and meta robots tag
    :raises: Exception if there's an error in fetching or parsing the URL
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error fetching URL: {e}")
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    title = soup.title.string if soup.title else "No title found"
    description = soup.find('meta', attrs={'name': 'description'})
    description = description['content'] if description else "No description found"
    canonical = soup.find('link', rel='canonical')
    canonical = canonical['href'] if canonical else "No canonical link found"
    meta_robots = soup.find('meta', attrs={'name': 'robots'})
    meta_robots = meta_robots['content'] if meta_robots else "No meta robots tag found"
    
    word_count = get_word_count(url)
    
    return {
        "title": title,
        "description": description,
        "url": url,
        "canonical": canonical,
        "word_count": word_count,
        "meta_robots": meta_robots
    }



def find_open_graph_tags(url):
    """
    Fetch HTML content from the given URL and find all Open Graph meta tags.
    
    :param url: The URL to fetch HTML content from
    :return: A dictionary of Open Graph meta tags
    :raises: Exception if there's an error in fetching or parsing the URL
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error fetching URL: {e}")
    
    soup = BeautifulSoup(response.content, 'html.parser')
    og_tags = {meta.attrs['property'][3:]: meta.attrs['content']
               for meta in soup.find_all('meta')
               if 'property' in meta.attrs and meta.attrs['property'].startswith('og:')}
    return og_tags


def check_website_status(url):
    """
    Check the status of a website by sending an HTTP request.
    
    :param url: The URL of the website to check
    :return: A dictionary containing the status code and reason
    :raises: Exception if there's an error in fetching the URL
    """
    try:
        response = requests.head(url)
        return {"status_code": response.status_code, "reason": response.reason}
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error checking website status: {e}")

def extract_headers_from_url(url):
    """
    Fetch HTML content from the given URL and extract all headers in order of appearance.
    
    :param url: The URL to fetch HTML content from
    :return: A list of headers in the format <tag>Text</tag>
    :raises: Exception if there's an error in fetching or parsing the URL
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error fetching URL: {e}")
    
    soup = BeautifulSoup(response.content, 'html.parser')
    headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    headers_formatted = [f"<{header.name}>{header.get_text().strip()}</{header.name}>" for header in headers]
    return headers_formatted



def get_links_with_keywords(url):
    # Send a GET request to the URL
    response = requests.get(url)
    
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract all the anchor tags
    anchor_tags = soup.find_all('a', href=True)
    
    # Initialize counters and lists
    total_links = 0
    internal_links = 0
    external_links = 0
    internal_links_with_domain = 0
    hidden_links = 0
    link_details = []
    
    # Parse the base URL to get the domain
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    
    # Regular expression to detect common hidden styles
    hidden_style_re = re.compile(r'display\s*:\s*none|visibility\s*:\s*hidden', re.IGNORECASE)
    
    # Loop through all anchor tags
    for tag in anchor_tags:
        href = tag['href']
        keyword = tag.get_text(strip=True)
        total_links += 1
        
        # Check if the link is hidden
        hidden = False
        if tag.has_attr('style') and hidden_style_re.search(tag['style']):
            hidden = True
        elif tag.find_parent(style=hidden_style_re):
            hidden = True

        if hidden:
            hidden_links += 1
        
        # Resolve relative URLs
        if not urlparse(href).netloc:
            href = urljoin(url, href)
        
        # Check if the link is internal or external
        if domain in urlparse(href).netloc:
            internal_links += 1
            if domain in href:
                internal_links_with_domain += 1
            link_type = 'internal'
        else:
            external_links += 1
            link_type = 'external'
        
        # Add link details to the list
        link_details.append({
            'href': href,
            'keyword': keyword,
            'type': link_type,
            'hidden': hidden
        })
    
    return {
        'total_links': total_links,
        'internal_links': internal_links,
        'external_links': external_links,
        'internal_links_with_domain': internal_links_with_domain,
        'hidden_links': hidden_links,
        'links': link_details
    }

@app.route('/links', methods=['GET'])
def get_links():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is required'}), 400
    
    try:
        # word_count =get_word_count(url)
        overview = extract_page_details(url)
        results = get_links_with_keywords(url)
        headers = extract_headers_from_url(url)
        status_code = check_website_status(url)
        og_tag = find_open_graph_tags(url)
        return jsonify(overview,results, headers,status_code,og_tag)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True,port=5009)

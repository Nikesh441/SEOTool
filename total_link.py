from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re

app = Flask(__name__)

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

@app.route('/api/links', methods=['GET'])
def get_links():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is required'}), 400
    
    try:
        results = get_links_with_keywords(url)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

from urllib.parse import urlsplit

from bs4 import BeautifulSoup


def parse_page_content(html):    
    soup = BeautifulSoup(html, 'html.parser')
    soup_h1 = soup.find('h1')

    if soup_h1:
        h1 = soup_h1.text.strip()
        if len(h1) > 200:
            h1 = h1[:200] + '...'
    else:
        h1 = None

    soup_title = soup.find('title')
    if soup_title:
        title = soup_title.text.strip()
        if len(title) > 200:
            title = title[:200] + '...'
    else:
        title = None

    soup_desc = soup.find('meta', attrs={'name': 'description'})
    if soup_desc:
        description = soup_desc.get('content', '')
        if description:
            description = description.strip()
            if len(description) > 200:
                description = description[:200] + '...'
        else:
            description = None
    else:
        description = None

    return h1, title, description


def normalize_url(url_data):
    if not url_data:
        return ''
    
    if not url_data.startswith(('http://', 'https://')):
        url_data = 'http://' + url_data
    
    parts = urlsplit(url_data)
    return f"{parts.scheme}://{parts.netloc}"
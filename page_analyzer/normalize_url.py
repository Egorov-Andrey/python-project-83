from urllib.parse import urlsplit


def normalize_url(url_data):
    if not url_data:
        return ''
    
    if not url_data.startswith(('http://', 'https://')):
        url_data = 'http://' + url_data
    
    parts = urlsplit(url_data)
    return f"{parts.scheme}://{parts.netloc}"
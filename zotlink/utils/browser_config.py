#!/usr/bin/env python3
"""
Centralized browser configuration for anti-detection and domain management.
"""

from typing import Dict, Optional
from urllib.parse import urlparse


class BrowserConfig:
    """Centralized browser configuration for anti-detection."""

    ANTI_DETECTION_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''}
        ]
    });
    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
    Object.defineProperty(navigator, 'platform', {get: () => 'MacIntel'});
    Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.'});
    delete Object.getPrototypeOf(navigator).webdriver;
    """

    SIMPLE_ANTI_DETECTION = """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
    delete Object.getPrototypeOf(navigator).webdriver;
    """

    BROWSER_ARGS = [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-setuid-sandbox',
        '--disable-blink-features=AutomationControlled',
        '--disable-extensions',
        '--disable-gpu',
        '--window-size=1920,1080',
        '--start-maximized',
    ]

    USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


class AntiCrawlerDomains:
    """Centralized list of domains requiring browser mode."""

    BROWSER_MODE_DOMAINS = {
        'biorxiv.org': {'source': 'bioRxiv', 'itemType': 'preprint'},
        'medrxiv.org': {'source': 'medRxiv', 'itemType': 'preprint'},
        'chemrxiv.org': {'source': 'ChemRxiv', 'itemType': 'preprint'},
        'psyarxiv.com': {'source': 'PsyArXiv', 'itemType': 'preprint'},
        'osf.io': {'source': 'OSF', 'itemType': 'preprint'},
        'socarxiv.org': {'source': 'SocArXiv', 'itemType': 'preprint'},
        'researchsquare.com': {'source': 'Research Square', 'itemType': 'preprint'},
        'authorea.com': {'source': 'Authorea', 'itemType': 'preprint'},
    }

    ANTI_CRAWLER_DOMAINS = {
        'biorxiv.org', 'medrxiv.org', 'chemrxiv.org',
        'psyarxiv.com', 'socarxiv.org', 'osf.io',
        'researchsquare.com', 'authorea.com'
    }

    @classmethod
    def requires_browser(cls, url: str) -> bool:
        """Check if URL requires browser mode."""
        domain = urlparse(url).netloc.lower()
        return any(d in domain for d in cls.BROWSER_MODE_DOMAINS)

    @classmethod
    def is_anti_crawler(cls, url: str) -> bool:
        """Check if URL is from an anti-crawler domain."""
        domain = urlparse(url).netloc.lower()
        return any(d in domain for d in cls.ANTI_CRAWLER_DOMAINS)

    @classmethod
    def get_domain_info(cls, url: str) -> Optional[Dict]:
        """Get domain info for URL."""
        domain = urlparse(url).netloc.lower()
        for domain_pattern, info in cls.BROWSER_MODE_DOMAINS.items():
            if domain_pattern in domain:
                return info
        return None


class PDFUrlBuilder:
    """Centralized PDF URL construction for various preprint servers."""

    PDF_PATTERNS = {
        'biorxiv.org': {
            'pattern': r'/content/(?:10\.1101/)?([0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+v?\d*)',
            'template': 'https://www.biorxiv.org/content/10.1101/{doc_id}.full.pdf'
        },
        'medrxiv.org': {
            'pattern': r'/content/(?:10\.1101/)?([0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+v?\d*)',
            'template': 'https://www.medrxiv.org/content/10.1101/{doc_id}.full.pdf'
        },
        'chemrxiv.org': {
            'pattern': r'article-details/([a-f0-9]{24,})',
            'template': 'https://chemrxiv.org/engage/api-gateway/chemrxiv/assets/orp/resource/item/{article_id}/original/manuscript.pdf'
        },
        'osf.io': {
            'pattern': r'osf\.io/preprints/[^/]+/([a-z0-9]+)',
            'template': 'https://osf.io/{preprint_id}/download'
        },
    }

    @classmethod
    def construct_pdf_url(cls, url: str) -> Optional[str]:
        """Construct PDF URL for a given preprint URL."""
        url_lower = url.lower()
        
        for domain, config in cls.PDF_PATTERNS.items():
            if domain in url_lower:
                match = re.search(config['pattern'], url)
                if match:
                    doc_id = match.group(1)
                    return config['template'].format(doc_id=doc_id, article_id=doc_id, preprint_id=doc_id)
        
        return None

    @classmethod
    def construct_biorxiv_pdf(cls, url: str) -> Optional[str]:
        """Construct bioRxiv/medRxiv PDF URL."""
        doc_id_match = re.search(r'/content/(?:10\.1101/)?([0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+v?\d*)', url)
        if doc_id_match:
            full_doc_id = doc_id_match.group(1)
            if 'biorxiv.org' in url.lower():
                return f"https://www.biorxiv.org/content/10.1101/{full_doc_id}.full.pdf"
            elif 'medrxiv.org' in url.lower():
                return f"https://www.medrxiv.org/content/10.1101/{full_doc_id}.full.pdf"
        return None

    @classmethod
    def construct_chemrxiv_pdf(cls, url: str) -> Optional[str]:
        """Construct ChemRxiv PDF URL."""
        article_match = re.search(r'article-details/([a-f0-9]{24,})', url)
        if article_match:
            article_id = article_match.group(1)
            return f"https://chemrxiv.org/engage/api-gateway/chemrxiv/assets/orp/resource/item/{article_id}/original/manuscript.pdf"
        return None

    @classmethod
    def construct_osf_pdf(cls, url: str) -> Optional[str]:
        """Construct OSF PDF URL."""
        match = re.search(r'osf\.io/preprints/[^/]+/([a-z0-9]+)', url)
        if match:
            preprint_id = match.group(1)
            return f"https://osf.io/{preprint_id}/download"
        return None

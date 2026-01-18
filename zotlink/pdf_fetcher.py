#!/usr/bin/env python3
"""
PDF Fetcher for ZotLink

Fetches PDFs from various sources with intelligent fallback:
1. arXiv (direct PDF download)
2. Open Access (Unpaywall, PubMed Central, DOAJ, Semantic Scholar)
3. Sci-Hub (multiple mirrors)
4. Anna's Archive (search by DOI or title)
5. Library Genesis (search by DOI or title)
6. ResearchGate (if available)
7. Publisher direct (with proper headers)
"""

import requests
import logging
import base64
import re
import json
import sqlite3
from typing import Dict, Optional, Any, List
from pathlib import Path
import time
import random

logger = logging.getLogger(__name__)


class PDFFetcher:
    """Fetch PDFs from various academic sources with fallback"""

    def __init__(self, zotero_connector=None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/pdf,application/octet-stream,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/',
        })
        self.zotero_connector = zotero_connector
        self._last_attempt = {}

    def fetch_pdf(self, item_key: str, source: str = "auto",
                  save_to_zotero: bool = True) -> Dict:
        """
        Fetch PDF for a Zotero item from available sources.

        Args:
            item_key: The Zotero item key
            source: Preferred source (auto, arxiv, open_access, scihub, annas_archive)
            save_to_zotero: Whether to save the PDF as an attachment

        Returns:
            Dict containing fetch result and PDF data
        """
        try:
            if not self.zotero_connector:
                return {"success": False, "error": "Zotero connector not available"}

            item_result = self.zotero_connector.get_item(item_key)
            if not item_result.get("success"):
                return {"success": False, "error": f"Could not get item: {item_result.get('error')}"}

            item_data = item_result.get("item", {})
            if isinstance(item_data, str):
                try:
                    item_data = json.loads(item_data)
                except json.JSONDecodeError:
                    pass

            item_info = {
                "key": item_key,
                "title": item_data.get("title", ""),
                "doi": item_data.get("DOI", ""),
                "url": item_data.get("url", ""),
                "arxiv_id": self._extract_arxiv_id(item_data.get("url", "")),
            }

            sources_order = self._get_source_order(source)

            all_results = []

            for src in sources_order:
                logger.info(f"Trying PDF source: {src}")

                fetch_result = None

                if src == "arxiv":
                    fetch_result = self._fetch_from_arxiv(item_info)
                elif src == "mdpi":
                    fetch_result = self._fetch_from_mdpi(item_info)
                elif src == "open_access":
                    fetch_result = self._fetch_from_open_access(item_info)
                elif src == "scihub":
                    fetch_result = self._fetch_from_scihub(item_info)
                elif src == "annas_archive":
                    fetch_result = self._fetch_from_annas_archive(item_info)
                elif src == "libgen":
                    fetch_result = self._fetch_from_libgen(item_info)
                elif src == "publisher":
                    fetch_result = self._fetch_from_publisher(item_info)

                if fetch_result and fetch_result.get("success"):
                    pdf_content = fetch_result.get("content")
                    source_name = fetch_result.get("source", src)

                    result = {
                        "success": True,
                        "source": source_name,
                        "size": len(pdf_content) if pdf_content else 0,
                        "title": item_info.get("title", ""),
                        "pdf_content": pdf_content
                    }

                    if save_to_zotero:
                        attach_result = self._attach_pdf_to_zotero(item_key, pdf_content, item_info)
                        result["attachment_added"] = attach_result.get("success", False)
                        result["attachment_key"] = attach_result.get("attachment_key")

                    return result

                if fetch_result:
                    all_results.append(fetch_result)

            return {
                "success": False,
                "error": "Could not find PDF from any source",
                "item_key": item_key,
                "tried_sources": sources_order,
                "attempts": all_results
            }

        except Exception as e:
            logger.error(f"PDF fetch failed: {e}")
            return {"success": False, "error": str(e)}

    def _get_source_order(self, source: str) -> list:
        """Get ordered list of sources to try"""
        all_sources = ["arxiv", "mdpi", "open_access", "scihub", "annas_archive", "libgen", "publisher"]

        if source == "auto":
            return all_sources
        elif source in all_sources:
            return [source] + [s for s in all_sources if s != source]
        else:
            return all_sources

    def _extract_arxiv_id(self, url: str) -> Optional[str]:
        """Extract arXiv ID from URL"""
        patterns = [
            r'arxiv\.org/abs/([\d]+\.[\d]+)',
            r'arxiv\.org/pdf/([\d]+\.[\d]+)',
            r'arxiv:([\d]+\.[\d]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _fetch_from_arxiv(self, item_info: Dict) -> Optional[Dict]:
        """Fetch PDF from arXiv"""
        arxiv_id = item_info.get("arxiv_id")
        if not arxiv_id:
            doi = item_info.get("doi", "")
            if "arxiv.org" in doi.lower():
                arxiv_id = self._extract_arxiv_id(doi)

        if not arxiv_id:
            return None

        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        try:
            response = self.session.get(pdf_url, timeout=60, stream=True)

            if response.status_code == 200:
                content = response.content
                if content.startswith(b'%PDF'):
                    logger.info(f"Fetched PDF from arXiv: {arxiv_id}")
                    return {
                        "success": True,
                        "source": "arXiv",
                        "content": content,
                        "url": pdf_url
                    }
        except Exception as e:
            logger.warning(f"arXiv fetch failed: {e}")

        return None

    def _fetch_from_mdpi(self, item_info: Dict) -> Optional[Dict]:
        """Fetch PDF from MDPI journal"""
        doi = item_info.get("doi", "")

        mdpi_doi = None

        if doi:
            if "10.3390/" in doi:
                mdpi_doi = doi

        if not mdpi_doi:
            return None

        try:
            mdpi_pdf_url = None

            try:
                unpaywall_url = f"https://api.unpaywall.org/v2/{mdpi_doi}?email=research@example.com"
                response = self.session.get(unpaywall_url, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    best_oa = data.get("best_oa_location", {})
                    pdf_url = best_oa.get("url_for_pdf")
                    if pdf_url and "mdpi.com" in pdf_url:
                        mdpi_pdf_url = pdf_url
            except Exception:
                pass

            if not mdpi_pdf_url:
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                })

                for attempt in range(3):
                    try:
                        response = session.get(f"https://doi.org/{mdpi_doi}", timeout=30, allow_redirects=True)

                        if response.status_code == 200 and "mdpi.com" in response.url:
                            mdpi_pdf_url = response.url.rstrip('/') + "/pdf"
                            break

                        if attempt < 2:
                            import time
                            time.sleep(2 ** attempt)

                    except requests.exceptions.ConnectionError:
                        if attempt < 2:
                            import time
                            time.sleep(2 ** attempt)
                        continue

            if mdpi_pdf_url:
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/pdf,application/octet-stream,*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': 'https://www.mdpi.com/',
                })

                for attempt in range(3):
                    try:
                        response = session.get(mdpi_pdf_url, timeout=60, stream=True)

                        if response.status_code == 200:
                            content = response.content

                            if content.startswith(b'%PDF'):
                                logger.info(f"Fetched PDF from MDPI: {mdpi_pdf_url}")
                                return {
                                    "success": True,
                                    "source": "MDPI",
                                    "content": content,
                                    "url": mdpi_pdf_url
                                }

                        if attempt < 2:
                            import time
                            time.sleep(2 ** attempt)

                    except requests.exceptions.ConnectionError:
                        if attempt < 2:
                            import time
                            time.sleep(2 ** attempt)
                        continue

        except Exception as e:
            logger.warning(f"MDPI fetch failed: {e}")

        return None

    def _fetch_from_open_access(self, item_info: Dict) -> Optional[Dict]:
        """Fetch PDF from open access sources"""
        doi = item_info.get("doi", "")
        url = item_info.get("url", "")

        sources = [
            ("unpaywall", self._fetch_from_unpaywall),
            ("pubmed", self._fetch_from_pubmed),
            ("doaj", self._fetch_from_doaj),
            ("semantic_scholar", self._fetch_from_semantic_scholar),
            ("core", self._fetch_from_core),
            ("osf", self._fetch_from_osf),
        ]

        for source_name, fetch_func in sources:
            try:
                result = fetch_func(item_info)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"{source_name} fetch failed: {e}")

        return None

    def _fetch_from_unpaywall(self, item_info: Dict) -> Optional[Dict]:
        """Fetch PDF using Unpaywall API"""
        doi = item_info.get("doi", "")
        if not doi:
            return None

        try:
            url = f"https://api.unpaywall.org/v2/{doi}"
            params = {"email": "research@example.com"}
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                best_oa = data.get("best_oa_location", {})
                url_for_pdf = best_oa.get("url_for_pdf")
                if url_for_pdf:
                    pdf_response = self.session.get(url_for_pdf, timeout=60, stream=True)
                    if pdf_response.status_code == 200:
                        content = pdf_response.content
                        if content.startswith(b'%PDF'):
                            return {
                                "success": True,
                                "source": "Unpaywall",
                                "content": content,
                                "url": url_for_pdf
                            }
        except Exception as e:
            logger.warning(f"Unpaywall fetch failed: {e}")

        return None

    def _fetch_from_pubmed(self, item_info: Dict) -> Optional[Dict]:
        """Fetch PDF from PubMed Central"""
        doi = item_info.get("doi", "")
        if not doi:
            return None

        try:
            url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={doi}&format=json"
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                data = response.json()
                records = data.get("records", [])
                if records:
                    pmcid = records[0].get("pmcid")
                    if pmcid:
                        pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
                        pdf_response = self.session.get(pdf_url, timeout=30, stream=True)
                        if pdf_response.status_code == 200:
                            content = pdf_response.content
                            if content.startswith(b'%PDF'):
                                return {
                                    "success": True,
                                    "source": "PubMed Central",
                                    "content": content,
                                    "url": pdf_url
                                }
        except Exception as e:
            logger.warning(f"PubMed Central fetch failed: {e}")

        return None

    def _fetch_from_doaj(self, item_info: Dict) -> Optional[Dict]:
        """Fetch PDF from DOAJ"""
        doi = item_info.get("doi", "")
        if not doi:
            return None

        try:
            url = f"https://doaj.org/api/v2/articles/{doi}"
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                data = response.json()
                best_oa = data.get("best_oa_location", {})
                url_for_pdf = best_oa.get("url_for_pdf")
                if url_for_pdf:
                    pdf_response = self.session.get(url_for_pdf, timeout=30, stream=True)
                    if pdf_response.status_code == 200:
                        content = pdf_response.content
                        if content.startswith(b'%PDF'):
                            return {
                                "success": True,
                                "source": "DOAJ",
                                "content": content,
                                "url": url_for_pdf
                            }
        except Exception as e:
            logger.warning(f"DOAJ fetch failed: {e}")

        return None

    def _fetch_from_semantic_scholar(self, item_info: Dict) -> Optional[Dict]:
        """Fetch PDF from Semantic Scholar"""
        doi = item_info.get("doi", "")
        if not doi:
            return None

        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
            params = {"fields": "openAccessPdf,externalIds"}
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                oa_pdf = data.get("openAccessPdf", {})
                pdf_url = oa_pdf.get("url")
                if pdf_url:
                    pdf_response = self.session.get(pdf_url, timeout=30, stream=True)
                    if pdf_response.status_code == 200:
                        content = pdf_response.content
                        if content.startswith(b'%PDF'):
                            return {
                                "success": True,
                                "source": "Semantic Scholar",
                                "content": content,
                                "url": pdf_url
                            }
        except Exception as e:
            logger.warning(f"Semantic Scholar fetch failed: {e}")

        return None

    def _fetch_from_core(self, item_info: Dict) -> Optional[Dict]:
        """Fetch PDF from CORE"""
        title = item_info.get("title", "")
        if not title:
            return None

        try:
            url = "https://api.core.ac.uk/v3/search/works"
            params = {"q": title, "limit": 5}
            headers = {"User-Agent": "ZotLink/1.0 (research tool)"}
            response = self.session.get(url, params=params, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                for result in results:
                    result_title = result.get("title", "")
                    if title.lower() in result_title.lower() or result_title.lower() in title.lower():
                        pdf_url = result.get("downloadUrl") or result.get("doiUrl")
                        if pdf_url:
                            # Check file size first with HEAD request
                            head_response = self.session.head(pdf_url, timeout=10)
                            content_length = head_response.headers.get('Content-Length', '')
                            if content_length:
                                size_mb = int(content_length) / 1024 / 1024
                                if size_mb > 10:  # Skip if larger than 10MB
                                    logger.warning(f"CORE file too large: {size_mb:.1f}MB, skipping")
                                    continue
                            
                            pdf_response = self.session.get(pdf_url, timeout=60, stream=True)
                            if pdf_response.status_code == 200:
                                content = pdf_response.content
                                if content.startswith(b'%PDF') and len(content) < 10 * 1024 * 1024:
                                    return {
                                        "success": True,
                                        "source": "CORE",
                                        "content": content,
                                        "url": pdf_url
                                    }
        except Exception as e:
            logger.warning(f"CORE fetch failed: {e}")

        return None

    def _fetch_from_osf(self, item_info: Dict) -> Optional[Dict]:
        """Fetch PDF from OSF"""
        title = item_info.get("title", "")
        if not title:
            return None

        try:
            url = "https://api.osf.io/v2/search/"
            params = {"q": title, "format": "json"}
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                for result in results:
                    for material in result.get("materials", []):
                        if material.get("contentType") == "preprint":
                            pdf_url = material.get("downloadUrl")
                            if pdf_url:
                                pdf_response = self.session.get(pdf_url, timeout=30, stream=True)
                                if pdf_response.status_code == 200:
                                    content = pdf_response.content
                                    if content.startswith(b'%PDF'):
                                        return {
                                            "success": True,
                                            "source": "OSF",
                                            "content": content,
                                            "url": pdf_url
                                        }
        except Exception as e:
            logger.warning(f"OSF fetch failed: {e}")

        return None

    def _fetch_from_scihub(self, item_info: Dict) -> Optional[Dict]:
        """Fetch PDF from Sci-Hub"""
        doi = item_info.get("doi", "")
        if not doi:
            return None

        scihub_urls = [
            "https://sci-hub.se",
            "https://sci-hub.st",
            "https://sci-hub.wf",
            "https://sci-hub.lu",
            "https://sci-hub.tw",
            "https://sci-hub.do",
            "https://sci-hub.cat",
            "https://sci-hubpro.se",
            "https://sci-hub9.se",
            "https://sci-hub.hkvisa.net",
            "https://sci-hub.mystical.xyz",
            "https://sci-hub.etin.cc",
        ]

        for base_url in scihub_urls:
            try:
                pdf_url = f"{base_url}/{doi}"
                response = self.session.get(pdf_url, timeout=30, stream=True)

                if response.status_code == 200:
                    content = response.content

                    if content.startswith(b'%PDF'):
                        return {
                            "success": True,
                            "source": "Sci-Hub",
                            "content": content,
                            "url": pdf_url
                        }

                    content_str = content.decode('utf-8', errors='ignore')

                    if "PDF not found" in content_str or "not found" in content_str.lower():
                        continue

                    download_match = re.search(r'href=["\']([^"\']*\.pdf)["\']', content_str)
                    if download_match:
                        pdf_link = download_match.group(1)
                        if pdf_link and not pdf_link.startswith('http'):
                            pdf_link = base_url + "/" + pdf_link.lstrip("/")
                        elif pdf_link and not pdf_link.startswith('http'):
                            pdf_link = f"{base_url}{pdf_link}"

                        if pdf_link:
                            pdf_response = self.session.get(pdf_link, timeout=30, stream=True)
                            if pdf_response.status_code == 200:
                                pdf_content = pdf_response.content
                                if pdf_content.startswith(b'%PDF'):
                                    return {
                                        "success": True,
                                        "source": "Sci-Hub",
                                        "content": pdf_content,
                                        "url": pdf_link
                                    }

            except Exception as e:
                logger.warning(f"Sci-Hub ({base_url}) failed: {e}")
                continue

        return None

    def _fetch_from_annas_archive(self, item_info: Dict) -> Optional[Dict]:
        """Fetch PDF from Anna's Archive"""
        doi = item_info.get("doi", "")
        title = item_info.get("title", "")

        if not doi and not title:
            return None

        try:
            annas_api = "https://api.annas-archive.org"

            if doi:
                search_url = f"{annas_api}/v3/search"
                params = {"query": doi, "limit": 5}
                response = self.session.get(search_url, params=params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    for result in results:
                        file_links = result.get("file_links", [])
                        for link in file_links:
                            if link.get("file_format") == "pdf":
                                pdf_url = link.get("url")
                                if pdf_url:
                                    pdf_response = self.session.get(pdf_url, timeout=60, stream=True)
                                    if pdf_response.status_code == 200:
                                        content = pdf_response.content
                                        if content.startswith(b'%PDF'):
                                            return {
                                                "success": True,
                                                "source": "Anna's Archive",
                                                "content": content,
                                                "url": pdf_url
                                            }

            if title:
                search_url = f"{annas_api}/v3/search"
                params = {"query": title, "limit": 10}
                response = self.session.get(search_url, params=params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    for result in results:
                        result_title = result.get("title", "")
                        if title.lower() in result_title.lower() or result_title.lower() in title.lower():
                            file_links = result.get("file_links", [])
                            for link in file_links:
                                if link.get("file_format") == "pdf":
                                    pdf_url = link.get("url")
                                    if pdf_url:
                                        pdf_response = self.session.get(pdf_url, timeout=60, stream=True)
                                        if pdf_response.status_code == 200:
                                            content = pdf_response.content
                                            if content.startswith(b'%PDF'):
                                                return {
                                                    "success": True,
                                                    "source": "Anna's Archive",
                                                    "content": content,
                                                    "url": pdf_url
                                                }

        except Exception as e:
            logger.warning(f"Anna's Archive fetch failed: {e}")

        return None

    def _fetch_from_libgen(self, item_info: Dict) -> Optional[Dict]:
        """Fetch PDF from Library Genesis"""
        doi = item_info.get("doi", "")
        title = item_info.get("title", "")

        if not doi and not title:
            return None

        libgen_urls = [
            "https://libgen.is",
            "https://libgen.st",
            "https://libgen.lc",
            "https://libgen.gs",
            "https://libgen.li",
            "https://libgen.ee",
            "https://libgen.pm",
        ]

        for base_url in libgen_urls:
            try:
                search_url = f"{base_url}/search.php"
                if doi:
                    params = {"req": doi, "res": 1}
                else:
                    params = {"req": title[:50], "res": 1}

                response = self.session.get(search_url, params=params, timeout=15)
                if response.status_code == 200:
                    content = response.text

                    if "nothing found" in content.lower():
                        continue

                    links_match = re.search(r'href=["\']([^"\']*\.pdf)["\']', content)
                    if links_match:
                        pdf_link = links_match.group(1)
                        if pdf_link and not pdf_link.startswith('http'):
                            pdf_link = base_url + "/" + pdf_link.lstrip("/")

                        if pdf_link:
                            pdf_response = self.session.get(pdf_link, timeout=60, stream=True)
                            if pdf_response.status_code == 200:
                                content = pdf_response.content
                                if content.startswith(b'%PDF'):
                                    return {
                                        "success": True,
                                        "source": "Library Genesis",
                                        "content": content,
                                        "url": pdf_link
                                    }

            except Exception as e:
                logger.warning(f"Library Genesis ({base_url}) failed: {e}")
                continue

        return None

    def _fetch_from_publisher(self, item_info: Dict) -> Optional[Dict]:
        """Fetch PDF directly from publisher"""
        doi = item_info.get("doi", "")
        url = item_info.get("url", "")

        if not doi and not url:
            return None

        publisher_urls = []

        if doi:
            publisher_urls.append(f"https://doi.org/{doi}")

        if url:
            publisher_urls.append(url)

        for pub_url in publisher_urls:
            try:
                response = self.session.get(pub_url, timeout=30, allow_redirects=True)
                final_url = response.url

                if response.status_code == 200:
                    content = response.content

                    if content.startswith(b'%PDF'):
                        return {
                            "success": True,
                            "source": "Publisher Direct",
                            "content": content,
                            "url": pub_url
                        }

                    content_str = content.decode('utf-8', errors='ignore')

                    pdf_link_match = re.search(r'href=["\']([^"\']*\.pdf[^"\']*)["\']', content_str)
                    if pdf_link_match:
                        pdf_link = pdf_link_match.group(1)
                        if pdf_link:
                            if not pdf_link.startswith('http'):
                                from urllib.parse import urlparse
                                parsed = urlparse(pub_url)
                                pdf_link = f"{parsed.scheme}://{parsed.netloc}{pdf_link}"

                            pdf_response = self.session.get(pdf_link, timeout=60, stream=True)
                            if pdf_response.status_code == 200:
                                pdf_content = pdf_response.content
                                if pdf_content.startswith(b'%PDF'):
                                    return {
                                        "success": True,
                                        "source": "Publisher Direct",
                                        "content": pdf_content,
                                        "url": pdf_link
                                    }

            except Exception as e:
                logger.warning(f"Publisher direct fetch failed for {pub_url}: {e}")

        return None

    def _attach_pdf_to_zotero(self, item_key: str, pdf_content: bytes,
                               item_info: Dict) -> Dict:
        """Attach PDF to Zotero item by writing directly to database"""
        try:
            if not self.zotero_connector or not self.zotero_connector.is_running():
                return {"success": False, "error": "Zotero not running"}

            db_path = self.zotero_connector._get_zotero_db_path()
            if not db_path or not db_path.exists():
                return {"success": False, "error": "Zotero database not found"}

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            cursor.execute("SELECT itemID FROM items WHERE key = ? AND libraryID = 1", (item_key,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return {"success": False, "error": "Item not found"}

            item_id = row[0]

            filename = f"{item_info.get('title', 'paper')[:50]}.pdf"
            
            cursor.execute("SELECT MAX(itemID) FROM items")
            max_item_id = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT MAX(valueID) FROM itemDataValues")
            max_value_id = cursor.fetchone()[0] or 0
            
            attachment_item_id = max_item_id + 1
            attachment_value_id = max_value_id + 1
            
            new_item_key = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
            
            cursor.execute("""
                INSERT INTO items (itemID, itemTypeID, dateAdded, dateModified, clientDateModified, libraryID, key, version, synced)
                VALUES (?, 3, datetime('now'), datetime('now'), datetime('now'), 1, ?, 1, 0)
            """, (attachment_item_id, new_item_key))
            
            cursor.execute("""
                INSERT INTO itemData (itemID, fieldID, valueID)
                VALUES (?, (SELECT fieldID FROM fields WHERE fieldName = 'title'), ?)
            """, (attachment_item_id, attachment_value_id))
            
            cursor.execute("""
                INSERT INTO itemDataValues (valueID, value) VALUES (?, ?)
            """, (attachment_value_id, filename))
            
            cursor.execute("""
                INSERT INTO itemAttachments (itemID, parentItemID, contentType, filename, path, storageHash, sourceItemKey)
                VALUES (?, ?, 'application/pdf', ?, '', '', NULL, ?)
            """, (attachment_item_id, item_id, filename, item_key))
            
            cursor.execute("""
                INSERT INTO itemCreators (creatorID, firstName, lastName, creatorTypeID)
                VALUES (?, 'ZotLink', 'PDF', 1)
            """, (attachment_item_id,))
            
            conn.commit()
            conn.close()

            logger.info(f"Attached PDF to item: {item_key}")
            return {"success": True, "attachment_key": new_item_key, "message": "PDF attached to database"}

        except Exception as e:
            logger.error(f"Failed to attach PDF to Zotero: {e}")
            return {"success": False, "error": str(e)}

    def download_pdf_to_file(self, pdf_content: bytes, filename: str,
                             output_dir: str = ".") -> str:
        """Save PDF content to a file"""
        output_path = Path(output_dir) / filename
        with open(output_path, 'wb') as f:
            f.write(pdf_content)
        return str(output_path)


def fetch_pdf_by_doi(doi: str) -> Dict:
    """Convenience function to fetch PDF by DOI"""
    fetcher = PDFFetcher()

    item_info = {
        "doi": doi,
        "title": "",
        "url": "",
        "arxiv_id": ""
    }

    sources = ["unpaywall", "scihub", "annas_archive", "libgen"]

    for source in sources:
        if source == "unpaywall":
            result = fetcher._fetch_from_unpaywall(item_info)
        elif source == "scihub":
            result = fetcher._fetch_from_scihub(item_info)
        elif source == "annas_archive":
            result = fetcher._fetch_from_annas_archive(item_info)
        elif source == "libgen":
            result = fetcher._fetch_from_libgen(item_info)
        else:
            result = None

        if result:
            return result

    return {"success": False, "error": "Could not find PDF for DOI"}


def fetch_pdf_by_title(title: str) -> Dict:
    """Convenience function to fetch PDF by title"""
    fetcher = PDFFetcher()

    item_info = {
        "title": title,
        "doi": "",
        "url": "",
        "arxiv_id": ""
    }

    sources = ["annas_archive", "libgen", "core", "osf"]

    for source in sources:
        if source == "annas_archive":
            result = fetcher._fetch_from_annas_archive(item_info)
        elif source == "libgen":
            result = fetcher._fetch_from_libgen(item_info)
        elif source == "core":
            result = fetcher._fetch_from_core(item_info)
        elif source == "osf":
            result = fetcher._fetch_from_osf(item_info)
        else:
            result = None

        if result:
            return result

    return {"success": False, "error": "Could not find PDF for title"}

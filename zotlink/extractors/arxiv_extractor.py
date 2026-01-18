#!/usr/bin/env python3
"""
ArXiv API Integration for ZotLink

Provides official arXiv API integration for fetching bibliographic metadata.
This replaces the HTTP scraping approach with the official arXiv API.
"""

import requests
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Optional, List, Any
from datetime import datetime
import re

logger = logging.getLogger(__name__)

ARXIV_API_BASE = "http://export.arxiv.org/api/query"


class ArxivAPIExtractor:
    """Extract metadata from arXiv using the official API"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ZotLink/1.0 (research tool)',
            'Accept': 'application/atom+xml'
        })

    def can_handle(self, url: str) -> bool:
        """Check if this extractor can handle the given URL"""
        return 'arxiv.org' in url.lower()

    def extract_metadata(self, arxiv_url: str) -> Dict[str, Any]:
        """
        Extract complete metadata from an arXiv URL using the official API.

        Args:
            arxiv_url: URL to arXiv paper (abs or pdf page)

        Returns:
            Dictionary containing all bibliographic metadata
        """
        try:
            arxiv_id = self._extract_arxiv_id(arxiv_url)
            if not arxiv_id:
                return {"error": "Could not parse arXiv ID from URL"}

            return self._query_arxiv_api(arxiv_id)

        except Exception as e:
            logger.error(f"Error extracting arXiv metadata: {e}")
            return {"error": f"Metadata extraction failed: {e}"}

    def _extract_arxiv_id(self, url: str) -> Optional[str]:
        """Extract arXiv ID from various URL formats"""
        patterns = [
            r'arxiv\.org/abs/([\d]+\.[\d]+)',
            r'arxiv\.org/pdf/([\d]+\.[\d]+)',
            r'arxiv\.org/([\d]+\.[\d]+)',
            r'arxiv:([\d]+\.[\d]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _query_arxiv_api(self, arxiv_id: str) -> Dict[str, Any]:
        """Query the official arXiv API for paper metadata"""
        try:
            params = {
                'id_list': arxiv_id,
                'max_results': 1
            }

            response = self.session.get(ARXIV_API_BASE, params=params, timeout=30)

            if response.status_code != 200:
                return {"error": f"arXiv API request failed: {response.status_code}"}

            return self._parse_arxiv_response(response.text, arxiv_id)

        except requests.RequestException as e:
            logger.error(f"arXiv API request failed: {e}")
            return {"error": f"API request failed: {e}"}

    def _parse_arxiv_response(self, xml_content: str, arxiv_id: str) -> Dict[str, Any]:
        """Parse the ATOM response from arXiv API"""
        try:
            root = ET.fromstring(xml_content)

            ns = {'atom': 'http://www.w3.org/2005/Atom',
                  'arxiv': 'http://arxiv.org/schemas/atom'}

            entry = root.find('atom:entry', ns)
            if entry is None:
                return {"error": "No entry found in arXiv response"}

            metadata = {
                'arxiv_id': arxiv_id,
                'abs_url': f"https://arxiv.org/abs/{arxiv_id}",
                'pdf_url': f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                'api_source': 'official_arxiv_api'
            }

            title = entry.find('atom:title', ns)
            if title is not None:
                title_text = ''.join(title.itertext()).strip()
                title_text = re.sub(r'\s+', ' ', title_text)
                metadata['title'] = title_text

            authors = []
            author_elements = entry.findall('atom:author', ns)
            for author in author_elements:
                name_elem = author.find('atom:name', ns)
                if name_elem is not None:
                    author_name = ''.join(name_elem.itertext()).strip()
                    if ',' in author_name:
                        parts = author_name.split(',', 1)
                        authors.append({
                            'lastName': parts[0].strip(),
                            'firstName': parts[1].strip() if len(parts) > 1 else ''
                        })
                    else:
                        parts = author_name.split()
                        if len(parts) >= 2:
                            authors.append({
                                'lastName': parts[-1],
                                'firstName': ' '.join(parts[:-1])
                            })
                        else:
                            authors.append({
                                'lastName': author_name,
                                'firstName': ''
                            })

            metadata['authors'] = authors
            metadata['authors_string'] = '; '.join(
                f"{a.get('lastName', '')}, {a.get('firstName', '')}".strip(', ')
                for a in authors
            )

            summary = entry.find('atom:summary', ns)
            if summary is not None:
                abstract_text = ''.join(summary.itertext()).strip()
                abstract_text = re.sub(r'\s+', ' ', abstract_text)
                metadata['abstract'] = abstract_text

            published = entry.find('atom:published', ns)
            if published is not None:
                date_text = ''.join(published.itertext()).strip()
                try:
                    parsed = datetime.strptime(date_text, '%Y-%m-%dT%H:%M:%SZ')
                    metadata['date'] = parsed.strftime('%Y/%m/%d')
                except ValueError:
                    metadata['date'] = date_text[:10] if len(date_text) >= 10 else date_text

            updated = entry.find('atom:updated', ns)
            if updated is not None:
                updated_text = ''.join(updated.itertext()).strip()
                metadata['updated'] = updated_text

            links = entry.findall('atom:link', ns)
            for link in links:
                rel = link.get('rel', '')
                if rel == 'alternate' or link.get('type') == 'text/html':
                    href = link.get('href', '')
                    if 'abs' in href:
                        metadata['abs_url'] = href
                    elif 'pdf' in href:
                        metadata['pdf_url'] = href

            primary_category = entry.find('arxiv:primary_category', ns)
            if primary_category is not None:
                term = primary_category.get('term', '')
                metadata['primary_subject'] = term

            categories = []
            category_elements = entry.findall('atom:category', ns)
            for cat in category_elements:
                term = cat.get('term', '')
                if term:
                    categories.append(term)
            metadata['subjects'] = categories

            doi_elem = entry.find('arxiv:doi', ns)
            if doi_elem is not None:
                doi_text = ''.join(doi_elem.itertext()).strip()
                metadata['doi'] = doi_text

            comment_elements = entry.findall('arxiv:comment', ns)
            for comment in comment_elements:
                comment_text = ''.join(comment.itertext()).strip()
                if comment_text:
                    metadata['comment'] = comment_text
                    break

            journal_ref = entry.find('arxiv:journal_ref', ns)
            if journal_ref is not None:
                journal_text = ''.join(journal_ref.itertext()).strip()
                if journal_text:
                    metadata['published_journal'] = journal_text

            metadata.setdefault('title', f'arXiv:{arxiv_id}')
            metadata.setdefault('authors_string', 'Unknown Authors')
            metadata.setdefault('date', datetime.now().strftime('%Y/%m/%d'))
            metadata.setdefault('abstract', '')

            logger.info(f"Successfully extracted arXiv metadata via API: {metadata.get('title', 'Unknown')}")
            return metadata

        except ET.ParseError as e:
            logger.error(f"Failed to parse arXiv API response: {e}")
            return {"error": f"Failed to parse API response: {e}"}

    def search_papers(self, query: str, max_results: int = 5,
                      sort_by: str = 'submittedDate',
                      sort_order: str = 'descending') -> Dict[str, Any]:
        """
        Search arXiv for papers matching a query.

        Args:
            query: Search query (supports field prefixes like ti:, au:, abs:, etc.)
            max_results: Maximum number of results to return
            sort_by: Sort field (relevance, lastUpdatedDate, submittedDate)
            sort_order: Sort order (ascending, descending)

        Returns:
            Dictionary with search results and metadata
        """
        try:
            sort_options = {
                'relevance': 'relevance',
                'lastUpdatedDate': 'lastUpdatedDate',
                'submittedDate': 'submittedDate'
            }
            sort_key = sort_options.get(sort_by, 'submittedDate')

            params = {
                'search_query': query,
                'max_results': min(max_results, 50),
                'sortBy': sort_key,
                'sortOrder': sort_order
            }

            response = self.session.get(ARXIV_API_BASE, params=params, timeout=30)

            if response.status_code != 200:
                return {"error": f"Search failed: {response.status_code}"}

            return self._parse_search_results(response.text)

        except requests.RequestException as e:
            logger.error(f"arXiv search failed: {e}")
            return {"error": f"Search failed: {e}"}

    def _parse_search_results(self, xml_content: str) -> Dict[str, Any]:
        """Parse search results from arXiv API response"""
        try:
            root = ET.fromstring(xml_content)

            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            total_results = 0
            opensearch_ns = {'opensearch': 'http://a9.com/-/spec/opensearch/1.0/'}
            total_elem = root.find('opensearch:totalResults', opensearch_ns)
            if total_elem is not None:
                total_results = int(total_elem.text) if total_elem.text else 0

            entries = []
            for entry in root.findall('atom:entry', ns):
                entry_data = {}

                id_elem = entry.find('atom:id', ns)
                if id_elem is not None:
                    id_text = ''.join(id_elem.itertext()).strip()
                    arxiv_id_match = re.search(r'([\d]+\.[\d]+)', id_text)
                    if arxiv_id_match:
                        entry_data['arxiv_id'] = arxiv_id_match.group(1)

                title_elem = entry.find('atom:title', ns)
                if title_elem is not None:
                    title_text = ''.join(title_elem.itertext()).strip()
                    title_text = re.sub(r'\s+', ' ', title_text)
                    entry_data['title'] = title_text

                authors = []
                for author in entry.findall('atom:author', ns):
                    name_elem = author.find('atom:name', ns)
                    if name_elem is not None:
                        authors.append(''.join(name_elem.itertext()).strip())
                entry_data['authors'] = authors

                summary_elem = entry.find('atom:summary', ns)
                if summary_elem is not None:
                    abstract_text = ''.join(summary_elem.itertext()).strip()
                    abstract_text = re.sub(r'\s+', ' ', abstract_text)
                    entry_data['abstract'] = abstract_text

                published_elem = entry.find('atom:published', ns)
                if published_elem is not None:
                    entry_data['published'] = ''.join(published_elem.itertext()).strip()

                links = {}
                for link in entry.findall('atom:link', ns):
                    rel = link.get('rel', '')
                    href = link.get('href', '')
                    if 'abs' in href:
                        links['abs'] = href
                    elif 'pdf' in href:
                        links['pdf'] = href
                entry_data['links'] = links

                categories = []
                for cat in entry.findall('atom:category', ns):
                    term = cat.get('term', '')
                    if term:
                        categories.append(term)
                entry_data['categories'] = categories

                entries.append(entry_data)

            return {
                'total_results': total_results,
                'entries': entries,
                'api_source': 'official_arxiv_api'
            }

        except ET.ParseError as e:
            logger.error(f"Failed to parse search results: {e}")
            return {"error": f"Failed to parse results: {e}"}


def extract_arxiv_metadata(arxiv_url: str) -> Dict[str, Any]:
    """Convenience function for extracting arXiv metadata"""
    extractor = ArxivAPIExtractor()
    return extractor.extract_metadata(arxiv_url)


def search_arxiv(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Convenience function for searching arXiv"""
    extractor = ArxivAPIExtractor()
    return extractor.search_papers(query, max_results)

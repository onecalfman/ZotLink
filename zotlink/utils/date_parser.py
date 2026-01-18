#!/usr/bin/env python3
"""
Centralized date parsing utilities for ZotLink.
"""

import re
from datetime import datetime
from typing import Optional


class DateParser:
    """Centralized date parsing and normalization for Zotero."""

    MONTHS = {
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12',
    }

    @staticmethod
    def normalize(date_str: str) -> str:
        """
        Normalize various date formats to YYYY-MM-DD.
        
        Supports:
        - "12 Jun 2017" -> "2017-06-12"
        - "2017/06/12" -> "2017-06-12"
        - "2017-06-12" -> "2017-06-12"
        - "2017" -> "2017-01-01"
        - "June 2017" -> "2017-06-01"
        """
        if not date_str or date_str == 'Unknown Date':
            return ""
        
        date_str = date_str.strip()
        
        try:
            date_match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', date_str)
            if date_match:
                day, month_name, year = date_match.groups()
                month = DateParser.MONTHS.get(month_name[:3].lower(), '01')
                return f"{year}-{month}-{day.zfill(2)}"
            
            if re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', date_str):
                return date_str
            
            if re.search(r'^\d{4}$', date_str):
                return f"{date_str}-01-01"
            
            month_match = re.search(r'(\w+)\s+(\d{4})', date_str)
            if month_match:
                month_name, year = month_match.groups()
                month = DateParser.MONTHS.get(month_name[:3].lower(), '01')
                return f"{year}-{month}-01"
            
        except Exception:
            pass
        
        return date_str

    @staticmethod
    def parse_citation_date(meta_date: str) -> str:
        """
        Parse citation_* date meta tags from HTML.
        
        Args:
            meta_date: Date from citation_date or citation_publication_date meta tag
            
        Returns:
            Normalized date string
        """
        if not meta_date:
            return ""
        
        meta_date = meta_date.strip()
        
        try:
            if re.match(r'\d{4}-\d{2}-\d{2}', meta_date):
                return meta_date
            
            date_match = re.search(r'(\d{4})/(\d{2})/(\d{2})', meta_date)
            if date_match:
                year, month, day = date_match.groups()
                return f"{year}-{month}-{day}"
            
            date_match = re.search(r'(\d{4})', meta_date)
            if date_match:
                return f"{date_match.group(1)}-01-01"
            
        except Exception:
            pass
        
        return meta_date

    @staticmethod
    def parse_arxiv_submission_date(date_str: str) -> str:
        """
        Parse arXiv submission date format like "Submitted on 12 Jun 2017".
        
        Args:
            date_str: Raw date string from arXiv
            
        Returns:
            Normalized date string
        """
        if not date_str:
            return ""
        
        try:
            date_match = re.search(r'Submitted on (\d{1,2})\s+(\w+)\s+(\d{4})', date_str)
            if date_match:
                day, month_name, year = date_match.groups()
                month = DateParser.MONTHS.get(month_name[:3].lower(), '01')
                return f"{year}-{month}-{day.zfill(2)}"
        except Exception:
            pass
        
        return date_str

    @staticmethod
    def parse_iso_date(date_str: str) -> Optional[datetime]:
        """
        Parse ISO format date string to datetime object.
        
        Args:
            date_str: ISO format date string
            
        Returns:
            datetime object or None
        """
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None

    @staticmethod
    def format_for_zotero(date_str: str) -> str:
        """
        Format date string for Zotero (YYYY-MM-DD or YYYY).
        
        Args:
            date_str: Input date string
            
        Returns:
            Zotero-compatible date format
        """
        if not date_str:
            return ""
        
        normalized = DateParser.normalize(date_str)
        
        if len(normalized) == 10:
            return normalized
        elif len(normalized) == 4:
            return normalized
        elif len(normalized) >= 10:
            return normalized[:10]
        
        return normalized

    @staticmethod
    def get_current_date() -> str:
        """Return current date in YYYY-MM-DD format."""
        return datetime.now().strftime('%Y-%m-%d')

    @staticmethod
    def get_current_year() -> str:
        """Return current year as string."""
        return str(datetime.now().year)

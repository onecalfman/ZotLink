#!/usr/bin/env python3
"""
Centralized author parsing utilities for ZotLink.
"""

import re
from typing import Dict, List, Optional


class AuthorParser:
    """Centralized author name parsing logic for Zotero compatibility."""

    @staticmethod
    def parse_author_name(name: str) -> Dict[str, str]:
        """
        Parse a single author name into firstName/lastName dict.
        
        Supports:
        - "Last, First" format
        - "First Last" format
        - Single name
        """
        name = name.strip()
        if not name or name == 'Unknown Author':
            return {"firstName": "", "lastName": ""}
        
        if ',' in name:
            parts = name.split(',', 1)
            lastName = parts[0].strip()
            firstName = parts[1].strip() if len(parts) > 1 else ""
        else:
            parts = name.split()
            if len(parts) >= 2:
                firstName = ' '.join(parts[:-1])
                lastName = parts[-1]
            else:
                firstName = ""
                lastName = name
        
        return {"firstName": firstName, "lastName": lastName}

    @staticmethod
    def parse_authors_to_zotero(authors_str: str, max_authors: int = 15) -> List[Dict]:
        """
        Parse various author string formats into Zotero creator format.
        
        Args:
            authors_str: Author string in various formats
            max_authors: Maximum number of authors to return
            
        Returns:
            List of Zotero creator dicts
        """
        authors = []
        if not authors_str:
            return authors
        
        if ';' in authors_str:
            author_names = authors_str.split(';')
        elif ' and ' in authors_str:
            author_names = [a.strip() for a in authors_str.split(' and ')]
        else:
            author_names = AuthorParser._split_comma_authors(authors_str)
        
        for author_name in author_names[:max_authors]:
            author_name = author_name.strip()
            if not author_name or author_name == 'Unknown Author':
                continue
            
            parsed = AuthorParser.parse_author_name(author_name)
            if parsed["firstName"] or parsed["lastName"]:
                authors.append({
                    "creatorType": "author",
                    "firstName": parsed["firstName"],
                    "lastName": parsed["lastName"]
                })
        
        return authors

    @staticmethod
    def _split_comma_authors(authors_str: str) -> List[str]:
        """
        Smart split comma-separated authors.
        
        Supports:
        1. "First Last, First Last" - comma-separated different authors
        2. "Last, First, Last, First" - consecutive "Last, First" format
        """
        parts = [p.strip() for p in authors_str.split(',')]
        
        if len(parts) <= 2:
            if len(parts) == 2 and ' ' in parts[0] and ' ' in parts[1]:
                return parts
            else:
                return [authors_str]
        
        all_have_spaces = all(' ' in part for part in parts)
        if all_have_spaces:
            return parts
        
        if len(parts) % 2 == 0:
            odd_indices_no_space = sum(1 for i in range(0, len(parts), 2) if ' ' not in parts[i])
            if odd_indices_no_space > len(parts) // 4:
                author_names = []
                for i in range(0, len(parts), 2):
                    if i + 1 < len(parts):
                        author_names.append(f"{parts[i]}, {parts[i+1]}")
                return author_names
        
        parts_with_space = sum(1 for part in parts if ' ' in part)
        if parts_with_space > len(parts) * 0.6:
            return parts
        
        return [authors_str]

    @staticmethod
    def format_author_for_display(authors: List[Dict]) -> str:
        """
        Format author list for display (semicolon separated).
        
        Args:
            authors: List of Zotero creator dicts
            
        Returns:
            Formatted author string
        """
        formatted = []
        for author in authors:
            last = author.get('lastName', '')
            first = author.get('firstName', '')
            if last or first:
                if first:
                    formatted.append(f"{last}, {first}")
                else:
                    formatted.append(last)
        return '; '.join(formatted)

    @staticmethod
    def parse_author_string(authors_string: str) -> str:
        """
        Convert various author input formats to consistent format.
        
        Args:
            authors_string: Input author string
            
        Returns:
            Normalized author string for Zotero
        """
        if not authors_string:
            return ""
        
        authors = AuthorParser.parse_authors_to_zotero(authors_string)
        return AuthorParser.format_author_for_display(authors)

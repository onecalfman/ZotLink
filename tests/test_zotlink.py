#!/usr/bin/env python3
"""
Test suite for ZotLink Zotero MCP Server

Tests Zotero API connectivity and functionality.
"""

import pytest
import sys
import os
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from zotlink.zotero_integration import ZoteroConnector
from zotlink.extractors.arxiv_extractor import ArxivAPIExtractor, extract_arxiv_metadata, search_arxiv
from zotlink.pdf_fetcher import PDFFetcher


class TestZoteroConnector:
    """Test cases for ZoteroConnector class"""

    @pytest.fixture
    def connector(self):
        """Create a ZoteroConnector instance"""
        return ZoteroConnector()

    def test_connector_initialization(self, connector):
        """Test connector initializes correctly"""
        assert connector.base_url == "http://127.0.0.1:23119"
        assert connector.session is not None
        assert 'User-Agent' in connector.session.headers

    @patch('requests.Session.get')
    def test_is_running_true(self, mock_get, connector):
        """Test is_running returns True when Zotero responds"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = connector.is_running()
        assert result is True

    @patch('requests.Session.get')
    def test_is_running_false(self, mock_get, connector):
        """Test is_running returns False when connection fails"""
        mock_get.side_effect = Exception("Connection refused")

        result = connector.is_running()
        assert result is False

    @patch('requests.Session.get')
    def test_get_version(self, mock_get, connector):
        """Test get_version returns version when Zotero is running"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Zotero is running"
        mock_get.return_value = mock_response

        with patch.object(connector, 'is_running', return_value=True):
            version = connector.get_version()
            assert version is not None

    @patch('requests.Session.get')
    def test_get_version_when_not_running(self, mock_get, connector):
        """Test get_version returns None when Zotero is not running"""
        with patch.object(connector, 'is_running', return_value=False):
            version = connector.get_version()
            assert version is None

    @patch('requests.Session.get')
    def test_get_collections_empty(self, mock_get, connector):
        """Test get_collections returns empty list when Zotero not running"""
        with patch.object(connector, 'is_running', return_value=False):
            collections = connector.get_collections()
            assert collections == []

    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_save_item_to_zotero_not_running(self, mock_get, mock_post, connector):
        """Test save_item_to_zotero returns error when Zotero not running"""
        with patch.object(connector, 'is_running', return_value=False):
            paper_info = {"title": "Test Paper", "url": "https://arxiv.org/abs/1234.5678"}
            result = connector.save_item_to_zotero(paper_info)
            assert result["success"] is False
            assert "Zotero is not running" in result["message"]

    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_get_library_items(self, mock_get, mock_post, connector):
        """Test get_library_items returns items from API"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"itemKey": "ABC123", "title": "Test Paper"}]
        mock_get.return_value = mock_response

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.get_library_items(limit=10)
            assert result["success"] is True
            assert "items" in result

    @patch('requests.Session.get')
    def test_search_items(self, mock_get, connector):
        """Test search_items returns matching items"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"itemKey": "ABC123", "title": "Machine Learning Paper"}
        ]
        mock_get.return_value = mock_response

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.search_items("machine learning")
            assert result["success"] is True

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_get_item(self, mock_db_path, connector):
        """Test get_item returns specific item from database"""
        import tempfile
        import sqlite3
        from pathlib import Path

        mock_db_path.return_value = Path(tempfile.mktemp(suffix='.sqlite'))

        conn = sqlite3.connect(str(mock_db_path.return_value))
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS items (
            itemID INTEGER PRIMARY KEY, key TEXT UNIQUE, itemTypeID INTEGER,
            dateAdded TEXT, dateModified TEXT, libraryID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemTypes (
            itemTypeID INTEGER PRIMARY KEY, typeName TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemData (
            itemID INTEGER, fieldID INTEGER, valueID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS fields (
            fieldID INTEGER PRIMARY KEY, fieldName TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemDataValues (
            valueID INTEGER PRIMARY KEY, value TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS creators (
            creatorID INTEGER PRIMARY KEY, firstName TEXT, lastName TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemCreators (
            itemID INTEGER, creatorID INTEGER, creatorTypeID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS creatorTypes (
            creatorTypeID INTEGER PRIMARY KEY, creatorType TEXT
        )''')
        cursor.execute("INSERT INTO items (key, itemTypeID, libraryID) VALUES (?, 1, 1)",
                       ("ABC123",))
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (1, 'journalArticle')")
        conn.commit()
        conn.close()

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.get_item("ABC123")
            assert result["success"] is True
            assert result["item"]["itemKey"] == "ABC123"

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_update_item(self, mock_db_path, connector):
        """Test update_item modifies item in database"""
        import tempfile
        import sqlite3
        from pathlib import Path

        mock_db_path.return_value = Path(tempfile.mktemp(suffix='.sqlite'))

        conn = sqlite3.connect(str(mock_db_path.return_value))
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS items (
            itemID INTEGER PRIMARY KEY, key TEXT UNIQUE, itemTypeID INTEGER,
            dateAdded TEXT, dateModified TEXT, libraryID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemTypes (
            itemTypeID INTEGER PRIMARY KEY, typeName TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS fields (
            fieldID INTEGER PRIMARY KEY, fieldName TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemDataValues (
            valueID INTEGER PRIMARY KEY, value TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemData (
            itemID INTEGER, fieldID INTEGER, valueID INTEGER
        )''')
        cursor.execute("INSERT INTO items (key, itemTypeID, libraryID) VALUES (?, 1, 1)",
                       ("ABC123",))
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (1, 'journalArticle')")
        cursor.execute("INSERT INTO fields (fieldID, fieldName) VALUES (1, 'title')")
        conn.commit()
        conn.close()

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.update_item("ABC123", {"title": "Updated Title"})
            assert result["success"] is True

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_update_item_tags(self, mock_db_path, connector):
        """Test update_item_tags modifies tags in database"""
        import tempfile
        import sqlite3
        from pathlib import Path

        mock_db_path.return_value = Path(tempfile.mktemp(suffix='.sqlite'))

        conn = sqlite3.connect(str(mock_db_path.return_value))
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS items (
            itemID INTEGER PRIMARY KEY, key TEXT UNIQUE, itemTypeID INTEGER,
            dateAdded TEXT, dateModified TEXT, libraryID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemTypes (
            itemTypeID INTEGER PRIMARY KEY, typeName TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS tags (
            tagID INTEGER PRIMARY KEY, name TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemTags (
            itemID INTEGER, tagID INTEGER, type INTEGER
        )''')
        cursor.execute("INSERT INTO items (key, itemTypeID, libraryID) VALUES (?, 1, 1)",
                       ("ABC123",))
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (1, 'journalArticle')")
        conn.commit()
        conn.close()

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.update_item_tags("ABC123", ["tag1", "tag2"])
            assert result["success"] is True

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_delete_item(self, mock_db_path, connector):
        """Test delete_item removes item from database"""
        import tempfile
        import sqlite3
        from pathlib import Path

        mock_db_path.return_value = Path(tempfile.mktemp(suffix='.sqlite'))

        conn = sqlite3.connect(str(mock_db_path.return_value))
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS items (
            itemID INTEGER PRIMARY KEY, key TEXT UNIQUE, itemTypeID INTEGER,
            dateAdded TEXT, dateModified TEXT, libraryID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemTypes (
            itemTypeID INTEGER PRIMARY KEY, typeName TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemTags (
            itemID INTEGER, tagID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemCreators (
            itemID INTEGER, creatorID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemData (
            itemID INTEGER, fieldID INTEGER, valueID INTEGER
        )''')
        cursor.execute("INSERT INTO items (key, itemTypeID, libraryID) VALUES (?, 1, 1)",
                       ("ABC123",))
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (1, 'journalArticle')")
        conn.commit()
        conn.close()

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.delete_item("ABC123")
            assert result["success"] is True

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_move_item_to_collection(self, mock_db_path, connector):
        """Test move_item_to_collection adds item to collection in database"""
        import tempfile
        import sqlite3
        from pathlib import Path

        mock_db_path.return_value = Path(tempfile.mktemp(suffix='.sqlite'))

        conn = sqlite3.connect(str(mock_db_path.return_value))
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS items (
            itemID INTEGER PRIMARY KEY, key TEXT UNIQUE, itemTypeID INTEGER,
            dateAdded TEXT, dateModified TEXT, libraryID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemTypes (
            itemTypeID INTEGER PRIMARY KEY, typeName TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS collections (
            collectionID INTEGER PRIMARY KEY, collectionKey TEXT, libraryID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS collectionItems (
            collectionID INTEGER, itemID INTEGER
        )''')
        cursor.execute("INSERT INTO items (key, itemTypeID, libraryID) VALUES (?, 1, 1)",
                       ("ABC123",))
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (1, 'journalArticle')")
        cursor.execute("INSERT INTO collections (collectionKey, libraryID) VALUES (?, 1)",
                       ("COLLECTION456",))
        conn.commit()
        conn.close()

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.move_item_to_collection("ABC123", "COLLECTION456")
            assert result["success"] is True


class TestArxivAPIExtractor:
    """Test cases for arXiv API integration"""

    @pytest.fixture
    def extractor(self):
        """Create an ArxivAPIExtractor instance"""
        return ArxivAPIExtractor()

    def test_extract_arxiv_id_from_abs_url(self, extractor):
        """Test extracting arXiv ID from abstract URL"""
        url = "https://arxiv.org/abs/1706.03762"
        arxiv_id = extractor._extract_arxiv_id(url)
        assert arxiv_id == "1706.03762"

    def test_extract_arxiv_id_from_pdf_url(self, extractor):
        """Test extracting arXiv ID from PDF URL"""
        url = "https://arxiv.org/pdf/1706.03762.pdf"
        arxiv_id = extractor._extract_arxiv_id(url)
        assert arxiv_id == "1706.03762"

    def test_extract_arxiv_id_from_complex_url(self, extractor):
        """Test extracting arXiv ID from URL with version"""
        url = "https://arxiv.org/abs/1706.03762v5"
        arxiv_id = extractor._extract_arxiv_id(url)
        assert arxiv_id == "1706.03762"

    def test_extract_arxiv_id_invalid_url(self, extractor):
        """Test extracting arXiv ID from invalid URL returns None"""
        url = "https://example.com/paper"
        arxiv_id = extractor._extract_arxiv_id(url)
        assert arxiv_id is None

    @pytest.fixture
    def mock_arxiv_response(self):
        """Sample arXiv API XML response"""
        return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <title>Attention Is All You Need</title>
    <summary>The paper describes the Transformer model.</summary>
    <published>2017-06-12T00:00:00Z</published>
    <updated>2018-01-10T00:00:00Z</updated>
    <author>
      <name>Vaswani, Ashish</name>
    </author>
    <author>
      <name>Shazeer, Noam</name>
    </author>
    <link rel="alternate" type="text/html" href="https://arxiv.org/abs/1706.03762v5"/>
    <link rel="related" type="application/pdf" href="https://arxiv.org/pdf/1706.03762v5.pdf"/>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.CL"/>
    <arxiv:doi xmlns:arxiv="http://arxiv.org/schemas/atom">10.48550/arXiv.1706.03762</arxiv:doi>
    <arxiv:journal_ref xmlns:arxiv="http://arxiv.org/schemas/atom">NIPS 2017</arxiv:journal_ref>
  </entry>
</feed>"""

    @patch('requests.Session.get')
    def test_parse_arxiv_response(self, mock_get, extractor, mock_arxiv_response):
        """Test parsing arXiv API XML response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_arxiv_response
        mock_get.return_value = mock_response

        result = extractor._query_arxiv_api("1706.03762")

        assert result["arxiv_id"] == "1706.03762"
        assert "Attention Is All You Need" in result["title"]
        assert len(result["authors"]) >= 2
        assert result["doi"] == "10.48550/arXiv.1706.03762"
        assert result["published_journal"] == "NIPS 2017"

    @patch('requests.Session.get')
    def test_extract_metadata_url_not_running(self, mock_get, extractor):
        """Test extract_metadata returns error when API fails"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = extractor.extract_metadata("https://arxiv.org/abs/1706.03762")
        assert "error" in result

    def test_extract_metadata_invalid_url(self, extractor):
        """Test extract_metadata returns error for invalid URL"""
        result = extractor.extract_metadata("https://example.com/paper")
        assert "error" in result

    @patch('requests.Session.get')
    def test_search_papers(self, mock_get, extractor):
        """Test search_papers returns results"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.0/">
  <opensearch:totalResults>10</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <title>Test Paper</title>
    <published>2017-06-12T00:00:00Z</published>
    <link rel="alternate" type="text/html" href="https://arxiv.org/abs/1706.03762v5"/>
    <link rel="related" type="application/pdf" href="https://arxiv.org/pdf/1706.03762v5.pdf"/>
  </entry>
</feed>"""
        mock_get.return_value = mock_response

        result = extractor.search_papers("transformer", max_results=5)

        assert "total_results" in result
        assert "entries" in result
        assert result["total_results"] == 10


class TestConvenienceFunctions:
    """Test convenience functions"""

    @patch('requests.Session.get')
    def test_extract_arxiv_metadata_function(self, mock_get):
        """Test extract_arxiv_metadata convenience function"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <title>Test Paper</title>
    <summary>Abstract here</summary>
    <published>2017-06-12T00:00:00Z</published>
    <author><name>Test Author</name></author>
  </entry>
</feed>"""
        mock_get.return_value = mock_response

        result = extract_arxiv_metadata("https://arxiv.org/abs/1706.03762")

        assert "arxiv_id" in result or "error" in result

    @patch('requests.Session.get')
    def test_search_arxiv_function(self, mock_get):
        """Test search_arxiv convenience function"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.0/">
  <opensearch:totalResults>2</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/1234.5678v1</id>
    <title>Paper 1</title>
    <published>2020-01-01T00:00:00Z</published>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/9876.5432v1</id>
    <title>Paper 2</title>
    <published>2020-02-01T00:00:00Z</published>
  </entry>
</feed>"""
        mock_get.return_value = mock_response

        result = search_arxiv("neural networks", max_results=10)

        assert "entries" in result


class TestIntegration:
    """Integration tests that require actual Zotero connection"""

    def test_zotero_connection_integration(self):
        """Test actual Zotero connection (if running)"""
        connector = ZoteroConnector()
        is_running = connector.is_running()

        if is_running:
            version = connector.get_version()
            collections = connector.get_collections()

            assert version is not None
            assert isinstance(collections, list)

    def test_zotero_item_operations_integration(self):
        """Test actual Zotero item operations (if running)"""
        connector = ZoteroConnector()

        if not connector.is_running():
            pytest.skip("Zotero not running")

        result = connector.get_library_items(limit=5)
        assert result["success"] is True or "error" in result


class TestAuthorParsing:
    """Test author name parsing logic"""

    @pytest.fixture
    def author_parser(self):
        from zotlink.utils import AuthorParser
        return AuthorParser()

    def test_split_comma_authors_single_author(self, author_parser):
        """Test splitting single author in Last, First format"""
        result = author_parser._split_comma_authors("Smith, John")
        assert result == ["Smith, John"]

    def test_split_comma_authors_two_authors(self, author_parser):
        """Test splitting two authors in First Last, First Last format"""
        result = author_parser._split_comma_authors("John Smith, Jane Doe")
        assert len(result) == 2

    def test_split_comma_authors_multiple(self, author_parser):
        """Test splitting multiple authors"""
        result = author_parser._split_comma_authors("John Smith, Jane Doe, Bob Chen")
        assert len(result) == 3


class TestMetadataValidation:
    """Test metadata validation against arXiv API"""

    @pytest.fixture
    def connector(self):
        return ZoteroConnector()

    def test_extract_arxiv_id_from_doi(self, connector):
        """Test extracting arXiv ID from DOI"""
        doi = "10.48550/arXiv.1706.03762"
        result = connector._get_arxiv_url_from_doi(doi)
        assert result is not None
        assert "1706.03762" in result

    def test_extract_arxiv_id_from_invalid_doi(self, connector):
        """Test extracting arXiv ID from non-arXiv DOI"""
        doi = "10.1038/nature12345"
        result = connector._get_arxiv_url_from_doi(doi)
        assert result is None

    def test_compare_metadata_titles(self, connector):
        """Test metadata comparison for titles"""
        zotero = {"title": "Attention Is All You Need", "abstract": "", "date": "", "creators": [], "doi": ""}
        arxiv = {"title": "Attention Is All You Need", "abstract": "", "date": "", "authors": []}

        diffs = connector._compare_metadata(zotero, arxiv)
        assert "title" not in diffs

    def test_compare_metadata_different_titles(self, connector):
        """Test detecting different titles"""
        zotero = {"title": "Old Title", "abstract": "", "date": "", "creators": [], "doi": ""}
        arxiv = {"title": "New Title", "abstract": "", "date": "", "authors": []}

        diffs = connector._compare_metadata(zotero, arxiv)
        assert "title" in diffs
        assert diffs["title"][0]["value"] == "Old Title"
        assert diffs["title"][1]["value"] == "New Title"

    def test_normalize_abstract(self, connector):
        """Test abstract normalization"""
        abstract1 = "This   is   a   test"
        abstract2 = "This is a test"
        assert connector._normalize_abstract(abstract1) == connector._normalize_abstract(abstract2)

    def test_extract_last_names(self, connector):
        """Test extracting last names from creators"""
        creators = [
            {"creatorType": "author", "lastName": "Smith", "firstName": "John"},
            {"creatorType": "author", "lastName": "Doe", "firstName": "Jane"},
            {"creatorType": "editor", "lastName": "Editor", "firstName": "Ed"}
        ]
        result = connector._extract_last_names(creators)
        assert result == ["Smith", "Doe"]
        assert "Editor" not in result


class TestPDFFetcher:
    """Test PDF fetching functionality"""

    @pytest.fixture
    def fetcher(self):
        return PDFFetcher()

    def test_extract_arxiv_id_from_url(self, fetcher):
        """Test arXiv ID extraction from URL"""
        assert fetcher._extract_arxiv_id("https://arxiv.org/abs/1706.03762") == "1706.03762"
        assert fetcher._extract_arxiv_id("https://arxiv.org/pdf/1706.03762.pdf") == "1706.03762"
        assert fetcher._extract_arxiv_id("https://example.com/paper") is None

    def test_get_source_order_auto(self, fetcher):
        """Test source order for auto mode"""
        order = fetcher._get_source_order("auto")
        assert order == ["arxiv", "mdpi", "open_access", "scihub", "annas_archive", "libgen", "publisher"]

    def test_get_source_order_specific(self, fetcher):
        """Test source order for specific source"""
        order = fetcher._get_source_order("scihub")
        assert order[0] == "scihub"
        assert "scihub" in order

    def test_get_source_order_invalid(self, fetcher):
        """Test source order for invalid source"""
        order = fetcher._get_source_order("invalid")
        assert len(order) == 7

    @patch('requests.Session.get')
    def test_fetch_from_arxiv_success(self, mock_get, fetcher):
        """Test successful arXiv PDF fetch"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'%PDF-1.4 test pdf content'
        mock_get.return_value = mock_response

        item_info = {"arxiv_id": "1706.03762", "doi": "", "title": "Test", "url": ""}
        result = fetcher._fetch_from_arxiv(item_info)

        assert result is not None
        assert result["success"] is True
        assert result["source"] == "arXiv"

    @patch('requests.Session.get')
    def test_fetch_from_arxiv_not_pdf(self, mock_get, fetcher):
        """Test arXiv fetch with non-PDF response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'not a pdf'
        mock_get.return_value = mock_response

        item_info = {"arxiv_id": "1706.03762", "doi": "", "title": "Test", "url": ""}
        result = fetcher._fetch_from_arxiv(item_info)

        assert result is None

    def test_fetch_from_arxiv_no_id(self, fetcher):
        """Test arXiv fetch without arXiv ID"""
        item_info = {"arxiv_id": None, "doi": "", "title": "Test", "url": ""}
        result = fetcher._fetch_from_arxiv(item_info)
        assert result is None

    def test_fetch_from_mdpi_no_doi(self, fetcher):
        """Test MDPI fetch without DOI"""
        item_info = {"doi": "", "title": "Test", "url": ""}
        result = fetcher._fetch_from_mdpi(item_info)
        assert result is None

    def test_fetch_from_mdpi_non_mdpi_doi(self, fetcher):
        """Test MDPI fetch with non-MDPI DOI"""
        item_info = {"doi": "10.1038/nature12345", "title": "Test", "url": ""}
        result = fetcher._fetch_from_mdpi(item_info)
        assert result is None

    @patch('requests.Session.get')
    def test_fetch_from_unpaywall(self, mock_get, fetcher):
        """Test Unpaywall PDF fetch"""
        mock_article_response = Mock()
        mock_article_response.status_code = 200
        mock_article_response.json.return_value = {
            "best_oa_location": {
                "url_for_pdf": "https://example.com/paper.pdf"
            }
        }

        mock_pdf_response = Mock()
        mock_pdf_response.status_code = 200
        mock_pdf_response.content = b'%PDF-1.4 test'

        mock_get.side_effect = [mock_article_response, mock_pdf_response]

        item_info = {"doi": "10.1000/xyz123", "title": "Test", "url": ""}
        result = fetcher._fetch_from_unpaywall(item_info)

        assert result is not None
        assert result["success"] is True
        assert result["source"] == "Unpaywall"

    @patch('requests.Session.get')
    def test_fetch_from_semantic_scholar(self, mock_get, fetcher):
        """Test Semantic Scholar PDF fetch"""
        mock_paper_response = Mock()
        mock_paper_response.status_code = 200
        mock_paper_response.json.return_value = {
            "openAccessPdf": {"url": "https://pdfs.semanticscholar.org/test.pdf"},
            "externalIds": {"DOI": "10.1000/xyz123"}
        }

        mock_pdf_response = Mock()
        mock_pdf_response.status_code = 200
        mock_pdf_response.content = b'%PDF-1.4 test'

        mock_get.side_effect = [mock_paper_response, mock_pdf_response]

        item_info = {"doi": "10.1000/xyz123", "title": "Test", "url": ""}
        result = fetcher._fetch_from_semantic_scholar(item_info)

        assert result is not None
        assert result["success"] is True

    def test_download_pdf_to_file(self, fetcher):
        """Test saving PDF to file"""
        import tempfile
        import os

        pdf_content = b'%PDF-1.4 test content'

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = fetcher.download_pdf_to_file(pdf_content, "test.pdf", tmpdir)
            assert os.path.exists(filepath)
            with open(filepath, 'rb') as f:
                assert f.read() == pdf_content


class TestPDFValidationIntegration:
    """Integration tests for validation and PDF fetching"""

    def test_validate_item_integration(self):
        """Test item validation with actual Zotero connection"""
        connector = ZoteroConnector()

        if not connector.is_running():
            pytest.skip("Zotero not running")

        result = connector.get_library_items(limit=1)
        if not result.get("success"):
            pytest.skip("Could not get library items")

        items = result.get("items", [])
        if not items:
            pytest.skip("No items in library")

        item_key = items[0].get("itemKey") if isinstance(items[0], dict) else items[0].get("key")
        if not item_key:
            pytest.skip("Could not get item key")

        validation = connector.validate_item_with_arxiv(item_key)

        assert "success" in validation
        assert "item_key" in validation

    def test_fetch_pdf_integration(self):
        """Test PDF fetching with actual Zotero connection"""
        from zotlink.pdf_fetcher import PDFFetcher

        connector = ZoteroConnector()
        fetcher = PDFFetcher(connector)

        if not connector.is_running():
            pytest.skip("Zotero not running")

        result = connector.get_library_items(limit=1)
        if not result.get("success"):
            pytest.skip("Could not get library items")

        items = result.get("items", [])
        if not items:
            pytest.skip("No items in library")

        item_key = items[0].get("itemKey") if isinstance(items[0], dict) else items[0].get("key")
        if not item_key:
            pytest.skip("Could not get item key")

        fetch_result = fetcher.fetch_pdf(item_key, source="arxiv", save_to_zotero=False)

        assert "success" in fetch_result


class TestMCPServerEntryPoints:
    """Test MCP server entry points and tool definitions"""

    def test_run_function_exists(self):
        """Test that run function exists and is importable"""
        from zotlink.zotero_mcp_server import run
        assert callable(run)

    def test_save_paper_by_doi_tool_defined(self):
        """Test that save_paper_by_doi tool is registered"""
        from zotlink.zotero_mcp_server import handle_list_tools
        import asyncio
        tools = asyncio.run(handle_list_tools())
        tool_names = [t.name for t in tools]
        assert "save_paper_by_doi" in tool_names

    def test_get_cookie_sync_status_removed(self):
        """Test that internal tools are not exposed"""
        from zotlink.zotero_mcp_server import handle_list_tools
        import asyncio
        tools = asyncio.run(handle_list_tools())
        tool_names = [t.name for t in tools]
        assert "get_cookie_sync_status" not in tool_names
        assert "set_database_cookies" not in tool_names
        assert "generate_bookmark_code" not in tool_names
        assert "get_cookie_guide" not in tool_names

    def test_tools_have_english_descriptions(self):
        """Test that all tool descriptions are in English"""
        from zotlink.zotero_mcp_server import handle_list_tools
        import asyncio
        tools = asyncio.run(handle_list_tools())
        for tool in tools:
            desc = tool.description.lower()
            chinese_indicators = ["保存", "获取", "论文", "集合", "数据库", "认证", "连接"]
            for indicator in chinese_indicators:
                assert indicator not in desc, f"Tool '{tool.name}' has Chinese description"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestItemAttachmentsNotesTags:
    """Test cases for item attachments, notes, and tags retrieval"""

    @pytest.fixture
    def connector(self):
        """Create a ZoteroConnector instance"""
        return ZoteroConnector()

    def _create_test_database(self, tmp_path):
        """Create a test database with full schema including attachments, notes, tags"""
        db_path = tmp_path / "test_zotero.sqlite"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS items (
            itemID INTEGER PRIMARY KEY, key TEXT UNIQUE, itemTypeID INTEGER,
            itemType TEXT, dateAdded TEXT, dateModified TEXT, libraryID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemTypes (
            itemTypeID INTEGER PRIMARY KEY, typeName TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemData (
            itemID INTEGER, fieldID INTEGER, valueID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS fields (
            fieldID INTEGER PRIMARY KEY, fieldName TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemDataValues (
            valueID INTEGER PRIMARY KEY, value TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS creators (
            creatorID INTEGER PRIMARY KEY, firstName TEXT, lastName TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemCreators (
            itemID INTEGER, creatorID INTEGER, creatorTypeID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS creatorTypes (
            creatorTypeID INTEGER PRIMARY KEY, creatorType TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS attachments (
            itemID INTEGER PRIMARY KEY, parentItemID INTEGER,
            path TEXT, filename TEXT, contentType TEXT, storagePath TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS notes (
            itemID INTEGER PRIMARY KEY, parentItemID INTEGER, note TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS tags (
            tagID INTEGER PRIMARY KEY, name TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemTags (
            itemID INTEGER, tagID INTEGER, type INTEGER
        )''')
        
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (1, 'journalArticle')")
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (2, 'attachment')")
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (14, 'note')")
        
        cursor.execute("INSERT INTO fields (fieldID, fieldName) VALUES (1, 'title')")
        
        cursor.execute("INSERT INTO items (key, itemTypeID, itemType, libraryID, dateAdded) VALUES (?, 1, 'journalArticle', 1, datetime('now'))",
                       ("ITEM123",))
        cursor.execute("INSERT INTO items (key, itemTypeID, itemType, libraryID, dateAdded) VALUES (?, 2, 'attachment', 1, datetime('now'))",
                       ("ATTACH456",))
        cursor.execute("INSERT INTO items (key, itemTypeID, itemType, libraryID, dateAdded) VALUES (?, 14, 'note', 1, datetime('now'))",
                       ("NOTE789",))
        
        cursor.execute("INSERT INTO itemDataValues (valueID, value) VALUES (1, 'Test Paper Title')")
        cursor.execute("INSERT INTO itemData (itemID, fieldID, valueID) VALUES (1, 1, 1)")
        
        cursor.execute("INSERT INTO attachments (itemID, parentItemID, path, filename, contentType, storagePath) VALUES (?, 1, 'storage/AB123456/file.pdf', 'paper.pdf', 'application/pdf', 'storage/AB123456')",
                       (2,))
        
        cursor.execute("INSERT INTO notes (itemID, parentItemID, note) VALUES (?, 1, 'This is a test note')",
                       (3,))
        
        cursor.execute("INSERT INTO tags (tagID, name) VALUES (1, 'machine-learning')")
        cursor.execute("INSERT INTO tags (tagID, name) VALUES (2, 'ai')")
        cursor.execute("INSERT INTO itemTags (itemID, tagID, type) VALUES (1, 1, 0)")
        cursor.execute("INSERT INTO itemTags (itemID, tagID, type) VALUES (1, 2, 0)")
        
        conn.commit()
        conn.close()
        return db_path

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_get_item_attachments(self, mock_db_path, connector, tmp_path):
        """Test _get_item_attachments returns attachment data"""
        db_path = self._create_test_database(tmp_path)
        mock_db_path.return_value = db_path

        with patch.object(connector, 'is_running', return_value=True):
            attachments = connector._get_item_attachments(1)
            assert len(attachments) == 1
            assert attachments[0]["filename"] == "paper.pdf"
            assert attachments[0]["contentType"] == "application/pdf"

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_get_item_notes(self, mock_db_path, connector, tmp_path):
        """Test _get_item_notes returns note data"""
        db_path = self._create_test_database(tmp_path)
        mock_db_path.return_value = db_path

        with patch.object(connector, 'is_running', return_value=True):
            notes = connector._get_item_notes(1)
            assert len(notes) == 1
            assert "test note" in notes[0]["note"]

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_get_item_tags(self, mock_db_path, connector, tmp_path):
        """Test _get_item_tags returns tag data"""
        db_path = self._create_test_database(tmp_path)
        mock_db_path.return_value = db_path

        with patch.object(connector, 'is_running', return_value=True):
            tags = connector._get_item_tags(1)
            assert len(tags) == 2
            tag_names = [t["name"] for t in tags]
            assert "machine-learning" in tag_names
            assert "ai" in tag_names

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_get_item_with_attachments(self, mock_db_path, connector, tmp_path):
        """Test get_item returns attachments when include_attachments=True"""
        db_path = self._create_test_database(tmp_path)
        mock_db_path.return_value = db_path

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.get_item("ITEM123", include_attachments=True)
            assert result["success"] is True
            item = result["item"]
            assert "attachments" in item
            assert len(item["attachments"]) == 1
            assert item["attachments"][0]["filename"] == "paper.pdf"

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_get_item_with_notes(self, mock_db_path, connector, tmp_path):
        """Test get_item returns notes when include_attachments=True"""
        db_path = self._create_test_database(tmp_path)
        mock_db_path.return_value = db_path

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.get_item("ITEM123", include_attachments=True)
            assert result["success"] is True
            item = result["item"]
            assert "notes" in item
            assert len(item["notes"]) == 1

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_get_item_with_tags(self, mock_db_path, connector, tmp_path):
        """Test get_item returns tags when include_attachments=True"""
        db_path = self._create_test_database(tmp_path)
        mock_db_path.return_value = db_path

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.get_item("ITEM123", include_attachments=True)
            assert result["success"] is True
            item = result["item"]
            assert "tags" in item
            assert "machine-learning" in item["tags"]
            assert "tags_detail" in item
            assert len(item["tags_detail"]) == 2

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_get_item_without_attachments(self, mock_db_path, connector, tmp_path):
        """Test get_item skips attachments when include_attachments=False"""
        db_path = self._create_test_database(tmp_path)
        mock_db_path.return_value = db_path

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.get_item("ITEM123", include_attachments=False)
            assert result["success"] is True
            item = result["item"]
            assert "attachments" not in item
            assert "notes" not in item
            assert "tags" not in item


class TestLibraryItemsWithDetails:
    """Test cases for get_library_items with include_details parameter"""

    @pytest.fixture
    def connector(self):
        """Create a ZoteroConnector instance"""
        return ZoteroConnector()

    def _create_test_database_for_library(self, tmp_path):
        """Create a test database for library items testing"""
        db_path = tmp_path / "test_library.sqlite"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS items (
            itemID INTEGER PRIMARY KEY, key TEXT UNIQUE, itemTypeID INTEGER,
            itemType TEXT, dateAdded TEXT, dateModified TEXT, libraryID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemTypes (
            itemTypeID INTEGER PRIMARY KEY, typeName TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemData (
            itemID INTEGER, fieldID INTEGER, valueID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS fields (
            fieldID INTEGER PRIMARY KEY, fieldName TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemDataValues (
            valueID INTEGER PRIMARY KEY, value TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS attachments (
            itemID INTEGER PRIMARY KEY, parentItemID INTEGER,
            path TEXT, filename TEXT, contentType TEXT, storagePath TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS notes (
            itemID INTEGER PRIMARY KEY, parentItemID INTEGER, note TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS tags (
            tagID INTEGER PRIMARY KEY, name TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemTags (
            itemID INTEGER, tagID INTEGER, type INTEGER
        )''')
        
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (1, 'journalArticle')")
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (2, 'attachment')")
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (14, 'note')")
        cursor.execute("INSERT INTO fields (fieldID, fieldName) VALUES (1, 'title')")
        
        cursor.execute("INSERT INTO items (key, itemTypeID, itemType, libraryID, dateAdded, dateModified) VALUES (?, 1, 'journalArticle', 1, datetime('now'), datetime('now'))",
                       ("LIBRARY001",))
        cursor.execute("INSERT INTO items (key, itemTypeID, itemType, libraryID, dateAdded, dateModified) VALUES (?, 1, 'journalArticle', 1, datetime('now'), datetime('now'))",
                       ("LIBRARY002",))
        
        # Attachment items need to exist in the items table for the join to work
        cursor.execute("INSERT INTO items (key, itemTypeID, itemType, libraryID, dateAdded, dateModified) VALUES (?, 2, 'attachment', 1, datetime('now'), datetime('now'))",
                       ("ATTACH001",))
        cursor.execute("INSERT INTO items (key, itemTypeID, itemType, libraryID, dateAdded, dateModified) VALUES (?, 2, 'attachment', 1, datetime('now'), datetime('now'))",
                       ("ATTACH002",))
        cursor.execute("INSERT INTO items (key, itemTypeID, itemType, libraryID, dateAdded, dateModified) VALUES (?, 2, 'attachment', 1, datetime('now'), datetime('now'))",
                       ("ATTACH003",))
        
        # Note items need to exist in the items table for the join to work
        cursor.execute("INSERT INTO items (key, itemTypeID, itemType, libraryID, dateAdded, dateModified) VALUES (?, 14, 'note', 1, datetime('now'), datetime('now'))",
                       ("NOTE001",))
        cursor.execute("INSERT INTO items (key, itemTypeID, itemType, libraryID, dateAdded, dateModified) VALUES (?, 14, 'note', 1, datetime('now'), datetime('now'))",
                       ("NOTE002",))
        
        cursor.execute("INSERT INTO itemDataValues (valueID, value) VALUES (1, 'First Paper')")
        cursor.execute("INSERT INTO itemDataValues (valueID, value) VALUES (2, 'Second Paper')")
        cursor.execute("INSERT INTO itemData (itemID, fieldID, valueID) VALUES (1, 1, 1)")
        cursor.execute("INSERT INTO itemData (itemID, fieldID, valueID) VALUES (2, 1, 2)")
        
        cursor.execute("INSERT INTO attachments (itemID, parentItemID, path, filename, contentType, storagePath) VALUES (?, 1, 'storage1/paper1.pdf', 'paper1.pdf', 'application/pdf', 'storage1')",
                       (3,))
        cursor.execute("INSERT INTO attachments (itemID, parentItemID, path, filename, contentType, storagePath) VALUES (?, 1, 'storage2/paper2.pdf', 'paper2.pdf', 'application/pdf', 'storage2')",
                       (4,))
        cursor.execute("INSERT INTO attachments (itemID, parentItemID, path, filename, contentType, storagePath) VALUES (?, 2, 'storage3/paper3.pdf', 'paper3.pdf', 'application/pdf', 'storage3')",
                       (5,))
        
        cursor.execute("INSERT INTO notes (itemID, parentItemID, note) VALUES (?, 1, 'Note 1')",
                       (6,))
        cursor.execute("INSERT INTO notes (itemID, parentItemID, note) VALUES (?, 1, 'Note 2')",
                       (7,))
        
        cursor.execute("INSERT INTO tags (tagID, name) VALUES (1, 'tag1')")
        cursor.execute("INSERT INTO tags (tagID, name) VALUES (2, 'tag2')")
        cursor.execute("INSERT INTO tags (tagID, name) VALUES (3, 'tag3')")
        cursor.execute("INSERT INTO itemTags (itemID, tagID, type) VALUES (1, 1, 0)")
        cursor.execute("INSERT INTO itemTags (itemID, tagID, type) VALUES (1, 2, 0)")
        cursor.execute("INSERT INTO itemTags (itemID, tagID, type) VALUES (1, 3, 0)")
        cursor.execute("INSERT INTO itemTags (itemID, tagID, type) VALUES (2, 1, 0)")
        
        conn.commit()
        conn.close()
        return db_path

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_get_library_items_without_details(self, mock_db_path, connector, tmp_path):
        """Test get_library_items returns basic info without details"""
        db_path = self._create_test_database_for_library(tmp_path)
        mock_db_path.return_value = db_path

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.get_library_items(limit=10, include_details=False)
            assert result["success"] is True
            items = result["items"]
            assert len(items) == 2
            item = items[0]
            assert "title" in item
            assert "itemKey" in item
            assert "attachment_count" not in item
            assert "tag_count" not in item

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_get_library_items_with_details(self, mock_db_path, connector, tmp_path):
        """Test get_library_items includes counts when include_details=True"""
        db_path = self._create_test_database_for_library(tmp_path)
        mock_db_path.return_value = db_path

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.get_library_items(limit=10, include_details=True)
            assert result["success"] is True
            items = result["items"]
            assert len(items) == 2
            
            first_item = items[0]
            assert "attachment_count" in first_item
            assert first_item["attachment_count"] == 2
            assert "note_count" in first_item
            assert first_item["note_count"] == 2
            assert "tag_count" in first_item
            assert first_item["tag_count"] == 3
            assert "tags" in first_item
            assert len(first_item["tags"]) == 3


class TestPDFTextExtraction:
    """Test cases for PDF text extraction functionality"""

    @pytest.fixture
    def connector(self):
        """Create a ZoteroConnector instance"""
        return ZoteroConnector()

    def _create_sample_pdf(self, storage_path):
        """Create a minimal valid PDF file for testing"""
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n%%EOF'
        with open(storage_path, "wb") as f:
            f.write(pdf_content)

    def _create_test_database_with_attachment(self, tmp_path, storage_dir):
        """Create a test database with attachment for PDF extraction"""
        db_path = tmp_path / "test_pdf_extract.sqlite"
        storage_subdir = storage_dir / "ATTACH001"
        storage_subdir.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS items (
            itemID INTEGER PRIMARY KEY, key TEXT UNIQUE, itemTypeID INTEGER,
            itemType TEXT, dateAdded TEXT, dateModified TEXT, libraryID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemTypes (
            itemTypeID INTEGER PRIMARY KEY, typeName TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS attachments (
            itemID INTEGER PRIMARY KEY, parentItemID INTEGER,
            path TEXT, filename TEXT, contentType TEXT, storagePath TEXT
        )''')
        
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (1, 'journalArticle')")
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (2, 'attachment')")
        
        cursor.execute("INSERT INTO items (key, itemTypeID, itemType, libraryID, dateAdded, dateModified) VALUES (?, 1, 'journalArticle', 1, datetime('now'), datetime('now'))",
                       ("MAINITEM",))
        cursor.execute("INSERT INTO items (key, itemTypeID, itemType, libraryID, dateAdded, dateModified) VALUES (?, 2, 'attachment', 1, datetime('now'), datetime('now'))",
                       ("ATTACH001",))
        
        cursor.execute("INSERT INTO attachments (itemID, parentItemID, filename, contentType, path, storagePath) VALUES (?, 1, 'paper.pdf', 'application/pdf', 'storage/ATTACH001/paper.pdf', 'storage/ATTACH001')",
                       (2,))
        
        conn.commit()
        conn.close()
        return db_path

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_get_item_pdf_content_success(self, mock_db_path, connector, tmp_path):
        """Test get_item_pdf_content finds the attachment file"""
        storage_dir = tmp_path / "storage"
        db_path = self._create_test_database_with_attachment(tmp_path, storage_dir)
        mock_db_path.return_value = db_path
        connector._zotero_storage_dir = storage_dir
        
        storage_subdir = storage_dir / "ATTACH001"
        storage_subdir.mkdir(parents=True, exist_ok=True)
        
        # Create a minimal valid PDF
        pdf_content = b'''%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
208
%%EOF'''
        pdf_path = storage_subdir / "ATTACH001.pdf"
        pdf_path.write_bytes(pdf_content)

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.get_item_pdf_content("MAINITEM")
            assert result["success"] is True
            assert "pdf_path" in result
            assert result["pdf_path"] == str(pdf_path)

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_get_item_pdf_content_no_attachment(self, mock_db_path, connector, tmp_path):
        """Test get_item_pdf_content returns error when no attachment"""
        db_path = tmp_path / "no_attach.sqlite"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS items (
            itemID INTEGER PRIMARY KEY, key TEXT UNIQUE, itemTypeID INTEGER,
            itemType TEXT, dateAdded TEXT, libraryID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemTypes (itemTypeID INTEGER PRIMARY KEY, typeName TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS attachments (
            itemID INTEGER PRIMARY KEY, parentItemID INTEGER,
            path TEXT, filename TEXT, contentType TEXT
        )''')
        
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (1, 'journalArticle')")
        cursor.execute("INSERT INTO items (key, itemTypeID, itemType, libraryID, dateAdded) VALUES (?, 1, 'journalArticle', 1, datetime('now'))",
                       ("NOATTACH",))
        
        conn.commit()
        conn.close()
        mock_db_path.return_value = db_path

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.get_item_pdf_content("NOATTACH")
            assert result["success"] is False
            assert "No PDF attachment found" in result["error"]

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_get_item_pdf_content_file_not_found(self, mock_db_path, connector, tmp_path):
        """Test get_item_pdf_content returns error when PDF file missing"""
        storage_dir = tmp_path / "missing_storage"
        db_path = self._create_test_database_with_attachment(tmp_path, storage_dir)
        mock_db_path.return_value = db_path
        connector._zotero_storage_dir = storage_dir

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.get_item_pdf_content("MAINITEM")
            assert result["success"] is False
            assert "not found in storage" in result["error"]


class TestGetItemFullData:
    """Test cases for get_item_full_data method"""

    @pytest.fixture
    def connector(self):
        """Create a ZoteroConnector instance"""
        return ZoteroConnector()

    @patch('zotlink.zotero_integration.ZoteroConnector._get_zotero_db_path')
    def test_get_item_full_data_success(self, mock_db_path, connector, tmp_path):
        """Test get_item_full_data returns complete item data"""
        db_path = tmp_path / "full_data.sqlite"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS items (
            itemID INTEGER PRIMARY KEY, key TEXT UNIQUE, itemTypeID INTEGER,
            itemType TEXT, dateAdded TEXT, dateModified TEXT, libraryID INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemTypes (itemTypeID INTEGER PRIMARY KEY, typeName TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemData (itemID INTEGER, fieldID INTEGER, valueID INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS fields (fieldID INTEGER PRIMARY KEY, fieldName TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemDataValues (valueID INTEGER PRIMARY KEY, value TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS creators (creatorID INTEGER PRIMARY KEY, firstName TEXT, lastName TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemCreators (itemID INTEGER, creatorID INTEGER, creatorTypeID INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS creatorTypes (creatorTypeID INTEGER PRIMARY KEY, creatorType TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS attachments (
            itemID INTEGER PRIMARY KEY, parentItemID INTEGER,
            path TEXT, filename TEXT, contentType TEXT, storagePath TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS notes (itemID INTEGER PRIMARY KEY, parentItemID INTEGER, note TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS tags (tagID INTEGER PRIMARY KEY, name TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itemTags (itemID INTEGER, tagID INTEGER, type INTEGER)''')
        
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (1, 'journalArticle')")
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (2, 'attachment')")
        cursor.execute("INSERT INTO itemTypes (itemTypeID, typeName) VALUES (14, 'note')")
        cursor.execute("INSERT INTO creatorTypes (creatorTypeID, creatorType) VALUES (1, 'author')")
        cursor.execute("INSERT INTO fields (fieldID, fieldName) VALUES (1, 'title')")
        
        cursor.execute("INSERT INTO items (key, itemTypeID, itemType, libraryID, dateAdded, dateModified) VALUES (?, 1, 'journalArticle', 1, datetime('now'), datetime('now'))", ("FULLITEM",))
        cursor.execute("INSERT INTO items (key, itemTypeID, itemType, libraryID, dateAdded, dateModified) VALUES (?, 2, 'attachment', 1, datetime('now'), datetime('now'))", ("ATTACH001",))
        cursor.execute("INSERT INTO items (key, itemTypeID, itemType, libraryID, dateAdded, dateModified) VALUES (?, 14, 'note', 1, datetime('now'), datetime('now'))", ("NOTE001",))
        cursor.execute("INSERT INTO itemDataValues (valueID, value) VALUES (1, 'Full Test Title')")
        cursor.execute("INSERT INTO itemData (itemID, fieldID, valueID) VALUES (1, 1, 1)")
        cursor.execute("INSERT INTO creators (creatorID, firstName, lastName) VALUES (1, 'John', 'Doe')")
        cursor.execute("INSERT INTO itemCreators (itemID, creatorID, creatorTypeID) VALUES (1, 1, 1)")
        cursor.execute("INSERT INTO attachments (itemID, parentItemID, path, filename, contentType, storagePath) VALUES (?, 1, 'storage/test.pdf', 'test.pdf', 'application/pdf', 'storage')", (2,))
        cursor.execute("INSERT INTO notes (itemID, parentItemID, note) VALUES (?, 1, 'Test note')", (3,))
        cursor.execute("INSERT INTO tags (tagID, name) VALUES (1, 'test-tag')")
        cursor.execute("INSERT INTO itemTags (itemID, tagID, type) VALUES (1, 1, 0)")
        
        conn.commit()
        conn.close()
        mock_db_path.return_value = db_path

        with patch.object(connector, 'is_running', return_value=True):
            result = connector.get_item_full_data("FULLITEM", include_attachments=True)
            assert result["success"] is True
            item = result["item"]
            assert item["title"] == "Full Test Title"
            assert len(item["attachments"]) == 1
            assert len(item["notes"]) == 1
            assert len(item["tags"]) == 1
            assert "tags_detail" in item


class TestNewMCPTools:
    """Test cases for new MCP tools"""

    def test_get_item_pdf_text_tool_registered(self):
        """Test that get_item_pdf_text tool is registered"""
        from zotlink.zotero_mcp_server import handle_list_tools
        import asyncio
        tools = asyncio.run(handle_list_tools())
        tool_names = [t.name for t in tools]
        assert "get_item_pdf_text" in tool_names

    def test_get_item_pdf_text_tool_schema(self):
        """Test get_item_pdf_text tool has correct input schema"""
        from zotlink.zotero_mcp_server import handle_list_tools
        import asyncio
        tools = asyncio.run(handle_list_tools())
        for tool in tools:
            if tool.name == "get_item_pdf_text":
                schema = tool.inputSchema
                assert "item_key" in schema["required"]
                assert "properties" in schema
                assert schema["properties"]["item_key"]["type"] == "string"

    def test_get_library_items_include_details_param(self):
        """Test get_library_items tool accepts include_details parameter"""
        from zotlink.zotero_mcp_server import handle_list_tools
        import asyncio
        tools = asyncio.run(handle_list_tools())
        for tool in tools:
            if tool.name == "get_library_items":
                schema = tool.inputSchema
                assert "include_details" in schema["properties"]
                assert schema["properties"]["include_details"]["type"] == "boolean"

    def test_get_zotero_item_include_attachments_param(self):
        """Test get_zotero_item tool accepts include_attachments parameter"""
        from zotlink.zotero_mcp_server import handle_list_tools
        import asyncio
        tools = asyncio.run(handle_list_tools())
        for tool in tools:
            if tool.name == "get_zotero_item":
                schema = tool.inputSchema
                assert "include_attachments" in schema["properties"]
                assert schema["properties"]["include_attachments"]["type"] == "boolean"

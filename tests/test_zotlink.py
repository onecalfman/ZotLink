#!/usr/bin/env python3
"""
Test suite for ZotLink Zotero MCP Server

Tests Zotero API connectivity and functionality.
"""

import pytest
import sys
import os
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
    def connector(self):
        return ZoteroConnector()

    def test_split_comma_authors_single_author(self, connector):
        """Test splitting single author in Last, First format"""
        result = connector._split_comma_authors("Smith, John")
        assert result == ["Smith, John"]

    def test_split_comma_authors_two_authors(self, connector):
        """Test splitting two authors in First Last, First Last format"""
        result = connector._split_comma_authors("John Smith, Jane Doe")
        assert len(result) == 2

    def test_split_comma_authors_multiple(self, connector):
        """Test splitting multiple authors"""
        result = connector._split_comma_authors("John Smith, Jane Doe, Bob Chen")
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

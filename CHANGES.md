# ZotLink MCP Server - What's New

## Recent Updates

### 1. arXiv API Integration (NEW!)

We've added official arXiv API integration for fetching bibliographic metadata. This replaces the previous HTTP scraping approach with the official arXiv API, providing more reliable and complete metadata.

**New MCP Tool: `search_arxiv_api`**
```json
{
  "query": "ti:transformer au:hinton",
  "max_results": 5
}
```

**Features:**
- Full metadata extraction via official arXiv API
- Support for advanced search queries (ti:, au:, abs: prefixes)
- Automatic author parsing in standard format
- Subject classification and DOI extraction
- Published journal information when available

**Usage:**
```python
from zotlink.extractors.arxiv_extractor import search_arxiv, extract_arxiv_metadata

# Search arXiv
results = search_arxiv("neural networks", max_results=10)

# Extract metadata from a specific paper
metadata = extract_arxiv_metadata("https://arxiv.org/abs/1706.03762")
```

### 2. Edit Existing Zotero Entries (NEW!)

Added comprehensive tools for editing and managing existing Zotero items.

**New MCP Tools:**

| Tool | Description |
|------|-------------|
| `get_library_items` | Retrieve items from your Zotero library |
| `search_zotero_items` | Search for items by query |
| `get_zotero_item` | Get a specific item by key |
| `update_zotero_item` | Update item metadata (title, abstract, date, url) |
| `update_zotero_item_tags` | Update tags on an item |
| `delete_zotero_item` | Delete an item from your library |
| `move_zotero_item` | Move an item to a different collection |

### 3. Validate & Update Tool (NEW!)

Compare Zotero items with arXiv API data and optionally update with corrected metadata.

**New MCP Tools:**

| Tool | Description |
|------|-------------|
| `validate_zotero_item` | Validate item against arXiv, show differences |
| `validate_and_update_item` | Validate and apply arXiv corrections |
| `fetch_pdf` | Fetch PDF from arXiv, open access, Sci-Hub, Anna's Archive |

**Usage Examples:**

```json
// Validate item metadata
{
  "item_key": "ABC123"
}

// Validate and auto-update
{
  "item_key": "ABC123",
  "apply_updates": true
}

// Fetch PDF from preferred source
{
  "item_key": "ABC123",
  "source": "auto",  // or "arxiv", "open_access", "scihub", "annas_archive"
  "save_to_zotero": true
}
```

### 4. PDF Fetching from Multiple Sources

The new `fetch_pdf` tool can retrieve PDFs from:

1. **arXiv** - Direct PDF download for arXiv papers
2. **Open Access** - PubMed Central, DOAJ, Unpaywall, Semantic Scholar
3. **Sci-Hub** - Via DOI lookup (multiple mirrors)
4. **Anna's Archive** - Via DOI or title search

### 5. Metadata Validation & Sync

The `validate_zotero_item` tool compares Zotero metadata with arXiv records and reports differences in:
- Title
- Abstract
- Date
- Authors
- DOI

The `validate_and_update_item` tool can automatically apply corrections from arXiv to your Zotero library.

### 6. Chinese Comments Removed (CLEANUP)

All Chinese comments and messages have been replaced with English equivalents for better internationalization and code readability.

### 7. Test Suite Added (NEW!)

Comprehensive test suite for Zotero API queries and arXiv integration.

**Run Tests:**
```bash
cd /home/jonas/stuff/ZotLink
python -m pytest tests/ -v
```

**Test Coverage:**
- Zotero connection testing
- Collection retrieval
- Item operations (get, search, update, delete, move)
- arXiv API integration
- Metadata validation
- PDF fetching from all sources
- Author name parsing
- Integration tests (when Zotero is running)

### 8. Flatpak Configuration Helper

Added a configuration helper for users running Zotero via flatpak.

**Usage:**
```bash
python flatpak_config.py --help
```

**Options:**
- `--install`: Install systemd service for port forwarding
- `--create-script`: Create socat port forwarding script
- `--setup-env`: Create environment setup script

**Note for Flatpak Users:**
If you're running Zotero via flatpak, the Connector API (port 23119) may not be accessible from outside the sandbox. Options:

1. **Recommended**: Install Zotero natively
2. **Alternative**: Use flatpak with network socket access:
   ```bash
   flatpak run --socket=x11 --socket=network org.zotero.Zotero
   ```

## Installation

```bash
pip install -e .
```

## Configuration

Set Zotero paths via environment variables:
```bash
export ZOTLINK_ZOTERO_ROOT=~/.zotero-zotero  # Zotero data directory
```

Or via `~/.zotlink/config.json`:
```json
{
  "zotero": {
    "database_path": "~/.zotero-zotero/zotero.sqlite",
    "storage_dir": "~/.zotero-zotero/storage"
  }
}
```

## Running the Server

```bash
# Run as MCP server
python -m zotlink.zotero_mcp_server

# Or use the CLI
zotlink
```

## API Reference

### New MCP Tools

All new tools are available through the MCP protocol:

1. **search_arxiv_api** - Search arXiv using official API
2. **get_library_items** - List items in your library
3. **search_zotero_items** - Search library contents
4. **get_zotero_item** - Get item details
5. **update_zotero_item** - Modify item metadata
6. **update_zotero_item_tags** - Update item tags
7. **delete_zotero_item** - Remove item from library
8. **move_zotero_item** - Move item between collections
9. **validate_zotero_item** - Validate against arXiv, show differences
10. **validate_and_update_item** - Validate and apply corrections
11. **fetch_pdf** - Fetch PDF from multiple sources

### Python API

```python
from zotlink.zotero_integration import ZoteroConnector
from zotlink.extractors.arxiv_extractor import search_arxiv, extract_arxiv_metadata
from zotlink.pdf_fetcher import PDFFetcher

# Zotero operations
connector = ZoteroConnector()
connector.is_running()  # Check if Zotero is running
connector.get_collections()  # Get collections
connector.get_library_items(limit=50)  # Get items
connector.update_item("ABC123", {"title": "New Title"})  # Update item
connector.validate_item_with_arxiv("ABC123")  # Validate against arXiv
connector.validate_and_update_item("ABC123", apply_updates=True)  # Validate and update

# arXiv operations
results = search_arxiv("transformer architecture", max_results=5)
metadata = extract_arxiv_metadata("https://arxiv.org/abs/1706.03762")

# PDF fetching
fetcher = PDFFetcher(connector)
result = fetcher.fetch_pdf("ABC123", source="auto", save_to_zotero=True)
```

## Troubleshooting

### Zotero Not Running
Make sure Zotero desktop app is running and fully loaded. The MCP server requires the Zotero Connector API (port 23119) to be accessible.

### Flatpak Issues
If using flatpak Zotero and the API is not accessible:
1. Try running with `--socket=network` flag
2. Or install Zotero natively for best results
3. Use the `flatpak_config.py` helper script

### API Access Denied
The Zotero Connector API only accepts connections from localhost (127.0.0.1) for security.

## Development

### Running Tests
```bash
python -m pytest tests/ -v
```

### Adding New Extractors
Create a new extractor class inheriting from `BaseExtractor` and register it in `ExtractorManager`.

## License

MIT License

# ZotLink MCP Server Setup Guide

This guide provides comprehensive instructions for setting up ZotLink MCP server with Claude Code and Open Code.

## Overview

ZotLink is an MCP (Model Context Protocol) server that enables AI assistants to interact with your Zotero library. It supports:

- Saving papers from arXiv, bioRxiv, medRxiv, chemRxiv, and CVF
- Automatic PDF download and metadata extraction
- Collection management
- Database authentication for paywalled sources (Nature, Science, IEEE, etc.)

## Prerequisites

### System Requirements

- **Python**: 3.10 or higher
- **Zotero**: Version 6.0 or higher (desktop application must be running)
- **Operating Systems**: macOS, Windows, Linux

### Required Software

1. **uv** - Fast Python package manager (installs ZotLink automatically)
2. **Zotero Desktop**: [Download from zotero.org](https://www.zotero.org/download/)

**Optional (for browser-based extraction):**
- Playwright with Chromium (some databases require browser automation)

---

## Installation

### Step 1: Install uv (Recommended)

uv is a fast Python package manager that handles dependencies efficiently.

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

### Step 2: Install ZotLink

**Using uvx (Recommended - runs directly from GitHub):**
```bash
uvx --from github.com/onecalfman/zotlink zotlink --help
```

**Using uv pip (local installation):**
```bash
uv pip install zotlink
```

**Using pip:**
```bash
pip install zotlink
```

### Step 3: Playwright (Optional)

For browser-based extraction on some databases:

```bash
python -m playwright install chromium
```

**Linux Additional Dependencies:**
```bash
sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 libasound2
```

### Step 4: Quick Start

```bash
# Run ZotLink directly from GitHub (no installation needed)
uvx --from github.com/onecalfman/zotlink zotlink --help
```

That's it! ZotLink will auto-detect your Zotero path or you can set it via environment variable.

---

## Zotero Configuration

### Finding Your Zotero Data Directory

**macOS:**
```
~/Zotero
```

**Windows:**
```
%APPDATA%\Zotero
```
or
```
C:\Users\YourName\Zotero
```

**Linux:**
```
~/Zotero
```

### Verify Zotero Paths

Your Zotero directory must contain:
- `zotero.sqlite` - The main database file
- `storage/` - Directory for attachments

### Auto-Detect Zotero Path

Run the initialization command to auto-detect your Zotero path:

```bash
zotlink init
```

This will:
1. Search common locations for your Zotero data
2. Validate the installation
3. Generate MCP configuration

---

## Claude Code Setup (claude.ai/code)

### Method 1: Using the MCP Server UI

1. Open Claude Code (claude.ai/code)
2. Navigate to **Settings** → **MCP Servers**
3. Click **Add MCP Server**
4. Fill in the configuration:

```
Server Name: zotlink
Command: zotlink
Arguments: (leave empty)
Environment Variables:
  - ZOTLINK_ZOTERO_ROOT=/path/to/your/Zotero
```

5. Click **Save**

### Method 2: Manual Configuration

Claude Code stores MCP configurations in a JSON file. The location varies:

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

#### Configuration Format

```json
{
  "mcpServers": {
    "zotlink": {
      "command": "zotlink",
      "args": [],
      "env": {
        "ZOTLINK_ZOTERO_ROOT": "/Users/yourname/Zotero"
      }
    }
  }
}
```

#### Advanced Configuration

```json
{
  "mcpServers": {
    "zotlink": {
      "command": "zotlink",
      "args": [],
      "env": {
        "ZOTLINK_ZOTERO_ROOT": "/Users/yourname/Zotero",
        "ZOTLINK_ZOTERO_DB": "/Users/yourname/Zotero/zotero.sqlite",
        "ZOTLINK_ZOTERO_DIR": "/Users/yourname/Zotero/storage"
      }
    }
  }
}
```

### Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ZOTLINK_ZOTERO_ROOT` | Path to Zotero data directory | Yes (or use ZOTLINK_ZOTERO_DB) |
| `ZOTLINK_ZOTERO_DB` | Path to zotero.sqlite file | Alternative to ZOTLINK_ZOTERO_ROOT |
| `ZOTLINK_ZOTERO_DIR` | Path to storage directory | Optional |

### Verification

1. Restart Claude Code
2. Start a new conversation
3. Ask: "Check Zotero status"
4. You should see a response indicating connection status

---

## Open Code Setup (opencode.ai)

### Method 1: Using Open Code Settings

1. Open Open Code (opencode.ai)
2. Go to **Settings** → **MCP Configuration**
3. Add a new MCP server with:

```
Name: zotlink
Command: zotlink
Type: stdio
Environment Variables:
  ZOTLINK_ZOTERO_ROOT=/path/to/your/Zotero
```

4. Save the configuration
5. Restart Open Code

### Method 2: Configuration File

Open Code may use a configuration file at:

**macOS:**
```
~/.config/opencode/mcp_config.json
```

**Linux:**
```
~/.config/opencode/mcp_config.json
```

**Windows:**
```
%APPDATA%\OpenCode\mcp_config.json
```

#### Configuration Format

```json
{
  "mcpServers": {
    "zotlink": {
      "command": "zotlink",
      "args": [],
      "type": "stdio",
      "env": {
        "ZOTLINK_ZOTERO_ROOT": "/Users/yourname/Zotero"
      }
    }
  }
}
```

### Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ZOTLINK_ZOTERO_ROOT` | Path to Zotero data directory | Yes |
| `ZOTLINK_ZOTERO_DB` | Path to zotero.sqlite file | Optional |
| `ZOTLINK_ZOTERO_DIR` | Path to storage directory | Optional |

### Verification

1. Restart Open Code
2. Start a new session
3. Run the `check_zotero_status` tool
4. Verify the connection is successful

---

## Configuration Options

### Priority Order

Configuration is read in this order (later overrides earlier):

1. **Auto-detection** - Searches common Zotero locations
2. **Local config file** - `~/.zotlink/config.json`
3. **MCP env config** - Environment variables in MCP configuration
4. **System environment variables** - `ZOTLINK_ZOTERO_ROOT`, etc.

### Local Config File

Create `~/.zotlink/config.json`:

```json
{
  "zotero": {
    "database_path": "/Users/yourname/Zotero/zotero.sqlite",
    "storage_dir": "/Users/yourname/Zotero/storage"
  },
  "logging": {
    "level": "INFO",
    "file": "~/.zotlink/zotlink.log"
  },
  "browser": {
    "enabled": true,
    "timeout": 30
  }
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ZOTLINK_ZOTERO_ROOT` | Zotero data directory | Auto-detected |
| `ZOTLINK_ZOTERO_DB` | SQLite database path | `{ZOTLINK_ZOTERO_ROOT}/zotero.sqlite` |
| `ZOTLINK_ZOTERO_DIR` | Storage directory | `{ZOTLINK_ZOTERO_ROOT}/storage` |
| `ZOTLINK_LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO |
| `ZOTLINK_BROWSER_MODE` | Enable browser extraction (true/false) | true |

---

## Available Tools

Once configured, ZotLink provides these tools:

### Core Tools

| Tool | Description |
|------|-------------|
| `check_zotero_status` | Check Zotero connection and version |
| `get_zotero_collections` | List all collections in your library |
| `save_paper_to_zotero` | Save a paper by URL (arXiv, bioRxiv, etc.) |
| `get_library_items` | Get items from your library |
| `search_zotero_items` | Search your library |
| `get_zotero_item` | Get a specific item by key |
| `update_zotero_item` | Update item metadata |
| `delete_zotero_item` | Delete an item |
| `move_zotero_item` | Move item to collection |

### ArXiv Tools

| Tool | Description |
|------|-------------|
| `extract_arxiv_metadata` | Extract metadata from arXiv URL |
| `search_arxiv_api` | Search arXiv using the official API |
| `validate_zotero_item` | Validate item against arXiv data |
| `validate_and_update_item` | Validate and auto-update from arXiv |

### PDF Tools

| Tool | Description |
|------|-------------|
| `fetch_pdf` | Fetch PDF for a Zotero item |

### Authentication Tools

| Tool | Description |
|------|-------------|
| `get_supported_databases` | List supported databases |
| `set_database_cookies` | Set cookies for a database |
| `test_database_access` | Test database access |
| `get_cookie_guide` | Get cookie setup guide |
| `get_cookie_sync_status` | Check sync service status |
| `get_database_auth_status` | Check all database auth status |
| `generate_bookmark_code` | Generate bookmark for cookie sync |

### Collection Tools

| Tool | Description |
|------|-------------|
| `create_zotero_collection` | Create a new collection (manual) |

---

## Usage Examples

### Saving an arXiv Paper

```
Use the save_paper_to_zotero tool with:
- paper_url: "https://arxiv.org/abs/2301.12345"
- collection_key: (optional, get from get_zotero_collections)
```

### Listing Collections

```
Call get_zotero_collections to see your library structure.
Each collection shows its key for use in save_paper_to_zotero.
```

### Searching arXiv

```
Use search_arxiv_api with:
- query: "ti:transformer OR au:hinton"
- max_results: 10
```

### Fetching a PDF

```
Use fetch_pdf with:
- item_key: "ABC123"
- source: "auto" (or specific: arxiv, open_access, scihub, annas_archive)
- save_to_zotero: true
```

---

## Troubleshooting

### Zotero Not Running

**Error**: "Zotero不可用，请启动Zotero桌面应用"

**Solution**:
1. Start Zotero desktop application
2. Wait for it to fully load
3. Restart the MCP server
4. Verify Zotero is running on port 23119

```bash
# Test if Zotero is responding
curl http://127.0.0.1:23119
```

### Zotero Path Not Found

**Error**: "未找到 zotero.sqlite 文件"

**Solution**:
1. Verify your Zotero data directory location
2. Run `zotlink init /path/to/your/Zotero` to generate config
3. Ensure the path contains `zotero.sqlite`

### Playwright/Chromium Not Installed

**Error**: Browser-related failures

**Solution**:
```bash
python -m playwright install chromium
```

### PDF Download Failed

**Error**: PDF not attached or download error

**Solutions**:
1. Some sources only provide link attachments, not PDFs
2. Check network connectivity
3. Try the `fetch_pdf` tool for manual download
4. Some publishers may block automated downloads

### Browser Mode Issues (Linux)

**Error**: Chromium sandbox errors

**Solution**:
```bash
# Install required system libraries
sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 libasound2

# Or disable sandbox (less secure)
export PLAYWRIGHT_CHROMIUM_SANDBOX=0
```

### Logging

Logs are written to `~/.zotlink/zotlink.log`. Check this file for detailed error information.

```bash
# View recent logs
tail -f ~/.zotlink/zotlink.log

# View errors only
grep -i error ~/.zotlink/zotlink.log
```

### Reset Configuration

To reset ZotLink configuration:

```bash
# Remove local config
rm -rf ~/.zotlink/

# Re-initialize
zotlink init /path/to/Zotero
```

### Verbose Debugging

Enable debug logging:

**In MCP config env:**
```json
{
  "env": {
    "ZOTLINK_LOG_LEVEL": "DEBUG",
    "ZOTLINK_ZOTERO_ROOT": "/path/to/Zotero"
  }
}
```

**Or in shell:**
```bash
export ZOTLINK_LOG_LEVEL=DEBUG
```

---

## Supported Sources

### Open Access (No Authentication Required)

| Source | URL Pattern | PDF Available |
|--------|-------------|---------------|
| arXiv | arxiv.org/abs/... | Yes |
| bioRxiv | biorxiv.org/content/... | Yes |
| medRxiv | medrxiv.org/content/... | Yes |
| chemRxiv | chemrxiv.org/... | Yes |
| CVF | cvpr.thecvf.com/... | Yes |

### Authentication Required

| Source | Cookie Required | Notes |
|--------|-----------------|-------|
| Nature | Yes | Academic access or subscription |
| Science | Yes | Institutional access |
| IEEE Xplore | Yes | Subscription required |
| Springer | Yes | Institutional access |
| ACM DL | Yes | Subscription required |

### Setting Authentication

For paywalled sources, set cookies:

```python
# Using the tool
set_database_cookies(
    database_name="Nature",
    cookies="session=abc123; ..."
)
```

See `get_cookie_guide` for detailed instructions.

---

## Development Setup

### From GitHub (Recommended)

```bash
# Run directly from GitHub
uvx --from github.com/onecalfman/zotlink zotlink --help
```

### From Source

```bash
git clone https://github.com/onecalfman/zotlink.git
cd zotlink
uv pip install -e .
python -m playwright install chromium
```

### Running Tests

```bash
pytest tests/ -v
```

---

## File Locations

| Path | Description |
|------|-------------|
| `~/.zotlink/config.json` | Local configuration |
| `~/.zotlink/zotlink.log` | Application log |
| `~/Zotero/zotero.sqlite` | Zotero database |
| `~/Zotero/storage/` | Zotero attachments |

---

## Getting Help

- **GitHub Issues**: https://github.com/onecalfman/zotlink/issues
- **Documentation**: See README.md and docs/DEVELOPMENT.md
- **MCP Protocol**: https://modelcontextprotocol.io/

---

## Quick Reference

### One-Line Setup

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run ZotLink directly from GitHub
uvx --from github.com/onecalfman/zotlink zotlink --help
```

### Claude Code Config

```json
{
  "mcpServers": {
    "zotlink": {
      "command": "uvx",
      "args": ["--from", "github.com/onecalfman/zotlink", "zotlink"],
      "env": {
        "ZOTLINK_ZOTERO_ROOT": "~/Zotero"
      }
    }
  }
}
```

### Open Code Config

```json
{
  "mcpServers": {
    "zotlink": {
      "command": "uvx",
      "args": ["--from", "github.com/onecalfman/zotlink", "zotlink"],
      "type": "stdio",
      "env": {
        "ZOTLINK_ZOTERO_ROOT": "~/Zotero"
      }
    }
  }
}
```

### First Use

1. Ensure Zotero is running
2. Start Claude Code or Open Code
3. Run: `check_zotero_status`
4. Run: `get_zotero_collections`
5. Save your first paper: `save_paper_to_zotero(paper_url="https://arxiv.org/abs/2301.12345")`

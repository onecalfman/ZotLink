<div align="center">

<img src="https://pic-1313147768.cos.ap-chengdu.myqcloud.com/ZotLink/logo.png" alt="ZotLink Logo" width="150" height="150">

# ZotLink

MCP Server for Zotero Connector

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**🌍 Language / 语言选择:**
[🇺🇸 English](README.md) | [🇨🇳 中文](README_zh.md)

</div>

## ✨ Features

- 🌐 **Open Sources**: arXiv, CVF (OpenAccess), bioRxiv, medRxiv, chemRxiv
- 🧠 **Rich Metadata**: title, authors, abstract, DOI, subjects
- 📄 **Smart PDF Attachment**: auto-attach or validated link fallback
- 📚 **One-Click Save**: list collections + save to any folder
- 💻 **Works with**: Claude Desktop, Cherry Studio, opencode.ai

---

## 🚀 Quick Start

### Install

```bash
# Using pip
pip install zotlink
python -m playwright install chromium

# Or using uvx (recommended)
uvx --from git+https://github.com/onecalfman/zotlink zotlink
```

*Requires Python 3.10+*

### Configure

Auto-generate MCP config:

```bash
zotlink init /path/to/Zotero
```

Or manually configure for **opencode.ai**:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "zotlink": {
      "enabled": true,
      "command": [
        "uvx",
        "--from",
        "git+https://github.com/onecalfman/zotlink",
        "zotlink"
      ],
      "type": "local",
      "environment": {
        "ZOTLINK_ZOTERO_ROOT": "/path/to/Zotero"
      }
    }
  }
}
```

For **Claude Desktop**, add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "zotlink": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/onecalfman/zotlink", "zotlink"],
      "env": {
        "ZOTLINK_ZOTERO_ROOT": "/Users/yourname/Zotero"
      }
    }
  }
}
```

Restart your app and you're ready!

---

## 🛠️ Development

```bash
git clone https://github.com/onecalfman/zotlink.git
cd ZotLink
pip install -e .
python -m playwright install chromium
zotlink
```

## 🧰 Tools

- `check_zotero_status` - Check Zotero connection
- `get_zotero_collections` - List all collections
- `save_paper_to_zotero` - Save paper by URL (arXiv/CVF/rxiv)
- `extract_arxiv_metadata` - Extract arXiv metadata
- Cookie helpers for auth-required sources

## 🌐 Browser Mode

Included by default for bioRxiv, medRxiv, chemRxiv. Falls back to HTTP on Windows.

**Linux dependencies**:
```bash
sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 libasound2
```

## 🔧 Environment Variables

```bash
# Recommended: single directory
export ZOTLINK_ZOTERO_ROOT=/path/to/Zotero

# Advanced: separate paths
export ZOTLINK_ZOTERO_DB=/path/to/Zotero/zotero.sqlite
export ZOTLINK_ZOTERO_DIR=/path/to/Zotero/storage
```

## 🧪 Troubleshooting

- **Zotero not detected**: Ensure Zotero Desktop is running (port 23119)
- **No PDF attached**: Some pages only expose links; server falls back to link attachments
- **Browser errors**: Verify Playwright is installed and Chromium is available

## 📄 License

MIT

---

<div align="center">
Made with ❤️ for the Zotero community
</div>

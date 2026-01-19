#!/usr/bin/env python3
"""
ZotLink - Academic Literature Management MCP Tool

Smart academic literature management based on Zotero Connector API
Full academic literature management with support for:
- arXiv paper auto-processing (metadata + PDF)
- Smart collection management (updateSession mechanism)
- Open access journal support
- Fully automated PDF downloads
- Complete metadata extraction (Comment, DOI, subjects, etc.)

Technical features:
- No cookies or login required
- Based on Zotero Connector official API
- Supports treeViewID and updateSession mechanisms
- 100% open source, easy to maintain
"""

import asyncio
import logging
import json
import sys
from typing import Any, Optional
from pathlib import Path

# MCP imports
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp import ClientSession
from mcp.server.stdio import stdio_server

# Local imports
from .zotero_integration import ZoteroConnector
from .cookie_sync import CookieSyncManager

# Configure logging - write to user directory to avoid read-only install paths
log_dir = Path.home() / '.zotlink'
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / 'zotlink.log'

# Windows console common GBK encoding issues: only write to file to avoid emoji encoding errors
handlers = [logging.FileHandler(log_file, encoding='utf-8')]
if sys.platform != 'win32':
    handlers.append(logging.StreamHandler(sys.stderr))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger(__name__)

# Global Zotero connector
zotero_connector = ZoteroConnector()

# Auto-load available cookies from files
logger.info("Loading shared cookies...")
cookie_results = zotero_connector.load_cookies_from_files()
if cookie_results:
    success_count = sum(1 for v in cookie_results.values() if v)
    total_count = len(cookie_results)
    logger.info(f"Cookie loading complete: {success_count}/{total_count} databases")
else:
    logger.info("No shared cookies available")

# Initialize cookie sync manager
cookie_sync_manager = CookieSyncManager(zotero_connector=zotero_connector)

# Sync loaded cookies to CookieSyncManager
logger.info("Syncing loaded cookies status...")
if zotero_connector.extractor_manager and zotero_connector.extractor_manager.cookies_store:
    for db_name, cookies in zotero_connector.extractor_manager.cookies_store.items():
        if cookies and cookies.strip():
            cookie_sync_manager.database_registry.update_cookie_status(db_name, cookies)
            logger.info(f"Synced {db_name} cookies status to auth manager")

cookie_sync_manager.start()

# Create MCP server
server = Server("zotlink")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available Zotero tools"""
    return [
        types.Tool(
            name="check_zotero_status",
            description="Check connection status and version info for Zotero desktop app",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_zotero_collections",
            description="Get all collections/folders from your Zotero library (tree structure)",
            inputSchema={
                "type": "object", 
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="save_paper_to_zotero",
            description="Save a paper to Zotero from a URL (arXiv, DOI, etc.). Automatically fetches metadata and PDF",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_url": {
                        "type": "string",
                        "description": "Paper URL (supports arXiv, DOI links, etc.)"
                    },
                    "paper_title": {
                        "type": "string", 
                        "description": "Paper title (optional, will be auto-extracted)"
                    },
                    "collection_key": {
                        "type": "string",
                        "description": "Target collection key (optional, saves to default location)"
                    }
                },
                "required": ["paper_url"]
            }
        ),
        types.Tool(
            name="save_paper_by_doi",
            description="Save a paper to Zotero by DOI. Supports arXiv DOIs (10.48550/arXiv.XXX) and published DOIs",
            inputSchema={
                "type": "object",
                "properties": {
                    "doi": {
                        "type": "string",
                        "description": "DOI string (e.g., '10.48550/arXiv.2301.00001' or '10.1038/s41586-023-03758-y')"
                    },
                    "collection_key": {
                        "type": "string",
                        "description": "Target collection key (optional, saves to default location)"
                    }
                },
                "required": ["doi"]
            }
        ),
        types.Tool(
            name="create_zotero_collection",
            description="Create a new collection/folder in Zotero for organizing papers",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Collection name"
                    },
                    "parent_key": {
                        "type": "string",
                        "description": "Parent collection key (optional, for nested collections)"
                    }
                },
                "required": ["name"]
            }
        ),
        types.Tool(
            name="extract_arxiv_metadata",
            description="Extract complete metadata from an arXiv URL (title, authors, abstract, subjects, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "arxiv_url": {
                        "type": "string",
                        "description": "arXiv URL (abs or pdf page)"
                    }
                },
                "required": ["arxiv_url"]
            }
        ),
        types.Tool(
            name="get_library_items",
            description="Get items from your Zotero library with pagination support. Optionally includes attachments, notes, and tags.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of items to return (default: 50)"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset for pagination (default: 0)"
                    },
                    "include_details": {
                        "type": "boolean",
                        "description": "Include attachment count, note count, and tags for each item (default: false)"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="search_zotero_items",
            description="Search for items in your Zotero library by keyword or phrase",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string"
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_zotero_item",
            description="Get detailed information about a specific Zotero item by its key. Optionally includes attachments, notes, and tags.",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_key": {
                        "type": "string",
                        "description": "The Zotero item key"
                    },
                    "include_attachments": {
                        "type": "boolean",
                        "description": "Include attachments, notes, and tags in response (default: true)"
                    }
                },
                "required": ["item_key"]
            }
        ),
        types.Tool(
            name="update_zotero_item",
            description="Update an existing Zotero item's metadata (title, abstract, date, URL, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_key": {
                        "type": "string",
                        "description": "The Zotero item key to update"
                    },
                    "title": {
                        "type": "string",
                        "description": "New title (optional)"
                    },
                    "abstract": {
                        "type": "string",
                        "description": "New abstract note (optional)"
                    },
                    "date": {
                        "type": "string",
                        "description": "New date (optional)"
                    },
                    "url": {
                        "type": "string",
                        "description": "New URL (optional)"
                    }
                },
                "required": ["item_key"]
            }
        ),
        types.Tool(
            name="update_zotero_item_tags",
            description="Update or replace tags on an existing Zotero item",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_key": {
                        "type": "string",
                        "description": "The Zotero item key"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tag strings to set"
                    }
                },
                "required": ["item_key", "tags"]
            }
        ),
        types.Tool(
            name="delete_zotero_item",
            description="Delete an item from your Zotero library",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_key": {
                        "type": "string",
                        "description": "The Zotero item key to delete"
                    }
                },
                "required": ["item_key"]
            }
        ),
        types.Tool(
            name="move_zotero_item",
            description="Move a Zotero item to a different collection",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_key": {
                        "type": "string",
                        "description": "The Zotero item key"
                    },
                    "collection_key": {
                        "type": "string",
                        "description": "The target collection key"
                    }
                },
                "required": ["item_key", "collection_key"]
            }
        ),
        types.Tool(
            name="search_arxiv_api",
            description="Search arXiv using the official API. Use prefixes: ti: (title), au: (author), abs: (abstract)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'ti:transformer', 'au:hinton', 'abs:neural networks')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return (default: 5, max: 50)"
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="validate_zotero_item",
            description="Validate a Zotero item against arXiv metadata. Shows differences between Zotero entry and arXiv data",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_key": {
                        "type": "string",
                        "description": "The Zotero item key to validate"
                    }
                },
                "required": ["item_key"]
            }
        ),
        types.Tool(
            name="validate_and_update_item",
            description="Validate a Zotero item against arXiv and optionally update it with corrected metadata",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_key": {
                        "type": "string",
                        "description": "The Zotero item key"
                    },
                    "apply_updates": {
                        "type": "boolean",
                        "description": "If True, automatically update Zotero with arXiv data where differences exist (default: False)"
                    }
                },
                "required": ["item_key"]
            }
        ),
        types.Tool(
            name="fetch_pdf",
            description="Fetch PDF for a Zotero item from open access sources (arXiv, PubMed, DOAJ, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_key": {
                        "type": "string",
                        "description": "The Zotero item key to fetch PDF for"
                    },
                    "source": {
                        "type": "string",
                        "enum": ["auto", "arxiv", "open_access", "scihub", "annas_archive"],
                        "description": "Preferred source: auto (try all), arxiv, open_access, scihub, annas_archive"
                    },
                    "save_to_zotero": {
                        "type": "boolean",
                        "description": "If True, save the fetched PDF as an attachment to the Zotero item (default: True)"
                    }
                },
                "required": ["item_key"]
            }
        ),
        types.Tool(
            name="get_item_pdf_text",
            description="Extract text from an attached PDF in Zotero for full-text search and analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_key": {
                        "type": "string",
                        "description": "The Zotero item key to extract PDF text from"
                    }
                },
                "required": ["item_key"]
            }
        )
    ]

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """List available resources"""
    return [
        types.Resource(
            uri="zotero://status",
            name="Zotero Connection Status",
            description="Current Zotero desktop app connection status",
            mimeType="application/json"
        ),
        types.Resource(
            uri="zotero://collections",
            name="Zotero Collection List", 
            description="All collections in your Zotero library",
            mimeType="application/json"
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls"""
    
    if name == "check_zotero_status":
        try:
            is_running = zotero_connector.is_running()
            version = zotero_connector.get_version()
            
            if is_running:
                collections_count = len(zotero_connector.get_collections())
                
                message = "Zotero Connection Successful!\n\n"
                message += f"App Status: Zotero desktop is running\n"
                message += f"Version Info: {version}\n"
                message += f"Collection Count: {collections_count}\n"
                message += f"API Endpoint: http://127.0.0.1:23119\n\n"
                message += f"Available Tools:\n"
                message += f"  save_paper_to_zotero - Save academic papers\n"
                message += f"  get_zotero_collections - View collections\n"
                message += f"  extract_arxiv_metadata - Extract arXiv metadata\n"
                message += f"  create_zotero_collection - Create new collection\n"
                message += f"  search_arxiv_api - Search arXiv\n"
                message += f"  And more...\n\n"
                message += f"Getting Started: View your collections and save academic papers!"
            else:
                message = "Zotero Not Running\n\n"
                message += f"Solutions:\n"
                message += f"1. Start Zotero desktop application\n"
                message += f"2. Ensure Zotero is fully loaded\n"
                message += f"3. Run this check again\n\n"
                message += f"Requirements: Zotero 6.0 or newer"
            
            return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to check Zotero status: {e}")
            return [types.TextContent(type="text", text=f"Error checking Zotero status: {e}")]
    
    elif name == "get_zotero_collections":
        try:
            if not zotero_connector.is_running():
                return [types.TextContent(type="text", text="Zotero unavailable. Please start Zotero desktop app")]
            
            collections = zotero_connector.get_collections()
            
            if not collections:
                message = "Collection Management\n\n"
                message += "No collections found\n\n"
                message += "Suggestions:\n"
                message += "  Use create_zotero_collection to create a new collection\n"
                message += "  Or manually create collections in Zotero desktop app"
                return [types.TextContent(type="text", text=message)]
            
            message = f"Zotero Collection List ({len(collections)} total)\n\n"
            
            root_collections = [c for c in collections if not c.get('parentCollection')]
            child_collections = [c for c in collections if c.get('parentCollection')]
            
            def format_collection(coll, level=0):
                indent = "  " * level
                name = coll.get('name', 'Unknown Collection')
                key = coll.get('key', 'no key')
                
                formatted = f"{indent}  {name}\n"
                formatted += f"{indent}    Key: {key}\n"
                
                children = [c for c in child_collections if c.get('parentCollection') == coll.get('id')]
                for child in children:
                    formatted += format_collection(child, level + 1)
                
                return formatted
            
            for root_coll in root_collections:
                message += format_collection(root_coll)
            
            message += f"\nUsage:\n"
            message += f"  Copy the collection Key value\n"
            message += f"  Specify collection_key in save_paper_to_zotero\n"
            message += f"  Papers will be automatically saved to the specified collection"
            
            return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to get collections: {e}")
            return [types.TextContent(type="text", text=f"Failed to get collections: {e}")]
    
    elif name == "save_paper_to_zotero":
        paper_url = arguments.get("paper_url")
        paper_title = arguments.get("paper_title", "")
        collection_key = arguments.get("collection_key")
        
        if not paper_url:
            return [types.TextContent(type="text", text="Missing paper URL")]
        
        if not zotero_connector.is_running():
            return [types.TextContent(type="text", text="Zotero unavailable. Please start Zotero desktop app")]
        
        try:
            paper_info = {
                "title": paper_title,
                "url": paper_url
            }
            
            if 'arxiv.org' in paper_url:
                logger.info("Processing arXiv paper")
            
            result = zotero_connector.save_item_to_zotero(paper_info, collection_key=collection_key)
            
            if result["success"]:
                message = f"Paper saved successfully!\n\n"
                
                database = result.get("database", "Unknown")
                enhanced = result.get("enhanced", False)
                
                message += f"Source: {database}\n"
                message += f"Metadata enhanced: {'Yes' if enhanced else 'No'}\n"
                
                import re
                
                if 'arxiv.org' in paper_url:
                    arxiv_match = re.search(r'arxiv\.org/(abs|pdf)/([^/?]+)', paper_url)
                    if arxiv_match:
                        arxiv_id = arxiv_match.group(2)
                        message += f"Type: arXiv preprint\n"
                        message += f"arXiv ID: {arxiv_id}\n"
                        actual_title = result.get('title') or paper_title or f'arXiv:{arxiv_id} (extracting...)'
                        message += f"Title: {actual_title}\n"
                        message += f"Link: {paper_url}\n"
                        message += f"PDF: https://arxiv.org/pdf/{arxiv_id}.pdf\n"
                
                elif 'biorxiv.org' in paper_url.lower():
                    message = message.replace(f"Source: {database}\n", "Source: bioRxiv\n")
                    message += f"Type: bioRxiv preprint\n"
                    actual_title = result.get('title') or paper_title or 'extracting...'
                    message += f"Title: {actual_title}\n"
                    message += f"Link: {paper_url}\n"
                    
                elif 'medrxiv.org' in paper_url.lower():
                    message = message.replace(f"Source: {database}\n", "Source: medRxiv\n")
                    message += f"Type: medRxiv preprint\n"
                    actual_title = result.get('title') or paper_title or 'extracting...'
                    message += f"Title: {actual_title}\n"
                    message += f"Link: {paper_url}\n"
                    
                elif 'chemrxiv.org' in paper_url.lower():
                    message = message.replace(f"Source: {database}\n", "Source: ChemRxiv\n")
                    message += f"Type: ChemRxiv preprint\n"
                    actual_title = result.get('title') or paper_title or 'extracting...'
                    message += f"Title: {actual_title}\n"
                    message += f"Link: {paper_url}\n"
                    
                elif database and database != 'arXiv':
                    message += f"Type: {database} journal article\n"
                    actual_title = result.get('title') or paper_title or 'extracting...'
                    message += f"Title: {actual_title}\n"
                    message += f"Link: {paper_url}\n"
                else:
                    actual_title = result.get('title') or paper_title or 'extracting...'
                    message += f"Title: {actual_title}\n"
                    message += f"URL: {paper_url}\n"
                
                if collection_key:
                    collection_moved = result.get("details", {}).get("collection_moved", False)
                    if collection_moved:
                        message += f"Collection: Moved to specified collection\n"
                        message += f"Method: Using updateSession official mechanism\n"
                    else:
                        message += f"Collection: Move failed, item in default location\n"
                        message += f"Manual: Please drag item to target collection in Zotero\n"
                else:
                    message += f"Saved to: My Library (default)\n"
                
                details = result.get("details", {})
                pdf_downloaded = details.get("pdf_downloaded", False)
                pdf_error = details.get("pdf_error")
                pdf_method = details.get("pdf_method", "link_attachment")
                
                if pdf_downloaded and pdf_method == "attachment":
                    message += f"PDF: Downloaded and saved as attachment\n"
                elif pdf_method == "failed":
                    if "biorxiv.org" in paper_url.lower():
                        message += f"PDF: Advanced download attempt failed\n"
                        message += f"  Possible: Network delay, server load, or anti-bot detection\n"
                        message += f"  Suggestion: Try again later or use browser Zotero connector\n"
                    else:
                        message += f"PDF: Save failed (network or server issue)\n"
                        message += f"  Metadata saved, add PDF manually later\n"
                elif pdf_method == "none":
                    message += f"PDF: No PDF link found\n"
                else:
                    message += f"PDF: Processing exception\n"
                
                if result.get("extra_preserved"):
                    message += f"Metadata: Fully extracted (Comment, subjects, DOI, etc.)\n"
                
                message += f"\nVerification:\n"
                if details.get("collection_moved"):
                    message += f"Success! Paper is in the specified collection\n"
                    message += f"1. Open Zotero desktop app\n"
                    message += f"2. Check the specified collection for the new item\n"
                    message += f"3. Verify PDF attachment and metadata completeness\n"
                elif collection_key:
                    message += f"Paper saved, collection move may need confirmation\n"
                    message += f"1. Open Zotero desktop app\n"
                    message += f"2. Check the specified collection first\n"
                    message += f"3. If not found, check 'My Library' and move manually\n"
                else:
                    message += f"Paper saved to default location\n"
                    message += f"1. Open Zotero desktop app\n"
                    message += f"2. Find in 'My Library'\n"
                    message += f"3. Move to collection if needed\n"
                
                message += f"\nDone! Enjoy your academic literature management!"
                
            else:
                message = f"Save failed: {result.get('message', 'Unknown error')}\n\n"
                message += f"Troubleshooting:\n"
                message += f"  Ensure Zotero desktop app is running\n"
                message += f"  Check network connection\n"
                message += f"  Verify paper URL is valid\n"
                message += f"  Try restarting Zotero app"
            
            return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to save paper: {e}")
            return [types.TextContent(type="text", text=f"Error saving paper: {e}")]
    
    elif name == "save_paper_by_doi":
        doi = arguments.get("doi", "").strip()
        collection_key = arguments.get("collection_key")
        
        if not doi:
            return [types.TextContent(type="text", text="Missing DOI")]
        
        if not zotero_connector.is_running():
            return [types.TextContent(type="text", text="Zotero unavailable. Please start Zotero desktop app")]
        
        try:
            logger.info(f"Processing DOI: {doi}")
            
            paper_info = zotero_connector._build_paper_info_from_doi(doi)
            
            if "error" in paper_info:
                return [types.TextContent(type="text", text=f"DOI parsing failed: {paper_info['error']}")]
            
            if not paper_info.get("title"):
                return [types.TextContent(type="text", text="Cannot extract paper title. DOI may be invalid or unsupported")]
            
            result = zotero_connector.save_item_to_zotero(paper_info, collection_key=collection_key)
            
            if result["success"]:
                message = f"Paper saved successfully!\n\n"
                message += f"DOI: {doi}\n"
                message += f"Title: {paper_info.get('title', 'Unknown')}\n"
                
                if paper_info.get('authors'):
                    message += f"Authors: {paper_info['authors']}\n"
                
                if paper_info.get('date'):
                    message += f"Date: {paper_info['date']}\n"
                
                if collection_key:
                    collection_moved = result.get("details", {}).get("collection_moved", False)
                    if collection_moved:
                        message += f"Collection: Moved to specified collection\n"
                    else:
                        message += f"Collection: Move failed, item in default location\n"
                else:
                    message += f"Saved to: My Library\n"
                
                if paper_info.get('pdf_url'):
                    message += f"PDF: {paper_info['pdf_url']}\n"
                
                message += f"\nTip: DOI is the most reliable paper identifier. Recommended!"
                
            else:
                message = f"Save failed: {result.get('message', 'Unknown error')}\n\n"
                message += f"Troubleshooting:\n"
                message += f"  Ensure Zotero desktop app is running\n"
                message += f"  Check network connection\n"
                message += f"  Verify DOI is valid"
            
            return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to save paper: {e}")
            return [types.TextContent(type="text", text=f"Error saving paper: {e}")]
    
    elif name == "create_zotero_collection":
        collection_name = arguments.get("name", "").strip()
        parent_key = arguments.get("parent_key", "").strip() or None
        
        if not collection_name:
            return [types.TextContent(type="text", text="Missing collection name")]
        
        if not zotero_connector.is_running():
            return [types.TextContent(type="text", text="Zotero unavailable. Please start Zotero desktop app")]
        
        message = f"Create Zotero Collection\n\n"
        message += f"Note: Due to Zotero API limitations, collections need to be created manually\n\n"
        message += f"Manual creation steps:\n"
        message += f"1. Open Zotero desktop app\n"
        message += f"2. Right-click on the collections panel on the left\n"
        message += f"3. Select 'New Collection'\n"
        message += f"4. Enter collection name: {collection_name}\n"
        
        if parent_key:
            message += f"5. Optionally drag under parent collection\n"
        
        message += f"6. Confirm creation\n\n"
        message += f"After creation:\n"
        message += f"  Use get_zotero_collections to get the new collection Key\n"
        message += f"  Use the Key in save_paper_to_zotero to specify target collection\n\n"
        message += f"Time: About 30 seconds for creation, long-term use!"
        
        return [types.TextContent(type="text", text=message)]
    
    elif name == "extract_arxiv_metadata":
        arxiv_url = arguments.get("arxiv_url")
        
        if not arxiv_url:
            return [types.TextContent(type="text", text="Missing arXiv URL")]
        
        if 'arxiv.org' not in arxiv_url:
            return [types.TextContent(type="text", text="Invalid arXiv URL")]
        
        try:
            metadata = zotero_connector._extract_arxiv_metadata(arxiv_url)
            
            if 'error' in metadata:
                return [types.TextContent(type="text", text=f"Extraction failed: {metadata['error']}")]
            
            message = f"arXiv Paper Metadata\n\n"
            message += f"arXiv ID: {metadata.get('arxiv_id', 'Unknown')}\n"
            message += f"Title: {metadata.get('title', 'Unknown')}\n"
            message += f"Authors: {metadata.get('authors_string', 'Unknown')}\n"
            message += f"Date: {metadata.get('date', 'Unknown')}\n"
            
            if metadata.get('comment'):
                message += f"Comment: {metadata['comment']}\n"
            
            if metadata.get('subjects'):
                subjects_str = ', '.join(metadata['subjects'][:3])
                message += f"Subjects: {subjects_str}\n"
            
            if metadata.get('doi'):
                message += f"DOI: {metadata['doi']}\n"
            
            message += f"PDF: {metadata.get('pdf_url', 'Unknown')}\n"
            
            if metadata.get('abstract'):
                abstract_preview = metadata['abstract'][:200] + "..." if len(metadata['abstract']) > 200 else metadata['abstract']
                message += f"\nAbstract Preview:\n{abstract_preview}\n"
            
            message += f"\nNext: Use save_paper_to_zotero to save to your library"
            
            return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to extract arXiv metadata: {e}")
            return [types.TextContent(type="text", text=f"Error extracting metadata: {e}")]
    
    elif name == "get_library_items":
        limit = arguments.get("limit", 50)
        offset = arguments.get("offset", 0)
        include_details = arguments.get("include_details", False)
        
        if not zotero_connector.is_running():
            return [types.TextContent(type="text", text="Zotero unavailable. Please start Zotero desktop app")]
        
        try:
            result = zotero_connector.get_library_items(limit=limit, offset=offset, include_details=include_details)
            
            if not result.get("success"):
                return [types.TextContent(type="text", text=f"Error: {result.get('error', 'Unknown error')}")]
            
            items = result.get("items", [])
            
            if not items:
                message = "Your library is empty or no more items\n\n"
                message += "Use save_paper_to_zotero to add papers!"
                return [types.TextContent(type="text", text=message)]
            
            message = f"Zotero Library Items (showing {len(items)} items)\n\n"
            
            for i, item in enumerate(items, 1):
                title = item.get('title', 'Untitled')
                item_type = item.get('itemType', 'Unknown')
                date_added = item.get('dateAdded', 'No date')[:10] if item.get('dateAdded') else 'No date'
                key = item.get('itemKey', 'No key')
                
                message += f"{i}. {title}\n"
                message += f"   Type: {item_type} | Added: {date_added}\n"
                message += f"   Key: {key}"
                
                if include_details:
                    attachment_count = item.get('attachment_count', 0)
                    note_count = item.get('note_count', 0)
                    tag_count = item.get('tag_count', 0)
                    tags = item.get('tags', [])
                    
                    details_parts = []
                    if attachment_count > 0:
                        details_parts.append(f"{attachment_count} attachments")
                    if note_count > 0:
                        details_parts.append(f"{note_count} notes")
                    if tag_count > 0:
                        details_parts.append(f"{tag_count} tags")
                    
                    if details_parts:
                        message += f" | {', '.join(details_parts)}"
                    
                    if tags:
                        message += f"\n   Tags: {', '.join(tags[:5])}"
                        if tag_count > 5:
                            message += f" +{tag_count - 5} more"
                
                message += "\n\n"
            
            message += f"Use get_zotero_item with a specific key for full details"
            
            return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to get library items: {e}")
            return [types.TextContent(type="text", text=f"Error getting library items: {e}")]
    
    elif name == "search_zotero_items":
        query = arguments.get("query", "").strip()
        
        if not query:
            return [types.TextContent(type="text", text="Missing search query")]
        
        if not zotero_connector.is_running():
            return [types.TextContent(type="text", text="Zotero unavailable. Please start Zotero desktop app")]
        
        try:
            results = zotero_connector.search_items(query)
            
            if not results:
                message = f"No items found matching: {query}\n\n"
                message += "Try different keywords or save new papers"
                return [types.TextContent(type="text", text=message)]
            
            message = f"Search Results for '{query}' ({len(results)} items)\n\n"
            
            for i, item in enumerate(results, 1):
                title = item.get('title', 'Untitled')
                item_type = item.get('itemType', 'Unknown')
                key = item.get('key', 'No key')
                
                message += f"{i}. {title}\n"
                message += f"   Type: {item_type} | Key: {key}\n\n"
            
            message += f"Use get_zotero_item with a specific key for details"
            
            return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to search items: {e}")
            return [types.TextContent(type="text", text=f"Error searching items: {e}")]
    
    elif name == "get_zotero_item":
        item_key = arguments.get("item_key", "").strip()
        include_attachments = arguments.get("include_attachments", True)
        
        if not item_key:
            return [types.TextContent(type="text", text="Missing item key")]
        
        if not zotero_connector.is_running():
            return [types.TextContent(type="text", text="Zotero unavailable. Please start Zotero desktop app")]
        
        try:
            result = zotero_connector.get_item(item_key, include_attachments=include_attachments)
            
            if not result.get("success"):
                return [types.TextContent(type="text", text=f"Item not found: {item_key}")]
            
            item = result.get("item", {})
            
            title = item.get('title', 'Untitled')
            item_type = item.get('itemType', 'Unknown')
            date = item.get('date', 'No date')
            url = item.get('url', 'No URL')
            abstract = item.get('abstractNote', 'No abstract')
            creators = item.get('creators', [])
            attachments = item.get('attachments', [])
            notes = item.get('notes', [])
            tags = item.get('tags', [])
            
            message = f"Zotero Item Details\n\n"
            message += f"Title: {title}\n"
            message += f"Type: {item_type}\n"
            message += f"Date: {date}\n"
            message += f"URL: {url}\n"
            
            if creators:
                authors = []
                for c in creators:
                    name = c.get('firstName', '') + ' ' + c.get('lastName', '')
                    if name.strip():
                        authors.append(name.strip())
                if authors:
                    message += f"Authors: {', '.join(authors)}\n"
            
            if abstract and abstract != 'No abstract':
                abstract_preview = abstract[:500] + "..." if len(abstract) > 500 else abstract
                message += f"\nAbstract:\n{abstract_preview}\n"
            
            if include_attachments:
                if attachments:
                    message += f"\nAttachments ({len(attachments)}):\n"
                    for att in attachments[:5]:
                        filename = att.get('filename', 'Unknown')
                        content_type = att.get('contentType', 'Unknown')
                        message += f"  - {filename} ({content_type})\n"
                    if len(attachments) > 5:
                        message += f"  ... and {len(attachments) - 5} more\n"
                
                if notes:
                    message += f"\nNotes ({len(notes)}):\n"
                    for note in notes[:3]:
                        note_text = note.get('note', '')[:100]
                        message += f"  - {note_text}...\n"
                    if len(notes) > 3:
                        message += f"  ... and {len(notes) - 3} more\n"
                
                if tags:
                    message += f"\nTags: {', '.join(tags)}\n"
            
            message += f"\nKey: {item_key}"
            
            return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to get item: {e}")
            return [types.TextContent(type="text", text=f"Error getting item: {e}")]
    
    elif name == "update_zotero_item":
        item_key = arguments.get("item_key", "").strip()
        title = arguments.get("title", "").strip() or None
        abstract = arguments.get("abstract", "").strip() or None
        date = arguments.get("date", "").strip() or None
        url = arguments.get("url", "").strip() or None
        
        if not item_key:
            return [types.TextContent(type="text", text="Missing item key")]
        
        if not zotero_connector.is_running():
            return [types.TextContent(type="text", text="Zotero unavailable. Please start Zotero desktop app")]
        
        try:
            updates = {}
            if title: updates['title'] = title
            if abstract: updates['abstractNote'] = abstract
            if date: updates['date'] = date
            if url: updates['url'] = url
            
            if not updates:
                return [types.TextContent(type="text", text="No updates specified")]
            
            success = zotero_connector.update_item(item_key, updates)
            
            if success:
                message = f"Item updated successfully!\n\n"
                message += f"Key: {item_key}\n"
                if title: message += f"New title: {title}\n"
                if abstract: message += f"New abstract: Set\n"
                if date: message += f"New date: {date}\n"
                if url: message += f"New URL: {url}\n"
                message += f"\nCheck Zotero to verify changes"
            else:
                message = f"Update failed for item: {item_key}\n\n"
                message += f"Possible causes:\n"
                message += f"  Item may not exist\n"
                message += f"  Network error\n"
                message += f"  Zotero sync in progress"
            
            return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to update item: {e}")
            return [types.TextContent(type="text", text=f"Error updating item: {e}")]
    
    elif name == "update_zotero_item_tags":
        item_key = arguments.get("item_key", "").strip()
        tags = arguments.get("tags", [])
        
        if not item_key:
            return [types.TextContent(type="text", text="Missing item key")]
        
        if not tags:
            return [types.TextContent(type="text", text="No tags specified")]
        
        if not zotero_connector.is_running():
            return [types.TextContent(type="text", text="Zotero unavailable. Please start Zotero desktop app")]
        
        try:
            success = zotero_connector.update_item_tags(item_key, tags)
            
            if success:
                message = f"Tags updated successfully!\n\n"
                message += f"Item Key: {item_key}\n"
                message += f"New Tags: {', '.join(tags)}\n"
            else:
                message = f"Failed to update tags for: {item_key}\n\n"
                message += f"Possible causes:\n"
                message += f"  Item may not exist\n"
                message += f"  Network error"
            
            return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to update tags: {e}")
            return [types.TextContent(type="text", text=f"Error updating tags: {e}")]
    
    elif name == "delete_zotero_item":
        item_key = arguments.get("item_key", "").strip()
        
        if not item_key:
            return [types.TextContent(type="text", text="Missing item key")]
        
        if not zotero_connector.is_running():
            return [types.TextContent(type="text", text="Zotero unavailable. Please start Zotero desktop app")]
        
        try:
            success = zotero_connector.delete_item(item_key)
            
            if success:
                message = f"Item deleted successfully!\n\n"
                message += f"Key: {item_key}\n"
                message += f"\nNote: This action cannot be undone"
            else:
                message = f"Failed to delete item: {item_key}\n\n"
                message += f"Possible causes:\n"
                message += f"  Item may not exist\n"
                message += f"  Network error"
            
            return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to delete item: {e}")
            return [types.TextContent(type="text", text=f"Error deleting item: {e}")]
    
    elif name == "move_zotero_item":
        item_key = arguments.get("item_key", "").strip()
        collection_key = arguments.get("collection_key", "").strip()
        
        if not item_key:
            return [types.TextContent(type="text", text="Missing item key")]
        
        if not collection_key:
            return [types.TextContent(type="text", text="Missing collection key")]
        
        if not zotero_connector.is_running():
            return [types.TextContent(type="text", text="Zotero unavailable. Please start Zotero desktop app")]
        
        try:
            success = zotero_connector.move_item_to_collection(item_key, collection_key)
            
            if success:
                message = f"Item moved successfully!\n\n"
                message += f"Item Key: {item_key}\n"
                message += f"Collection Key: {collection_key}\n"
            else:
                message = f"Failed to move item: {item_key}\n\n"
                message += f"Possible causes:\n"
                message += f"  Item or collection may not exist\n"
                message += f"  Network error\n"
                message += f"  Use get_zotero_collections to verify keys"
            
            return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to move item: {e}")
            return [types.TextContent(type="text", text=f"Error moving item: {e}")]
    
    elif name == "search_arxiv_api":
        query = arguments.get("query", "").strip()
        max_results = arguments.get("max_results", 5)
        
        if not query:
            return [types.TextContent(type="text", text="Missing search query")]
        
        try:
            if max_results > 50:
                max_results = 50
            elif max_results < 1:
                max_results = 1
            
            results = zotero_connector.search_arxiv(query, max_results=max_results)
            
            if not results:
                message = f"No results found for: {query}\n\n"
                message += f"Try different search terms"
                return [types.TextContent(type="text", text=message)]
            
            message = f"arXiv Search Results for '{query}' ({len(results)} items)\n\n"
            
            for i, paper in enumerate(results, 1):
                title = paper.get('title', 'Untitled')
                arxiv_id = paper.get('id', 'Unknown')
                date = paper.get('published', 'Unknown date')
                authors = paper.get('authors', [])
                
                message += f"{i}. {title}\n"
                message += f"   ID: {arxiv_id}\n"
                message += f"   Date: {date}\n"
                if authors:
                    author_names = [a.get('name', '') for a in authors[:3]]
                    message += f"   Authors: {', '.join(author_names)}\n"
                message += f"   Link: https://arxiv.org/abs/{arxiv_id}\n\n"
            
            message += f"Use save_paper_to_zotero with the arXiv URL to save papers"
            
            return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to search arXiv: {e}")
            return [types.TextContent(type="text", text=f"Error searching arXiv: {e}")]
    
    elif name == "validate_zotero_item":
        item_key = arguments.get("item_key", "").strip()
        
        if not item_key:
            return [types.TextContent(type="text", text="Missing item key")]
        
        if not zotero_connector.is_running():
            return [types.TextContent(type="text", text="Zotero unavailable. Please start Zotero desktop app")]
        
        try:
            item = zotero_connector.get_item(item_key)
            
            if not item:
                return [types.TextContent(type="text", text=f"Item not found: {item_key}")]
            
            doi = item.get('DOI', '')
            
            if not doi or 'arxiv' not in doi.lower():
                return [types.TextContent(type="text", text=f"Item {item_key} does not have an arXiv DOI. Validation requires arXiv papers.")]
            
            arxiv_id = doi.replace('10.48550/arXiv.', '')
            
            metadata = zotero_connector._extract_arxiv_metadata(f"https://arxiv.org/abs/{arxiv_id}")
            
            if 'error' in metadata:
                return [types.TextContent(type="text", text=f"Failed to fetch arXiv metadata: {metadata['error']}")]
            
            differences = []
            
            zotero_title = item.get('title', '').strip()
            arxiv_title = metadata.get('title', '').strip().replace('\n', ' ')
            
            if zotero_title.lower() != arxiv_title.lower():
                differences.append(f"Title:\n  Zotero: {zotero_title}\n  arXiv: {arxiv_title}\n")
            
            zotero_date = item.get('date', '')
            arxiv_date = metadata.get('date', '')
            
            if zotero_date and zotero_date != arxiv_date:
                differences.append(f"Date:\n  Zotero: {zotero_date}\n  arXiv: {arxiv_date}\n")
            
            message = f"Validation Results for {item_key}\n\n"
            message += f"DOI: {doi}\n"
            message += f"arXiv ID: {arxiv_id}\n\n"
            
            if differences:
                message += f"Found {len(differences)} difference(s):\n\n"
                for diff in differences:
                    message += f"{diff}\n"
                message += f"Use validate_and_update_item to automatically update"
            else:
                message += f"No differences found. Metadata matches arXiv!"
            
            return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to validate item: {e}")
            return [types.TextContent(type="text", text=f"Error validating item: {e}")]
    
    elif name == "validate_and_update_item":
        item_key = arguments.get("item_key", "").strip()
        apply_updates = arguments.get("apply_updates", False)
        
        if not item_key:
            return [types.TextContent(type="text", text="Missing item key")]
        
        if not zotero_connector.is_running():
            return [types.TextContent(type="text", text="Zotero unavailable. Please start Zotero desktop app")]
        
        try:
            item = zotero_connector.get_item(item_key)
            
            if not item:
                return [types.TextContent(type="text", text=f"Item not found: {item_key}")]
            
            doi = item.get('DOI', '')
            
            if not doi or 'arxiv' not in doi.lower():
                return [types.TextContent(type="text", text=f"Item {item_key} does not have an arXiv DOI. Validation requires arXiv papers.")]
            
            arxiv_id = doi.replace('10.48550/arXiv.', '')
            
            metadata = zotero_connector._extract_arxiv_metadata(f"https://arxiv.org/abs/{arxiv_id}")
            
            if 'error' in metadata:
                return [types.TextContent(type="text", text=f"Failed to fetch arXiv metadata: {metadata['error']}")]
            
            updates = {}
            zotero_title = item.get('title', '').strip()
            arxiv_title = metadata.get('title', '').strip().replace('\n', ' ')
            
            if zotero_title.lower() != arxiv_title.lower():
                updates['title'] = arxiv_title
            
            zotero_date = item.get('date', '')
            arxiv_date = metadata.get('date', '')
            
            if zotero_date and zotero_date != arxiv_date:
                updates['date'] = arxiv_date
            
            message = f"Validation Results for {item_key}\n\n"
            message += f"DOI: {doi}\n"
            message += f"arXiv ID: {arxiv_id}\n\n"
            
            if not updates:
                message += f"No updates needed. Metadata matches arXiv!"
                if apply_updates:
                    message += f"\nNothing to update."
                return [types.TextContent(type="text", text=message)]
            
            if apply_updates:
                success = zotero_connector.update_item(item_key, updates)
                
                if success:
                    message += f"Applied {len(updates)} update(s):\n\n"
                    if 'title' in updates:
                        message += f"Title: Updated to arXiv version\n"
                    if 'date' in updates:
                        message += f"Date: Updated to {arxiv_date}\n"
                    message += f"\nZotero item updated successfully!"
                else:
                    message += f"Failed to apply updates to {item_key}"
                
                return [types.TextContent(type="text", text=message)]
            else:
                message += f"Found {len(updates)} update(s) available:\n\n"
                if 'title' in updates:
                    message += f"Title:\n  Current: {zotero_title}\n  arXiv: {arxiv_title}\n\n"
                if 'date' in updates:
                    message += f"Date:\n  Current: {zotero_date}\n  arXiv: {arxiv_date}\n\n"
                message += f"Use apply_updates=true to apply these changes"
                return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to validate and update item: {e}")
            return [types.TextContent(type="text", text=f"Error: {e}")]
    
    elif name == "fetch_pdf":
        item_key = arguments.get("item_key", "").strip()
        source = arguments.get("source", "auto")
        save_to_zotero = arguments.get("save_to_zotero", True)
        
        if not item_key:
            return [types.TextContent(type="text", text="Missing item key")]
        
        if not zotero_connector.is_running():
            return [types.TextContent(type="text", text="Zotero unavailable. Please start Zotero desktop app")]
        
        try:
            item = zotero_connector.get_item(item_key)
            
            if not item:
                return [types.TextContent(type="text", text=f"Item not found: {item_key}")]
            
            title = item.get('title', 'Unknown')
            message = f"Fetching PDF for: {title}\n\n"
            
            pdf_result = zotero_connector.fetch_pdf_for_item(item_key, source=source)
            
            if pdf_result.get("success"):
                message += f"PDF fetched successfully!\n"
                message += f"Source: {pdf_result.get('source', 'Unknown')}\n"
                message += f"Size: {pdf_result.get('size', 'Unknown')}\n"
                
                if pdf_result.get("saved_to_zotero"):
                    message += f"Status: Saved to Zotero as attachment\n"
                elif save_to_zotero:
                    message += f"Status: Downloaded but not saved to Zotero\n"
                else:
                    message += f"Status: Downloaded only\n"
                
                if pdf_result.get("file_path"):
                    message += f"Path: {pdf_result['file_path']}\n"
                
                message += f"\nTip: Check Zotero to view the PDF attachment"
            else:
                error_msg = pdf_result.get("error", "Unknown error")
                message += f"Failed to fetch PDF: {error_msg}\n\n"
                
                if "open access" in error_msg.lower() or "arXiv" in error_msg:
                    message += f"Possible causes:\n"
                    message += f"  Paper is behind paywall\n"
                    message += f"  arXiv PDF not yet available\n"
                    message += f"  Publisher doesn't provide open access\n\n"
                    message += f"Suggestions:\n"
                    message += f"  Try alternative source: arXiv, PubMed, etc.\n"
                    message += f"  Check if PDF is available on publisher website"
                else:
                    message += f"Network or server error. Try again later."
            
            return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to fetch PDF: {e}")
            return [types.TextContent(type="text", text=f"Error fetching PDF: {e}")]
    
    elif name == "get_item_pdf_text":
        item_key = arguments.get("item_key", "").strip()
        
        if not item_key:
            return [types.TextContent(type="text", text="Missing item key")]
        
        if not zotero_connector.is_running():
            return [types.TextContent(type="text", text="Zotero unavailable. Please start Zotero desktop app")]
        
        try:
            result = zotero_connector.get_item_pdf_content(item_key)
            
            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")
                message = f"Failed to extract PDF text: {error_msg}\n\n"
                
                if "not found" in error_msg.lower():
                    message += f"Possible causes:\n"
                    message += f"  Item does not exist\n"
                    message += f"  Item key is incorrect\n\n"
                    message += f"Suggestions:\n"
                    message += f"  Use get_library_items to list available items\n"
                    message += f"  Copy the correct item key"
                elif "no pdf" in error_msg.lower():
                    message += f"Possible causes:\n"
                    message += f"  Item has no PDF attachment\n"
                    message += f"  PDF is stored remotely\n\n"
                    message += f"Suggestions:\n"
                    message += f"  Use fetch_pdf to download a PDF\n"
                    message += f"  Check if PDF is synced locally"
                else:
                    message += f"PDF may not be synced locally.\n"
                    message += f"Open Zotero and ensure the item is synced."
                
                return [types.TextContent(type="text", text=message)]
            
            title = result.get("title", "Untitled")
            page_count = result.get("page_count", 0)
            char_count = result.get("character_count", 0)
            text = result.get("text", "")
            
            message = f"PDF Text Extracted\n\n"
            message += f"Item: {title}\n"
            message += f"Pages: {page_count}\n"
            message += f"Characters: {char_count:,}\n\n"
            
            if text:
                text_preview = text[:2000] + "..." if len(text) > 2000 else text
                message += f"Text Preview:\n{text_preview}\n"
                
                message += f"\nFull text available for full-text search.\n"
                message += f"Use get_item_pdf_text to extract text from other items."
            else:
                message += f"No text could be extracted from the PDF.\n"
                message += f"The PDF may be scanned images without OCR."
            
            return [types.TextContent(type="text", text=message)]
            
        except Exception as e:
            logger.error(f"Failed to extract PDF text: {e}")
            return [types.TextContent(type="text", text=f"Error extracting PDF text: {e}")]
    
    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    """Main entry point"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="zotlink",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

def run():
    """Entry point for uvx"""
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())

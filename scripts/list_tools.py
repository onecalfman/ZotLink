#!/usr/bin/env python3
"""List ZotLink MCP server tools"""

tools = [
    ("check_zotero_status", "Check Zotero connection status"),
    ("get_zotero_collections", "Get all Zotero collections"),
    ("save_paper_to_zotero", "Save a paper by URL (arXiv, DOI, etc.)"),
    ("save_paper_by_doi", "Save a paper by DOI (recommended for reliable metadata)"),
    ("create_zotero_collection", "Create a new collection"),
    ("extract_arxiv_metadata", "Extract arXiv metadata"),
    ("set_database_cookies", "Set database authentication cookies"),
    ("get_supported_databases", "List supported databases"),
    ("get_databases_status", "Get database status info"),
    ("update_database_cookies", "Update database cookies"),
    ("test_database_access", "Test database access"),
    ("get_cookie_guide", "Get cookie acquisition guide"),
    ("get_database_auth_status", "Get authentication status"),
    ("get_authentication_guide", "Get authentication guide"),
    ("generate_bookmark_code", "Generate bookmarklet code"),
    ("get_library_items", "Get items from library"),
    ("search_zotero_items", "Search library items"),
    ("get_zotero_item", "Get specific item"),
    ("update_zotero_item", "Update item metadata"),
    ("update_zotero_item_tags", "Update item tags"),
    ("delete_zotero_item", "Delete an item"),
    ("move_zotero_item", "Move item to collection"),
    ("search_arxiv_api", "Search arXiv API"),
    ("validate_zotero_item", "Validate item against arXiv"),
    ("validate_and_update_item", "Validate and update item"),
    ("fetch_pdf", "Fetch PDF from sources"),
]

print("=== ZotLink MCP Server Tools ===")
for name, desc in tools:
    print(f"  {name}: {desc}")

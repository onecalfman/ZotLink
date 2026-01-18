# ZotLink Development Commands
# Just = command runner (brew install just)
#
# Usage: just <command>

default:
    @just --list

# Sync dependencies
install:
    uv sync

# Install package
install-package:
    uv pip install -e .

# Run all tests
test:
    uv run pytest tests/ -v --tb=short

# Run tests quietly
test-quick:
    uv run pytest tests/ -q

# Run with coverage
test-coverage:
    uv run pytest tests/ --cov=zotlink --cov-report=html
    @echo "Coverage: htmlcov/index.html"

# Type checking
typecheck:
    uv run mypy zotlink/ --ignore-missing-imports

# Lint code
lint:
    uv run ruff check zotlink/

# Format code
format:
    uv run ruff format zotlink/ tests/

# Start MCP server
start:
    uv run python -m zotlink.zotero_mcp_server

# Check Zotero connection
check-zotero:
    uv run python -c "import zotlink.zotero_integration as zi; c = zi.ZoteroConnector(); print('Running:', c.is_running())"

# Test arXiv API
test-arxiv:
    uv run python -c "import zotlink.extractors.arxiv_extractor as ae; r = ae.search_arxiv('transformer', max_results=3); print('Found:', len(r.get('entries', [])))"

# Test PDF fetching
test-pdf:
    @echo "PDF Fetch Sources:" && uv run python -c "import zotlink.pdf_fetcher as pf; f = pf.PDFFetcher(); print('  ' + ', '.join(f._get_source_order('auto')))"
    @echo "Testing PDF fetch with DOI: 10.3390/s25123806" && uv run python -c "import sys; sys.path.insert(0, '.'); from zotlink.pdf_fetcher import PDFFetcher; from zotlink.zotero_integration import ZoteroConnector; c = ZoteroConnector(); f = PDFFetcher(c); r = f.fetch_pdf('76ZP9V4C', source='auto', save_to_zotero=False); print('Success:', r.get('success', False)); print('Source:', r.get('source', 'unknown'))"

# List MCP server tools
list-tools:
    @python scripts/list_tools.py

# Run all checks
check: lint typecheck test
    @echo "All checks passed!"

# Clean up
clean:
    rm -rf htmlcov/ .coverage __pycache__/ tests/__pycache__/ zotlink/__pycache__/ zotlink/*/__pycache__/
    rm -rf .pytest_cache/ .hypothesis/
    rm -rf .venv
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Benchmark
benchmark:
    @echo "Benchmarking..." && time uv run pytest tests/test_zotlink.py -q --tb=0

# Package info
info:
    @uv run python -c "import zotlink; print('Version:', getattr(zotlink, '__version__', 'unknown'))" 2>/dev/null || echo "unknown"
    @echo "Python:" $(uv run python --version 2>&1)


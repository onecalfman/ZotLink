#!/usr/bin/env python3
"""
Remove Chinese comments from Python files and replace with English equivalents.
"""

import re
import os

def remove_chinese_comments(content):
    """Remove or replace Chinese comments with English equivalents"""
    
    replacements = [
        # Docstrings and module headers
        (r'"""🔗 ZotLink.*?旧易维护"""', '"""ZotLink MCP Server - Academic paper management for Zotero"""'),
        (r'🔗 ZotLink Zotero集成模块', 'ZotLink Zotero Integration Module'),
        (r'🔗 ZotLink 提取器管理器', 'ZotLink Extractor Manager'),
        (r'🔗 ZotLink - 智能学术文献管理MCP工具', 'ZotLink - Academic Literature Management MCP Tool'),
        (r'基于Zotero Connector官方源代码实现的智能文献管理系统', 'Smart academic literature management based on Zotero Connector API'),
        (r'提供完整的学术文献管理功能，支持：', 'Full academic literature management with support for:'),
        (r'- 📄 arXiv论文自动处理（元数据 \+ PDF）', '- arXiv paper auto-processing (metadata + PDF)'),
        (r'- 🎯 智能集合管理（updateSession机制）', '- Smart collection management (updateSession mechanism)'),
        (r'- 📚 开放获取期刊支持', '- Open access journal support'),
        (r'- 🤖 完全自动化的PDF下载', '- Fully automated PDF downloads'),
        (r'- 📝 完整的元数据提取（Comment、DOI、学科分类等）', '- Complete metadata extraction (Comment, DOI, subjects, etc.)'),
        (r'技术特点：', 'Technical features:'),
        (r'- 无需cookies或登录认证', '- No cookies or login required'),
        (r'- 基于Zotero Connector官方API', '- Based on Zotero Connector official API'),
        (r'- 支持treeViewID和updateSession机制', '- Supports treeViewID and updateSession mechanisms'),
        (r'- 100%开源，易于维护', '- 100% open source, easy to maintain'),
        
        # Function/method comments
        (r'初始化连接器', 'Initialize connector'),
        (r'从环境变量与配置文件加载Zotero路径覆盖设置', 'Load Zotero path overrides from env vars and config'),
        (r'从Claude配置文件加载Zotero路径设置', 'Load Zotero paths from Claude config'),
        (r'从arxiv URL提取详细的论文元数据', 'Extract detailed paper metadata from arXiv URL'),
        (r'提取arxiv ID', 'Extract arXiv ID'),
        (r'获取arxiv摘要页面', 'Get arXiv abstract page'),
        (r'提取标题', 'Extract title'),
        (r'提取作者 - 改进版本', 'Extract authors - improved version'),
        (r'格式化作者列表', 'Format author list'),
        (r'提取摘要 - 改进版本', 'Extract abstract - improved version'),
        (r'提取日期 - 改进版本', 'Extract date - improved version'),
        (r'提取评论信息（页数、图表等）', 'Extract comment info (pages, figures, etc.)'),
        (r'提取学科分类', 'Extract subject classification'),
        (r'提取DOI（如果有）', 'Extract DOI if available'),
        (r'提取期刊信息（如果已发表）', 'Extract journal info if published'),
        (r'为arxiv论文增强元数据', 'Enhance metadata for arXiv papers'),
        (r'检测到arxiv论文，开始增强元数据', 'Detected arXiv paper, enhancing metadata...'),
        (r'合并元数据，优先使用arxiv提取的信息', 'Merge metadata, prefer arXiv extracted info'),
        (r'查找Zotero数据库文件，优先使用覆盖路径', 'Find Zotero database, prefer override path'),
        (r'直接从数据库读取集合信息', 'Read collections directly from database'),
        (r'创建临时副本以避免锁定问题', 'Create temp copy to avoid locking issues'),
        (r'清理临时文件', 'Clean up temp files'),
        (r'读取数据库集合失败', 'Failed to read database collections'),
        (r'检查Zotero是否在运行', 'Check if Zotero is running'),
        (r'获取Zotero版本信息', 'Get Zotero version info'),
        (r'获取所有集合', 'Get all collections'),
        (r'优先尝试直接读取数据库，备选API方式', 'Try direct DB read first, fallback to API'),
        (r'首先尝试直接从数据库读取（新的解决方案！）', 'First try reading directly from database (new solution!)'),
        (r'如果数据库读取失败，回退到API方式', 'If DB read fails, fallback to API'),
        (r'保存论文到Zotero', 'Save paper to Zotero'),
        (r'检查Zotero是否在运行', 'Check if Zotero is running'),
        (r'构建Zotero项目数据', 'Build Zotero item data'),
        (r'保存到Zotero', 'Save to Zotero'),
        (r'智能分割逗号分隔的作者', 'Smart split comma-separated authors'),
        (r'将论文信息转换为Zotero格式', 'Convert paper info to Zotero format'),
        (r'解析作者 - 改进的逻辑支持多种格式', 'Parse authors - improved logic supports multiple formats'),
        (r'解析日期', 'Parse date'),
        (r'确定项目类型', 'Determine item type'),
        (r'下载PDF内容', 'Download PDF content'),
        (r'根据论文信息智能确定默认的期刊/会议名称', 'Smart determine default publication title'),
        (r'通过Connector API保存项目 - 实用解决方案', 'Save via Connector API - practical solution'),
        (r'按照官方插件方法：生成随机ID', 'Follow official plugin method: generate random ID'),
        (r'为item生成随机ID', 'Generate random ID for item'),
        (r'构建保存payload', 'Build save payload'),
        (r'设置目标集合', 'Set target collection'),
        (r'保存项目', 'Save item'),
        (r'尝试下载PDF内容', 'Attempt to download PDF content'),
        (r'测试数据库访问', 'Test database access'),
        (r'获取所有数据库的状态信息', 'Get status info for all databases'),
        (r'读取数据库状态失败', 'Failed to read database status'),
        (r'测试Zotero连接', 'Test Zotero connection'),
        (r'在ZoteroConnector类中添加新方法', 'Add new methods to ZoteroConnector class'),
        
        # Logging messages
        (r'✅ 提取器管理器初始化成功', 'Extractor manager initialized successfully'),
        (r'⚠️ 提取器管理器不可用', 'Extractor manager not available'),
        (r'🔧 从Zotero根目录自动推导数据库路径', 'Auto-detected DB path from Zotero root'),
        (r'🔧 从Zotero根目录自动推导存储目录', 'Auto-detected storage dir from Zotero root'),
        (r'⚠️ Zotero根目录.*?下未找到预期的数据库或存储目录', 'Zotero root does not contain expected database or storage'),
        (r'🔧 使用环境变量ZOTLINK_ZOTERO_DB覆盖Zotero数据库路径', 'Using env var to override Zotero DB path'),
        (r'🔧 使用配置文件覆盖Zotero数据库路径', 'Using config to override Zotero DB path'),
        (r'🔧 使用配置文件指定storage目录', 'Using config to specify storage directory'),
        (r'🔧 加载Zotero路径覆盖设置失败', 'Failed to load Zotero path overrides'),
        (r'📖 找到Claude配置文件', 'Found Claude config file'),
        (r'💡 推荐在MCP配置中使用env环境变量设置Zotero路径', 'Recommended: use env vars for Zotero paths in MCP config'),
        (r'⚠️ 读取Claude配置文件失败', 'Failed to read Claude config'),
        (r'⚠️ 加载Claude配置失败', 'Failed to load Claude config'),
        (r'提取arxiv ID:', 'Extracting arXiv ID:'),
        (r'成功提取arxiv元数据:', 'Successfully extracted arXiv metadata:'),
        (r'提取arxiv元数据失败:', 'Failed to extract arXiv metadata:'),
        (r'检测到arxiv论文，开始增强元数据...', 'Detected arXiv paper, starting metadata enhancement...'),
        (r'arxiv元数据增强完成:', 'arXiv metadata enhancement complete:'),
        (r'arxiv元数据增强失败:', 'arXiv metadata enhancement failed:'),
        (r'找到Zotero数据库', 'Found Zotero database'),
        (r'未找到Zotero数据库文件', 'Zotero database file not found'),
        (r'从数据库成功读取.*?个集合', 'Successfully read N collections from database'),
        (r'读取数据库集合失败:', 'Failed to read collections from database:'),
        (r'Zotero未运行或无法连接', 'Zotero not running or cannot connect'),
        (r'获取Zotero版本失败', 'Failed to get Zotero version'),
        (r'尝试直接从数据库读取集合', 'Attempting to read collections directly from database'),
        (r'✅ 成功从数据库获取.*?个集合', 'Successfully got N collections from database'),
        (r'数据库读取失败，尝试API方式', 'Database read failed, trying API'),
        (r'成功从端点获取集合', 'Successfully got collections from endpoint'),
        (r'无法通过API或数据库获取集合列表', 'Cannot get collection list via API or database'),
        (r'获取Zotero集合失败', 'Failed to get Zotero collections'),
        (r'成功保存到Zotero:', 'Successfully saved to Zotero:'),
        (r'🎯 关键修复：在返回结果中添加正确的标题信息', 'FIX: Add correct title info to return result'),
        (r'保存到Zotero失败:', 'Failed to save to Zotero:'),
        (r'成功保存项目', 'Successfully saved item'),
        (r'🎯 正确的附件处理：调用saveAttachment API保存PDF', 'CORRECT: Use saveAttachment API for PDF'),
        (r'🔍 发现PDF链接', 'Found PDF link'),
        (r'📎 将在保存后手动触发PDF下载', 'Will manually trigger PDF download after save'),
        (r'✅ 使用浏览器预下载的PDF内容，跳过HTTP下载', 'Using browser-pre-downloaded PDF content, skipping HTTP'),
        (r'PDF下载成功', 'PDF download successful'),
        (r'PDF下载失败', 'PDF download failed'),
        (r'✅ 项目保存成功', 'Item saved successfully'),
        (r'⚠️ PDF附件：链接附件已添加', 'PDF attachment: link attachment added'),
        (r'✅ 保存成功！论文元数据和PDF链接已处理', 'Save successful! Paper metadata and PDF link processed'),
        (r'✅ 集合移动成功', 'Collection move successful'),
        (r'✅ 更新.*?cookies成功', 'Updated cookies successfully'),
        (r'❌ 更新.*?cookies失败', 'Failed to update cookies'),
        (r'❌ 更新数据库cookies失败', 'Failed to update database cookies'),
        (r'✅ Zotero连接成功，版本:', 'Zotero connection successful, version:'),
        (r'⚠️ Zotero连接成功，但无法获取版本信息', 'Zotero connection successful, but could not get version'),
        (r'❌ Zotero未运行或连接失败', 'Zotero not running or connection failed'),
        (r'🧪 测试Zotero连接...', 'Testing Zotero connection...'),
        (r'📚 找到.*?个集合', 'Found N collections'),
        
        # UI messages
        (r'🎉 \*\*Zotero连接成功！\*\*', 'Zotero Connection Successful!'),
        (r'📱 \*\*应用状态\*\*: ✅ Zotero桌面应用正在运行', 'App Status: Zotero desktop is running'),
        (r'📝 \*\*版本信息\*\*:', 'Version Info:'),
        (r'📚 \*\*集合数量\*\*:', 'Collection Count:'),
        (r'🔗 \*\*API端点\*\*:', 'API Endpoint:'),
        (r'✨ \*\*支持的数据库\*\*', 'Supported Databases'),
        (r'🛠️ \*\*可用功能\*\*:', 'Available Features:'),
        (r'🚀 \*\*开始使用\*\*:', 'Getting Started:'),
        (r'❌ \*\*Zotero未运行\*\*', 'Zotero Not Running'),
        (r'🔧 \*\*解决方案\*\*:', 'Solutions:'),
        (r'💡 \*\*要求\*\*:', 'Requirements:'),
        (r'📚 \*\*集合管理\*\*', 'Collection Management'),
        (r'⚠️ 当前没有发现任何集合', 'No collections found'),
        (r'💡 \*\*建议\*\*:', 'Suggestions:'),
        (r'📚 \*\*Zotero集合列表\*\*', 'Zotero Collection List'),
        (r'\*\*使用方法\*\*:', 'Usage:'),
        
        # Various Chinese patterns in code
        (r'未知作者', 'Unknown Author'),
        (r'未知日期', 'Unknown Date'),
        (r'未知集合', 'Unknown Collection'),
        (r'未知标题', 'Unknown Title'),
        (r'无法解析arxiv ID', 'Cannot parse arXiv ID'),
        (r'无法访问arxiv页面', 'Cannot access arXiv page'),
        (r'元数据提取失败', 'Metadata extraction failed'),
        (r'Zotero未运行，请启动Zotero桌面应用', 'Zotero is not running, please start the Zotero desktop app'),
    ]
    
    result = content
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result)
    
    return result

def process_file(filepath):
    """Process a single Python file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = remove_chinese_comments(content)
        
        if content != new_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Cleaned: {filepath}")
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = ['zotlink/zotero_integration.py', 'zotlink/zotero_mcp_server.py']
    
    for filepath in files:
        if os.path.exists(filepath):
            process_file(filepath)
        else:
            print(f"File not found: {filepath}")

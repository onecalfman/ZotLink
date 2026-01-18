#!/usr/bin/env python3
"""
Base extractor for ZotLink.

Defines the common interface for all academic database extractors.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List
import requests
import logging

from ..utils import BrowserConfig

logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    """Base class for academic database extractors."""
    
    def __init__(self, session: Optional[requests.Session] = None):
        """
        Initialize extractor.
        
        Args:
            session: Optional requests session for maintaining cookies/state
        """
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': BrowserConfig.USER_AGENT
        })
    
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """检查此提取器是否可以处理给定的URL"""
        pass
    
    @abstractmethod
    def extract_metadata(self, url: str) -> Dict:
        """从URL提取论文元数据"""
        pass
    
    @abstractmethod 
    def requires_authentication(self) -> bool:
        """检查此提取器是否需要认证"""
        pass
    
    @abstractmethod
    def get_database_name(self) -> str:
        """获取数据库名称"""
        pass
    
    def set_cookies(self, cookies: str) -> bool:
        """设置认证cookies"""
        if not self.requires_authentication():
            return True
            
        try:
            # 解析cookie字符串并设置到session
            if cookies:
                # 简单的cookie解析
                cookie_dict = {}
                for cookie in cookies.split(';'):
                    if '=' in cookie:
                        key, value = cookie.strip().split('=', 1)
                        cookie_dict[key] = value
                
                self.session.cookies.update(cookie_dict)
                logger.info(f"✅ 为{self.get_database_name()}设置cookies成功")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ 设置cookies失败: {e}")
            return False
    
    def test_access(self, test_url: Optional[str] = None) -> bool:
        """测试是否有访问权限"""
        return True  # 默认实现
    
    def get_supported_item_types(self) -> List[str]:
        """获取支持的Zotero项目类型"""
        return ['journalArticle', 'preprint', 'book', 'bookSection', 'conferencePaper']

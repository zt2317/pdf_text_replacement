import json
import os
import logging
from typing import List, Dict, Any

class ConfigManager:
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = config_dir
        self.logger = logging.getLogger(__name__)
    
    def list_config_files(self) -> List[str]:
        """列出所有配置文件"""
        if not os.path.exists(self.config_dir):
            self.logger.warning(f"配置目录不存在: {self.config_dir}")
            return []
        
        files = [f for f in os.listdir(self.config_dir) if f.endswith('.json')]
        self.logger.info(f"发现配置文件: {files}")
        return files
    
    def load_config(self, config_name: str) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = os.path.join(self.config_dir, config_name)
        
        if not os.path.exists(config_path):
            self.logger.error(f"配置文件不存在: {config_path}")
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.logger.info(f"成功加载配置: {config_name}")
            return config
        except json.JSONDecodeError as e:
            self.logger.error(f"配置文件格式错误: {config_path} - {e}")
            raise
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {config_path} - {e}")
            raise
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置文件格式"""
        if "replacements" not in config:
            self.logger.error("配置文件缺少 replacements 字段")
            return False
        
        if not isinstance(config["replacements"], list):
            self.logger.error("配置文件中 replacements 应该是列表")
            return False
        
        for i, replacement in enumerate(config["replacements"]):
            if not isinstance(replacement, dict):
                self.logger.error(f"第 {i} 个替换项格式错误，应该是对象")
                return False
            
            if "old_text" not in replacement or "new_text" not in replacement:
                self.logger.error(f"第 {i} 个替换项缺少 old_text 或 new_text 字段")
                return False
            
            if not isinstance(replacement["old_text"], str) or not isinstance(replacement["new_text"], str):
                self.logger.error(f"第 {i} 个替换项的 old_text 和 new_text 应该是字符串")
                return False
        
        self.logger.info("配置文件验证通过")
        return True
    
    def get_replacements(self, config_name: str) -> List[Dict[str, str]]:
        """获取替换配置"""
        config = self.load_config(config_name)
        
        if not self.validate_config(config):
            raise ValueError("配置验证失败")
        
        return config["replacements"]
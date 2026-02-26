import os
import logging
from typing import Dict, Optional

class FontManager:
    def __init__(self, fonts_dir: str = "fonts"):
        self.fonts_dir = fonts_dir
        self.logger = logging.getLogger(__name__)
        self.loaded_fonts: Dict[str, str] = {}
    
    def get_font_path(self, fontname: str) -> Optional[str]:
        """获取字体文件路径"""
        font_file = os.path.join(self.fonts_dir, f"{fontname}.ttf")
        
        if os.path.exists(font_file):
            return font_file
        
        self.logger.warning(f"字体文件不存在: {font_file}")
        return None
    
    def load_font(self, fontname: str) -> Optional[str]:
        """加载字体"""
        if fontname in self.loaded_fonts:
            return self.loaded_fonts[fontname]
        
        font_path = self.get_font_path(fontname)
        if font_path:
            self.loaded_fonts[fontname] = font_path
            self.logger.info(f"成功加载字体: {fontname}")
            return font_path
        
        self.logger.warning(f"无法加载字体: {fontname}, 使用默认字体")
        return None
    
    def get_default_font(self) -> str:
        """获取默认字体"""
        return "Helvetica"
    
    def get_font_for_replacement(self, fontname: str) -> str:
        """获取替换用的字体"""
        font_path = self.load_font(fontname)
        
        if font_path:
            return fontname
        
        return self.get_default_font()
import fitz
import os
from typing import List, Dict, Tuple, Optional
import logging


class PDFProcessor:
    def __init__(self, fonts_dir: str = "fonts"):
        self.fonts_dir = fonts_dir
        self.logger = logging.getLogger(__name__)

    def load_pdf(self, pdf_path: str):
        try:
            return fitz.open(pdf_path)
        except Exception as e:
            self.logger.error(f"无法加载PDF文件 {pdf_path}: {e}")
            raise

    def find_text_with_style(self, page, text: str) -> List[Dict]:
        """查找文本并获取样式信息"""
        results = []
        text_instances = page.search_for(text)
        text_dict = page.get_text("dict")
        
        for inst in text_instances:
            style_info = None
            if "blocks" in text_dict:
                for block in text_dict["blocks"]:
                    if "lines" not in block:
                        continue
                    for line in block["lines"]:
                        for span in line["spans"]:
                            span_bbox = fitz.Rect(span["bbox"])
                            if span_bbox.intersects(inst) and text in span.get("text", ""):
                                style_info = {
                                    "fontname": span.get("font", "helv"),
                                    "fontsize": span.get("size", 12),
                                    "color": span.get("color", 0),
                                }
                                break
                        if style_info:
                            break
                    if style_info:
                        break
            
            if style_info:
                results.append({
                    "rect": inst,
                    "style": style_info
                })
        
        return results

    def process_replacements(self, doc, replacements: List[Dict]) -> int:
        """处理所有替换项"""
        total_replacements = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            all_replacements = []
            for replacement in replacements:
                old_text = replacement["old_text"]
                new_text = replacement["new_text"]
                items = self.find_text_with_style(page, old_text)
                
                for item in items:
                    all_replacements.append({
                        "rect": item["rect"],
                        "new_text": new_text,
                        "style": item["style"]
                    })
            
            if not all_replacements:
                continue
            
            for item in all_replacements:
                page.add_redact_annot(item["rect"], fill=(1, 1, 1))
            
            page.apply_redactions()
            
            for item in all_replacements:
                rect = item["rect"]
                style = item["style"]
                color_tuple = self._int_to_rgb(style["color"])
                
                page.insert_text(
                    (rect.x0, rect.y1),
                    item["new_text"],
                    fontname=style["fontname"],
                    fontsize=style["fontsize"],
                    color=color_tuple
                )
            
            total_replacements += len(all_replacements)
            self.logger.info(f"页面 {page_num}: 完成 {len(all_replacements)} 处替换")
        
        return total_replacements

    def _int_to_rgb(self, color_int: int) -> Tuple[float, float, float]:
        """将整数颜色值转换为RGB元组"""
        if isinstance(color_int, tuple):
            return color_int
        r = ((color_int >> 16) & 0xFF) / 255.0
        g = ((color_int >> 8) & 0xFF) / 255.0
        b = (color_int & 0xFF) / 255.0
        return (r, g, b)

    def save_pdf(self, doc, output_path: str):
        try:
            doc.save(output_path, garbage=4, deflate=True)
            doc.close()
        except Exception as e:
            self.logger.error(f"保存PDF失败: {e}")
            raise
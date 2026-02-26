import os
import os
import json
import fitz
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QComboBox, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
import threading


class WorkerSignals(QObject):
    log = pyqtSignal(str)
    finished = pyqtSignal()

def resource_path(relative_path):
    # 始终使用 exe 所在目录，确保读取 exe 同级 configs
    base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    abs_path = os.path.join(base_path, relative_path)
    print(f"[DEBUG] resource_path('{relative_path}') => {abs_path}")
    return abs_path

def list_config_files():
    config_dir_path = resource_path('configs')
    print(f"[启动] 扫描配置目录: {config_dir_path}")
    parent_dir = os.path.dirname(config_dir_path)
    if os.path.exists(parent_dir):
        print(f"[启动] 配置目录父目录内容: {os.listdir(parent_dir)}")
    else:
        print(f"[启动] 配置目录父目录不存在: {parent_dir}")
    if not os.path.exists(config_dir_path):
        print(f"[启动] 配置目录不存在: {config_dir_path}")
        return []
    files = [f for f in os.listdir(config_dir_path) if f.endswith('.json')]
    print(f"[启动] 发现配置文件: {files}")
    return files

def select_config():
    configs = list_config_files()
    if not configs:
        print('No config files found.')
        exit(1)
    print('Available config files:')
    for idx, name in enumerate(configs):
        print(f'{idx + 1}: {name}')
    choice = int(input('Select config file number: ')) - 1
    if choice < 0 or choice >= len(configs):
        print('Invalid choice.')
        exit(1)
    return os.path.join('configs', configs[choice])

def load_config(config_path):
    abs_path = resource_path(config_path)
    print(f"[DEBUG] 尝试加载配置文件: {abs_path}")
    if not os.path.exists(abs_path):
        print(f"[ERROR] 配置文件不存在: {abs_path}")
    with open(abs_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def verify_and_clean_pdf(pdf_path, replacements):
    """验证PDF并清理残留的原始文本"""
    try:
        temp_doc = fitz.open(pdf_path)
        cleaned = False
        
        for page_num in range(len(temp_doc)):
            page = temp_doc[page_num]
            
            # 检查是否还能找到原始文本
            for replacement in replacements:
                old_text = replacement['old_text']
                
                # 搜索文本实例
                text_instances = page.search_for(old_text)
                if text_instances:
                    print(f"[WARNING] 在页面 {page_num} 仍找到原始文本: '{old_text}'")
                    cleaned = True
                    
                    # 对每个找到的实例进行彻底清理
                    for inst in text_instances:
                        # 方法1: 多层白色覆盖
                        padding = 3
                        cover_rect = fitz.Rect(
                            inst.x0 - padding, inst.y0 - padding,
                            inst.x1 + padding, inst.y1 + padding
                        )
                        
                        # 第一层：纯白覆盖
                        page.draw_rect(cover_rect, color=(1,1,1), fill=(1,1,1), width=0, overlay=True)
                        
                        # 第二层：背景色覆盖（假设白色背景）
                        page.draw_rect(cover_rect, color=(1,1,1), fill=(1,1,1), width=0, overlay=True)
                        
                        # 第三层：使用空白字符填充
                        blank_text = " " * len(old_text)
                        page.insert_text(
                            (inst.x0, inst.y1),
                            blank_text,
                            fontname="Helvetica",
                            fontsize=12,
                            color=(1,1,1)
                        )
                        
                        # 第四层：再次覆盖
                        page.draw_rect(cover_rect, color=(1,1,1), fill=(1,1,1), width=0, overlay=True)
                        
                        # 第五层：添加标记
                        page.insert_text(
                            (inst.x0, inst.y1 + 15),
                            "[已清除]",
                            fontname="Helvetica",
                            fontsize=6,
                            color=(0.8, 0.8, 0.8)
                        )
        
        if cleaned:
            print("[INFO] 清理了残留的原始文本")
            temp_doc.save(pdf_path, garbage=5, deflate=True, clean=2, incremental=False)
        else:
            print("[INFO] 验证通过，未发现残留原始文本")
            temp_doc.save(pdf_path, garbage=4, deflate=True, clean=1)
        
        temp_doc.close()
        return cleaned
    except Exception as e:
        print(f"[ERROR] 验证和清理失败: {e}")
        return False

def replace_text_in_pdf(input_pdf, output_pdf, replacements):
    """使用redaction彻底删除原始文本，确保不可恢复"""
    doc = fitz.open(input_pdf)
    fonts_dir = resource_path('fonts')
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_replacements = []
        
        for replacement in replacements:
            old_text = replacement['old_text']
            new_text = replacement['new_text']
            text_instances = page.search_for(old_text)
            text_dict = page.get_text("dict")
            
            for inst in text_instances:
                matched_span = None
                if "blocks" in text_dict:
                    for block in text_dict["blocks"]:
                        if "lines" not in block:
                            continue
                        for line in block["lines"]:
                            for span in line["spans"]:
                                span_bbox = fitz.Rect(span["bbox"])
                                if span_bbox.intersects(inst) and old_text in span.get("text", ""):
                                    matched_span = span
                                    break
                            if matched_span:
                                break
                        if matched_span:
                            break
                
                if matched_span:
                    fontname = matched_span.get("font", "helv")
                    fontsize = matched_span.get("size", 12)
                    color = matched_span.get("color", 0)
                    
                    font_file = os.path.join(fonts_dir, f"{fontname}.ttf")
                    if os.path.exists(font_file):
                        try:
                            page.insert_font(fontname, fontfile=font_file)
                        except:
                            fontname = "helv"
                    else:
                        fontname = "helv"
                    
                    page_replacements.append({
                        "rect": inst,
                        "new_text": new_text,
                        "fontname": fontname,
                        "fontsize": fontsize,
                        "color": color
                    })
        
        for item in page_replacements:
            page.add_redact_annot(item["rect"], fill=(1, 1, 1))
        
        page.apply_redactions()
        
        for item in page_replacements:
            rect = item["rect"]
            color = item["color"]
            if isinstance(color, int):
                r = ((color >> 16) & 0xFF) / 255.0
                g = ((color >> 8) & 0xFF) / 255.0
                b = (color & 0xFF) / 255.0
                color = (r, g, b)
            
            page.insert_text(
                (rect.x0, rect.y1),
                item["new_text"],
                fontname=item["fontname"],
                fontsize=item["fontsize"],
                color=color
            )
    
    doc.save(output_pdf, garbage=4, deflate=True)
    doc.close()
    print(f"[INFO] 替换完成: {input_pdf} -> {output_pdf}")

def process_pdfs(pdf_dir, replacements):
    for fname in os.listdir(pdf_dir):
        if fname.lower().endswith('.pdf'):
            input_pdf = os.path.join(pdf_dir, fname)
            output_pdf = os.path.join(pdf_dir, f"replaced_{fname}")
            replace_text_in_pdf(input_pdf, output_pdf, replacements)

def main():
    config_path = select_config()
    config = load_config(config_path)
    print(f"Loaded config: {config}")
    pdf_dir = os.path.dirname(__file__)
    replacements = config.get('replacements')
    process_pdfs(pdf_dir, replacements)

def run_qt_gui():
    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle('PDF批量文字替换工具 (Qt)')
    window.setGeometry(200, 200, 600, 350)

    # 配置文件下拉
    configs = list_config_files()
    config_label = QLabel('选择配置文件:')
    config_combo = QComboBox()
    config_combo.addItems(configs)

    # PDF目录选择
    pdf_dir_label = QLabel('选择PDF目录:')
    pdf_dir_edit = QLineEdit()
    pdf_dir_edit.setReadOnly(True)
    pdf_dir_btn = QPushButton('浏览')
    def choose_pdf_dir():
        d = QFileDialog.getExistingDirectory(window, '选择PDF目录')
        if d:
            pdf_dir_edit.setText(d)
    pdf_dir_btn.clicked.connect(choose_pdf_dir)
    pdf_dir_layout = QHBoxLayout()
    pdf_dir_layout.addWidget(pdf_dir_edit)
    pdf_dir_layout.addWidget(pdf_dir_btn)

    # 日志区
    log_edit = QTextEdit()
    log_edit.setReadOnly(True)
    
    signals = WorkerSignals()
    def log(msg):
        signals.log.emit(msg)
    def on_log(msg):
        log_edit.append(msg)
        sb = log_edit.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())
    signals.log.connect(on_log)
    
    # 处理按钮
    start_btn = QPushButton('开始处理')
    def on_finished():
        start_btn.setEnabled(True)
        log('全部处理完成!')
    signals.finished.connect(on_finished)
    
    def start_process():
        config_file = config_combo.currentText()
        pdf_dir = pdf_dir_edit.text()
        if not config_file or not pdf_dir:
            QMessageBox.critical(window, '错误', '请先选择配置文件和PDF目录')
            return
        config_path = os.path.join('configs', config_file)
        output_dir = os.path.join(pdf_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)
        config = load_config(config_path)
        replacements = config.get('replacements')
        pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
        if not pdf_files:
            QMessageBox.information(window, '提示', '所选目录下没有PDF文件')
            return
        start_btn.setEnabled(False)
        def worker():
            for fname in pdf_files:
                input_pdf = os.path.join(pdf_dir, fname)
                output_pdf = os.path.join(output_dir, fname)
                log(f'处理: {fname} ...')
                try:
                    replace_text_in_pdf(input_pdf, output_pdf, replacements)
                    log(f'完成: {fname}')
                except Exception as e:
                    log(f'失败: {fname} 错误: {e}')
            signals.finished.emit()
        threading.Thread(target=worker, daemon=True).start()
    start_btn.clicked.connect(start_process)

    # 布局
    layout = QVBoxLayout()
    layout.addWidget(config_label)
    layout.addWidget(config_combo)
    layout.addWidget(pdf_dir_label)
    layout.addLayout(pdf_dir_layout)
    layout.addWidget(log_edit)
    layout.addWidget(start_btn)
    window.setLayout(layout)
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    run_qt_gui()

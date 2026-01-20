import os
import json
import fitz
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QComboBox, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QLineEdit
)
from PyQt5.QtCore import Qt
import threading

def resource_path(relative_path):
    """ Get the absolute path to the resource, works for both development and PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def list_config_files(config_dir):
    return [f for f in os.listdir(resource_path(config_dir)) if f.endswith('.json')]

def select_config(config_dir):
    configs = list_config_files(config_dir)
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
    return os.path.join(resource_path(config_dir), configs[choice])

def load_config(config_path):
    with open(resource_path(config_path), 'r', encoding='utf-8') as f:
        return json.load(f)

def replace_text_in_pdf(input_pdf, output_pdf, replacements):
    doc = fitz.open(input_pdf)
    fonts_dir = resource_path('fonts')
    # 收集所有待替换项（不分replacement顺序），并按y0从大到小排序，确保从下往上依次涂白替换
    all_replacements = []
    processed_bboxes = set()
    for replacement in replacements:
        old_text = replacement['old_text']
        new_text = replacement['new_text']
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_instances = page.search_for(old_text)
            text_dict = page.get_text("dict")
            for inst in text_instances:
                inst_tuple = (page_num, round(inst.x0, 2), round(inst.y0, 2), round(inst.x1, 2), round(inst.y1, 2))
                if inst_tuple in processed_bboxes:
                    continue
                # 取出该区域的原始文本，确保包含old_text才收集
                extracted_text = page.get_textbox(inst).strip()
                if old_text not in extracted_text:
                    continue
                processed_bboxes.add(inst_tuple)
                matched_span = None
                for block in text_dict["blocks"]:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                span_bbox = fitz.Rect(span["bbox"])
                                if span_bbox.intersects(inst):
                                    # 在span文本中查找old_text
                                    if old_text in span.get("text", ""):
                                        matched_span = span
                                        break
                            if matched_span:
                                break
                        if matched_span:
                            break
                    if matched_span:
                        break
                # 如果找到包含old_text的span就用它，否则用第一个intersect的span
                final_span = matched_span
                if not final_span:
                    # fallback: 取第一个intersect的span
                    for block in text_dict["blocks"]:
                        if "lines" in block:
                            for line in block["lines"]:
                                for span in line["spans"]:
                                    span_bbox = fitz.Rect(span["bbox"])
                                    if span_bbox.intersects(inst):
                                        final_span = span
                                        break
                                if final_span:
                                    break
                            if final_span:
                                break
                        if final_span:
                            break
                if final_span:
                    all_replacements.append((page_num, inst.x0, inst.y0, inst.x1, inst.y1, final_span, replacement))
                    print(f"[DEBUG] 收集替换: {old_text} -> {new_text} at page {page_num}, inst {inst}, 字号: {final_span.get('size')}, 字体: {final_span.get('font')}, span内容: {final_span.get('text')}, 原文: {extracted_text}")
    # 按页码、y0从大到小排序，确保从下往上依次替换
    all_replacements.sort(key=lambda x: (x[0], -x[2], -x[3]))
    # now apply
    for item in all_replacements:
        page_num, x0, y0, x1, y1, span, replacement = item
        inst = fitz.Rect(x0, y0, x1, y1)
        page = doc[page_num]
        old_text = replacement['old_text']
        new_text = replacement['new_text']
        fontname = span.get("font", "Helvetica")
        fontsize = span.get("size", 12)
        color = span.get("color", 0)
        font_file = os.path.join(fonts_dir, f"{fontname}.ttf")
        if os.path.exists(font_file):
            try:
                page.insert_font(fontname, fontfile=font_file)
            except Exception:
                pass
        else:
            fontname = "Helvetica"
        # 先画白色方框覆盖所有相关span
        text_dict = page.get_text("dict")
        spans_to_cover = []
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for s in line["spans"]:
                        span_bbox = fitz.Rect(s["bbox"])
                        if span_bbox.intersects(inst):
                            if old_text in s.get("text", "") or s.get("text", "").strip() in old_text:
                                page.draw_rect(span_bbox, color=(1,1,1), fill=(1,1,1))
                                spans_to_cover.append(s)
        # 只在第一个相关span插入新内容
        if spans_to_cover:
            s = spans_to_cover[0]
            span_bbox = fitz.Rect(s["bbox"])
            page.insert_text(
                (span_bbox.x0, span_bbox.y1),
                new_text,
                fontname=s.get("font", fontname),
                fontsize=s.get("size", fontsize),
                color=s.get("color", color)
            )
    doc.save(output_pdf)
    doc.close()
    print(f"[INFO] 替换完成: {input_pdf} -> {output_pdf}")

def process_pdfs(pdf_dir, replacements):
    for fname in os.listdir(pdf_dir):
        if fname.lower().endswith('.pdf'):
            input_pdf = os.path.join(pdf_dir, fname)
            output_pdf = os.path.join(pdf_dir, f"replaced_{fname}")
            replace_text_in_pdf(input_pdf, output_pdf, replacements)

def main():
    config_dir = 'configs'
    config_path = select_config(config_dir)
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
    config_dir = 'configs'
    configs = [f for f in os.listdir(resource_path(config_dir)) if f.endswith('.json')]
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
    def log(msg):
        log_edit.append(msg)
        log_edit.verticalScrollBar().setValue(log_edit.verticalScrollBar().maximum())

    # 处理按钮
    start_btn = QPushButton('开始处理')
    def start_process():
        config_file = config_combo.currentText()
        pdf_dir = pdf_dir_edit.text()
        if not config_file or not pdf_dir:
            QMessageBox.critical(window, '错误', '请先选择配置文件和PDF目录')
            return
        config_path = os.path.join(resource_path(config_dir), config_file)
        output_dir = os.path.join(pdf_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)
        config = load_config(config_path)
        replacements = config.get('replacements')
        pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
        if not pdf_files:
            QMessageBox.information(window, '提示', '所选目录下没有PDF文件')
            return
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
            log('全部处理完成!')
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

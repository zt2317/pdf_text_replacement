---
name: pdf-text-replacement
description: PDF批量文字替换工具 - 支持在PDF文件中替换指定文本，保持原有样式
license: MIT
compatibility: opencode
metadata:
  category: PDF处理
  tags: ["PDF", "文字替换", "批量处理", "GUI", "PyQt5"]
---

## What I do
- 批量替换PDF文件中的指定文本内容
- 保持原有文本的字体、字号和颜色等样式
- 支持通过配置文件管理多个替换规则
- 提供图形用户界面，操作简单直观
- 自动创建输出目录结构，支持多PDF文件同时处理

## When to use me
Use me when you need to replace text in multiple PDF files while preserving the original formatting. Perfect for:
- Updating company information in PDF documents
- Correcting typos or outdated information across multiple PDFs
- Standardizing text formats in a batch of documents
- Replacing temporary or placeholder text with final content

## Features
- ✨ 图形用户界面，操作简单直观
- 📄 支持配置文件批量管理替换规则
- 🎨 保持原有文本的字体、字号和颜色
- 📦 支持多PDF文件批量处理
- 📁 自动创建输出目录结构
- 📊 处理进度实时显示
- 🔤 支持自定义字体文件

## Requirements
- Python 3.6+
- Dependencies:
  - PyQt5
  - PyMuPDF
  - PyInstaller

## Usage

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Prepare configuration files
Create JSON configuration files in the `configs` directory:

```json
{
  "replacements": [
    {
      "old_text": "待替换文本",
      "new_text": "替换后的文本"
    }
  ]
}
```

### 3. Launch the application
```bash
python main.py
```

### 4. Operation steps
1. Select a configuration file from the dropdown menu
2. Choose the directory containing PDF files
3. Click "开始处理" to batch replace text in PDFs
4. View processed files in the `output` directory

## Configuration format

JSON configuration structure:
```json
{
  "replacements": [
    {
      "old_text": "xuena Hu",
      "new_text": "R&T LOGISTICS INC"
    },
    {
      "old_text": "1252 calbourne dr",
      "new_text": "4882 W. 145TH STREET"
    }
  ]
}
```

## Build executable
```bash
pyinstaller --onefile --windowed main.py
```

## Output results
- **Output directory**: `output/`
- **Naming convention**: Original filename, saved in output subdirectory
- **File format**: Same PDF format as input files

## Technical features
- Processes text from bottom to top to avoid coverage conflicts
- Supports custom font files (place in fonts directory)
- Automatic text area recognition for precise replacement
- Multi-threaded processing for smooth interface response
- Complete error handling and logging

## Notes
- Ensure PyMuPDF library is properly installed for PDF processing
- Tool automatically scans all `.json` files in `configs` directory as configuration options
- Be patient when processing large PDF files - interface shows real-time progress
- Custom font files must be `.ttf` format with filenames matching font names

## Directory structure
```
pdf_text_replacement/
├── main.py              # Main program file
├── requirements.txt     # Dependency list
├── configs/            # Configuration files directory
│   ├── example_config.json
│   └── xh_to_rt.json
├── fonts/              # Custom fonts directory
└── output/             # Output directory (auto-created)
```

## Troubleshooting
1. **Configuration files not found**: Ensure `configs` directory exists and contains valid JSON files
2. **Font mismatch**: Check if corresponding font files exist in the `fonts` directory
3. **PDF processing failed**: Check if PDF files are corrupted or password-protected
4. **Interface unresponsive**: Normal behavior when processing large files - please wait for completion
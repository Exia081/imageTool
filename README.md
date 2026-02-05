# 图片 / PDF 处理脚本

使用 python3 + Pillow / PyMuPDF 实现的命令行工具：

- **image_tool**：对图片添加文字/图片水印，以及按质量或尺寸压缩。
- **pdf_tool**：将 PDF 每页转为 JPG，可选在每张图上加文字水印。

## 安装

```bash
pip install -r requirements.txt
```

---

## image_tool：图片加水印与压缩

### 用法

```bash
python3 image_tool.py -i <输入文件或目录> [-o <输出路径>] [选项]
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `-i`, `--input` | 输入文件或目录（必填） |
| `-o`, `--output` | 输出文件或目录；不填时单文件输出为「原名_compressed.扩展名」，目录时为同目录 |
| `--quality` | JPEG/WebP 质量 1–100 |
| `--max-size` | 最长边不超过 N 像素（保持比例缩放） |
| `--watermark-text` | 文字水印内容 |
| `--watermark-image` | 水印图片路径 |
| `--watermark-mode` | 文字水印模式：`tiled`（45° 重复平铺整图，默认）/ `single`（单处水印） |
| `--watermark-opacity` | 文字水印透明度 0–1，默认 0.5（50%） |
| `--font` | 文字水印字体文件路径（.ttf/.ttc）；不指定时中文默认尝试微软雅黑等 CJK 字体 |
| `--font-size` | 文字水印字号，默认 36 |
| `--position` | 水印位置（仅 `single` 模式生效）：`top-left` / `top-right` / `bottom-left` / `bottom-right` / `center`，默认 `bottom-right` |
| `--overwrite` | 覆盖已存在的输出文件 |

### 示例

仅压缩，质量 85，输出到新文件：

```bash
python3 image_tool.py -i photo.jpg -o out.jpg --quality 85
```

缩放到最长边 1920 像素：

```bash
python3 image_tool.py -i photo.jpg -o out.jpg --max-size 1920
```

文字水印（默认 45° 平铺、50% 透明度；含中文时自动尝试微软雅黑）+ 压缩：

```bash
python3 image_tool.py -i photo.jpg -o out.jpg --quality 80 --watermark-text "© 2025"
```

单处文字水印（指定位置）：

```bash
python3 image_tool.py -i photo.jpg -o out.jpg --watermark-text "© 2025" --watermark-mode single --position bottom-right
```

指定中文字体（若系统未找到微软雅黑）：

```bash
python3 image_tool.py -i photo.jpg -o out.jpg --watermark-text "内部资料" --font /path/to/msyh.ttc
```

图片水印：

```bash
python3 image_tool.py -i photo.jpg -o out.jpg --watermark-image logo.png --position top-right
```

批量处理目录（输出到当前目录，文件名加 `_compressed`）：

```bash
python3 image_tool.py -i ./photos
```

批量处理并输出到指定目录：

```bash
python3 image_tool.py -i ./photos -o ./output
```

支持的图片格式：`.jpg`、`.jpeg`、`.png`、`.webp`。

---

## pdf_tool：PDF 转 JPG 与文字水印

将 PDF 每一页渲染为一张 JPG 图片，可选在每张图上加文字水印（与 image_tool 水印样式一致）。

### 用法

```bash
python3 pdf_tool.py -i <输入 PDF 文件> [-o <输出目录或文件名前缀>] [选项]
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `-i`, `--input` | 输入 PDF 文件（必填） |
| `-o`, `--output` | 输出目录或文件名前缀；不填时在输入同目录下生成。为目录时文件名为「PDF 名_page_1.jpg」等；为路径（如 `out/report`）时生成 `report_1.jpg`、`report_2.jpg` 等 |
| `--dpi` | 渲染 DPI，默认 150（影响清晰度与文件大小） |
| `--quality` | JPG 质量 1–100，默认 85 |
| `--watermark-text` | 文字水印内容（可选） |
| `--watermark-mode` | 文字水印模式：`tiled`（45° 平铺整图，默认）/ `single`（单处水印） |
| `--watermark-opacity` | 文字水印透明度 0–1，默认 0.8 |
| `--font` | 文字水印字体文件路径（.ttf/.ttc） |
| `--font-size` | 文字水印字号，默认 36 |
| `--position` | 水印位置（仅 `single` 模式生效）：`top-left` / `top-right` / `bottom-left` / `bottom-right` / `center`，默认 `bottom-right` |
| `--overwrite` | 覆盖已存在的输出文件 |

### 示例

仅将 PDF 转成 JPG，输出到指定目录：

```bash
python3 pdf_tool.py -i doc.pdf -o ./output
```

转 JPG 并加平铺文字水印：

```bash
python3 pdf_tool.py -i doc.pdf -o ./output --watermark-text "内部使用"
```

单处文字水印、右下角：

```bash
python3 pdf_tool.py -i doc.pdf -o ./output --watermark-text "机密" --watermark-mode single --position bottom-right
```

指定 DPI 与 JPG 质量：

```bash
python3 pdf_tool.py -i doc.pdf -o ./output --dpi 200 --quality 90
```

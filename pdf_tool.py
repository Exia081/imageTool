#!/usr/bin/env python3
"""
PDF 转 JPG 与文字水印脚本。
支持：将 PDF 每页渲染为 JPG，可选在每张图上加文字水印。
"""
import argparse
import sys
from pathlib import Path

try:
    import fitz
except ImportError:
    print("错误：未安装 pymupdf，请执行: pip install pymupdf", file=sys.stderr)
    sys.exit(1)

from PIL import Image

from image_tool import (
    POSITION_OPTIONS,
    WATERMARK_MODE_OPTIONS,
    apply_text_watermark,
    apply_text_watermark_tiled,
)


def pdf_pages_to_images(pdf_path: Path, dpi: int = 150) -> list[Image.Image]:
    """将 PDF 每一页渲染为 PIL Image（RGB）。"""
    doc = fitz.open(pdf_path)
    images = []
    try:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            images.append(img)
    finally:
        doc.close()
    return images


def resolve_output_paths(
    pdf_path: Path,
    output_arg: str | None,
    num_pages: int,
) -> tuple[Path, list[Path]]:
    """
    根据 -o 参数得到输出目录和每页输出文件路径列表。
    返回 (output_dir, [out_path_page1, out_path_page2, ...])。
    """
    stem = pdf_path.stem
    if output_arg is None:
        out_dir = pdf_path.parent
        base = stem
    else:
        p = Path(output_arg)
        if p.exists() and p.is_dir():
            out_dir = p
            base = stem
        else:
            out_dir = p.parent
            base = p.stem
            out_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for i in range(1, num_pages + 1):
        if num_pages == 1:
            paths.append(out_dir / f"{base}.jpg")
        else:
            paths.append(out_dir / f"{base}_page_{i}.jpg")
    return out_dir, paths


def process_pdf(
    pdf_path: Path,
    out_paths: list[Path],
    dpi: int = 150,
    quality: int = 85,
    watermark_text: str | None = None,
    position: str = "bottom-right",
    watermark_mode: str = "tiled",
    font_path: str | None = None,
    font_size: int = 36,
    watermark_opacity: float = 0.8,
    overwrite: bool = False,
) -> None:
    """将 PDF 转成 JPG，可选加文字水印。"""
    images = pdf_pages_to_images(pdf_path, dpi=dpi)
    if len(images) != len(out_paths):
        raise ValueError("页数与输出路径数量不一致")

    for img, out_path in zip(images, out_paths):
        if out_path.exists() and not overwrite:
            print(f"跳过（已存在）: {out_path}", file=sys.stderr)
            continue
        if watermark_text:
            if watermark_mode == "single":
                img = apply_text_watermark(
                    img,
                    text=watermark_text,
                    position=position,
                    font_path=font_path,
                    font_size=font_size,
                    opacity=watermark_opacity,
                    prefer_cjk=True,
                )
            else:
                img = apply_text_watermark_tiled(
                    img,
                    text=watermark_text,
                    font_path=font_path,
                    font_size=font_size,
                    opacity=watermark_opacity,
                    prefer_cjk=True,
                )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "JPEG", quality=quality)


def main() -> int:
    parser = argparse.ArgumentParser(description="PDF 转 JPG，可选加文字水印")
    parser.add_argument("-i", "--input", required=True, help="输入 PDF 文件")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="输出目录或输出文件名前缀（默认在输入同目录下生成）",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        metavar="N",
        help="渲染 DPI（默认 150）",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=85,
        metavar="1-100",
        help="JPG 质量 1–100（默认 85）",
    )
    parser.add_argument("--watermark-text", default=None, help="文字水印内容（可选）")
    parser.add_argument(
        "--watermark-mode",
        choices=WATERMARK_MODE_OPTIONS,
        default="tiled",
        help="文字水印模式：tiled=45度平铺，single=单处水印（默认 tiled）",
    )
    parser.add_argument(
        "--watermark-opacity",
        type=float,
        default=0.8,
        metavar="0-1",
        help="文字水印透明度 0–1（默认 0.8）",
    )
    parser.add_argument("--font", default=None, help="文字水印字体文件路径（.ttf/.ttc）")
    parser.add_argument(
        "--font-size",
        type=int,
        default=36,
        metavar="N",
        help="文字水印字号（默认 36）",
    )
    parser.add_argument(
        "--position",
        choices=POSITION_OPTIONS,
        default="bottom-right",
        help="水印位置（single 模式生效）",
    )
    parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的输出文件")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误：输入不存在: {input_path}", file=sys.stderr)
        return 1
    if not input_path.is_file():
        print(f"错误：输入不是文件: {input_path}", file=sys.stderr)
        return 1
    if input_path.suffix.lower() != ".pdf":
        print(f"错误：输入不是 PDF 文件: {input_path}", file=sys.stderr)
        return 1

    try:
        doc = fitz.open(input_path)
        num_pages = len(doc)
        doc.close()
    except Exception as e:
        print(f"错误：无法打开 PDF: {e}", file=sys.stderr)
        return 1

    out_dir, out_paths = resolve_output_paths(input_path, args.output, num_pages)
    process_pdf(
        input_path,
        out_paths,
        dpi=args.dpi,
        quality=args.quality,
        watermark_text=args.watermark_text,
        position=args.position,
        watermark_mode=args.watermark_mode,
        font_path=args.font,
        font_size=args.font_size,
        watermark_opacity=args.watermark_opacity,
        overwrite=args.overwrite,
    )
    for p in out_paths:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())

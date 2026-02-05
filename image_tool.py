#!/usr/bin/env python3
"""
图片加水印与压缩脚本。
支持：按质量/尺寸压缩，文字水印，图片水印。
"""
import argparse
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 支持的图片扩展名
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# 水印位置到 (x, y) 计算方式的映射：(对齐方式: 水平, 垂直)
# 实际坐标在贴图时按图片尺寸计算
POSITION_OPTIONS = ("top-left", "top-right", "bottom-left", "bottom-right", "center")
WATERMARK_MODE_OPTIONS = ("tiled", "single")


def get_output_path(input_path: Path, output_arg: str | None, is_dir: bool) -> Path | None:
    """根据输入和 output 参数得到输出路径。目录模式返回 None 表示用默认规则。"""
    if output_arg is not None:
        p = Path(output_arg)
        if is_dir and p.is_dir():
            return p
        if not is_dir:
            return p
        return p
    return None


def collect_inputs(input_path: Path) -> list[tuple[Path, Path]]:
    """
    收集 (输入文件, 输出文件) 列表。
    - 若 input_path 是文件：返回 [(input_path, default_output)]
    - 若 input_path 是目录：遍历目录下图片，输出为 default 同名加 _compressed 在输出目录
    """
    if input_path.is_file():
        if input_path.suffix.lower() not in IMAGE_EXTENSIONS:
            return []
        base = input_path.stem
        ext = input_path.suffix
        default_out = input_path.parent / f"{base}_compressed{ext}"
        return [(input_path, default_out)]
    if input_path.is_dir():
        pairs = []
        for p in sorted(input_path.iterdir()):
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                default_out = input_path / f"{p.stem}_compressed{p.suffix}"
                pairs.append((p, default_out))
        return pairs
    return []


def resize_if_needed(img: Image.Image, max_size: int | None) -> Image.Image:
    """若指定 max_size 则按比例缩放到最长边不超过 max_size。"""
    if max_size is None:
        return img
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return img


def _contains_cjk(text: str) -> bool:
    """判断文本是否包含 CJK（中日韩）字符。"""
    for ch in text:
        if (
            "\u4e00" <= ch <= "\u9fff"
            or "\u3400" <= ch <= "\u4dbf"
            or "\U00020000" <= ch <= "\U0002a6df"
        ):
            return True
    return False


def _load_truetype(path: str, size: int):
    """加载 TTF/TTC 字体，.ttc 使用 index=0。"""
    path_lower = path.lower()
    if path_lower.endswith(".ttc"):
        return ImageFont.truetype(path, size, index=0)
    return ImageFont.truetype(path, size)


def _get_font(
    size: int,
    font_path: str | None,
    prefer_cjk: bool = False,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """获取字体，优先 font_path，否则按 prefer_cjk 尝试微软雅黑/CJK 或西文，最后兜底 default。"""
    if font_path and os.path.isfile(font_path):
        return _load_truetype(font_path, size)
    # 若需中文，优先微软雅黑及常见 CJK
    if prefer_cjk:
        cjk_paths = [
            "C:\\Windows\\Fonts\\msyh.ttc",
            "C:\\Windows\\Fonts\\msyhbd.ttf",
            "/Library/Fonts/Microsoft/msyh.ttf",
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
            "/usr/share/fonts/truetype/msttcorefonts/Microsoft_YaHei.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        ]
        for name in cjk_paths:
            if os.path.isfile(name):
                return _load_truetype(name, size)
    # 西文回退
    for name in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
    ):
        if os.path.isfile(name):
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def _text_bbox(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> tuple[int, int, int, int]:
    """返回文字包围盒 (left, top, right, bottom)。"""
    return draw.textbbox(xy, text, font=font)


def apply_text_watermark(
    img: Image.Image,
    text: str,
    position: str,
    font_path: str | None = None,
    font_size: int = 36,
    fill: tuple[int, int, int] | tuple[int, int, int, int] | None = None,
    opacity: float = 0.5,
    prefer_cjk: bool = False,
) -> Image.Image:
    """在图片上绘制单处文字水印。"""
    if not text or position not in POSITION_OPTIONS:
        return img
    if fill is None:
        fill = (255, 255, 255, int(255 * opacity))
    elif len(fill) == 3:
        fill = (*fill, int(255 * opacity))
    else:
        fill = (*fill[:3], int(255 * opacity))
    original_mode = img.mode
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _get_font(font_size, font_path, prefer_cjk=prefer_cjk)
    bbox = _text_bbox(draw, (0, 0), text, font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    margin = 20
    w, h = img.size
    if position == "top-left":
        x, y = margin, margin
    elif position == "top-right":
        x, y = w - tw - margin, margin
    elif position == "bottom-left":
        x, y = margin, h - th - margin
    elif position == "bottom-right":
        x, y = w - tw - margin, h - th - margin
    else:
        x, y = (w - tw) // 2, (h - th) // 2
    draw.text((x, y), text, font=font, fill=fill)
    out = Image.alpha_composite(img, overlay)
    if original_mode != "RGBA":
        out = out.convert(original_mode)
    return out


def apply_text_watermark_tiled(
    img: Image.Image,
    text: str,
    font_path: str | None = None,
    font_size: int = 36,
    opacity: float = 0.8,
    prefer_cjk: bool = False,
    angle: float = 45.0,
    spacing_ratio: float = 1.5,
) -> Image.Image:
    """在图片上绘制 45 度重复平铺文字水印，覆盖整张图。"""
    if not text:
        return img
    alpha = int(255 * opacity)
    fill = (255, 255, 255, alpha)
    original_mode = img.mode
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    draw_temp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    font = _get_font(font_size, font_path, prefer_cjk=prefer_cjk)
    bbox = _text_bbox(draw_temp, (0, 0), text, font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    step_x = int(tw * spacing_ratio)
    step_y = int(th * spacing_ratio)
    # 瓦片：2x2 个文字 + 间距，使平铺后覆盖充分
    tile_w = step_x * 2
    tile_h = step_y * 2
    tile = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
    draw_tile = ImageDraw.Draw(tile)
    for row in range(2):
        for col in range(2):
            draw_tile.text((col * step_x, row * step_y), text, font=font, fill=fill)
    tile = tile.rotate(-angle, expand=True, resample=Image.Resampling.BICUBIC)
    tw_tile, th_tile = tile.size
    w, h = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    y = -th_tile
    while y < h + th_tile:
        x = -tw_tile
        while x < w + tw_tile:
            overlay.paste(tile, (x, y), tile)
            x += tw_tile
        y += th_tile
    out = Image.alpha_composite(img, overlay)
    if original_mode != "RGBA":
        out = out.convert(original_mode)
    return out


def apply_image_watermark(
    img: Image.Image,
    watermark_path: Path,
    position: str,
    scale: float = 0.2,
    opacity: float = 1.0,
) -> Image.Image:
    """在图片上粘贴图片水印。scale 为相对主图短边的比例，opacity 0~1。"""
    if position not in POSITION_OPTIONS:
        return img
    wm = Image.open(watermark_path).convert("RGBA")
    if opacity < 1.0:
        wm.putalpha(int(255 * opacity))
    # 按主图短边比例缩放水印
    min_side = min(img.size)
    target = max(24, int(min_side * scale))
    wm.thumbnail((target, target), Image.Resampling.LANCZOS)
    ww, wh = wm.size
    margin = 20
    w, h = img.size
    if position == "top-left":
        x, y = margin, margin
    elif position == "top-right":
        x, y = w - ww - margin, margin
    elif position == "bottom-left":
        x, y = margin, h - wh - margin
    elif position == "bottom-right":
        x, y = w - ww - margin, h - wh - margin
    else:
        x, y = (w - ww) // 2, (h - wh) // 2
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    img.paste(wm, (x, y), wm)
    return img


def save_image(img: Image.Image, out_path: Path, quality: int | None, fmt: str | None) -> None:
    """根据扩展名和 quality 保存图片。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ext = out_path.suffix.lower()
    if fmt:
        img.save(out_path, format=fmt, quality=quality or 85, optimize=True)
        return
    if ext in (".jpg", ".jpeg"):
        img_to_save = img.convert("RGB") if img.mode == "RGBA" else img
        img_to_save.save(out_path, "JPEG", quality=quality or 85, optimize=True)
    elif ext == ".webp":
        img.save(out_path, "WEBP", quality=quality or 85, optimize=True)
    else:
        img.save(out_path, optimize=True, compress_level=6)


def process_one(
    input_path: Path,
    output_path: Path,
    quality: int | None,
    max_size: int | None,
    watermark_text: str | None,
    watermark_image: Path | None,
    position: str,
    overwrite: bool,
    font_path: str | None = None,
    font_size: int = 36,
    watermark_mode: str = "tiled",
    watermark_opacity: float = 0.5,
) -> None:
    """处理单张图片：缩放 -> 水印 -> 保存。"""
    if not overwrite and output_path.exists():
        print(f"跳过（已存在）: {output_path}", file=sys.stderr)
        return
    img = Image.open(input_path).copy()
    img = resize_if_needed(img, max_size)
    if watermark_text:
        prefer_cjk = _contains_cjk(watermark_text)
        if watermark_mode == "tiled":
            img = apply_text_watermark_tiled(
                img,
                watermark_text,
                font_path=font_path,
                font_size=font_size,
                opacity=watermark_opacity,
                prefer_cjk=prefer_cjk,
            )
        else:
            img = apply_text_watermark(
                img,
                watermark_text,
                position,
                font_path=font_path,
                font_size=font_size,
                opacity=watermark_opacity,
                prefer_cjk=prefer_cjk,
            )
    if watermark_image and watermark_image.is_file():
        img = apply_image_watermark(img, watermark_image, position)
    save_image(img, output_path, quality, None)
    print(f"已输出: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="图片加水印与压缩")
    parser.add_argument("-i", "--input", required=True, help="输入文件或目录")
    parser.add_argument("-o", "--output", default=None, help="输出文件或目录（默认在原名加 _compressed）")
    parser.add_argument("--quality", type=int, default=None, metavar="1-100", help="JPEG/WebP 质量")
    parser.add_argument("--max-size", type=int, default=None, metavar="N", help="最长边不超过 N 像素")
    parser.add_argument("--watermark-text", default=None, help="文字水印内容")
    parser.add_argument("--watermark-image", default=None, help="水印图片路径")
    parser.add_argument(
        "--watermark-mode",
        choices=WATERMARK_MODE_OPTIONS,
        default="tiled",
        help="文字水印模式：tiled=45度重复平铺整图，single=单处水印（默认 tiled）",
    )
    parser.add_argument(
        "--watermark-opacity",
        type=float,
        default=0.8,
        metavar="0-1",
        help="文字水印透明度 0~1（默认 0.8）",
    )
    parser.add_argument("--font", default=None, help="文字水印字体文件路径（.ttf/.ttc）")
    parser.add_argument("--font-size", type=int, default=36, metavar="N", help="文字水印字号（默认 36）")
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
    is_dir = input_path.is_dir()
    output_arg = args.output
    if is_dir and output_arg is None:
        output_dir = input_path  # 批量时默认输出到同目录
    else:
        output_dir = Path(output_arg) if output_arg else input_path.parent

    pairs = collect_inputs(input_path)
    if not pairs:
        print("错误：未找到任何图片文件。", file=sys.stderr)
        return 1

    # 单文件且指定了 -o 时，用 -o 作为输出路径
    if not is_dir and output_arg:
        pairs = [(pairs[0][0], Path(output_arg))]

    output_dir_path = Path(output_arg) if output_arg else None
    for inp, default_out in pairs:
        if is_dir and output_dir_path is not None:
            output_dir_path.mkdir(parents=True, exist_ok=True)
            out_path = output_dir_path / f"{inp.stem}_compressed{inp.suffix}"
        else:
            out_path = default_out
        process_one(
            inp,
            out_path,
            quality=args.quality,
            max_size=args.max_size,
            watermark_text=args.watermark_text,
            watermark_image=Path(args.watermark_image) if args.watermark_image else None,
            position=args.position,
            overwrite=args.overwrite,
            font_path=args.font,
            font_size=args.font_size,
            watermark_mode=args.watermark_mode,
            watermark_opacity=args.watermark_opacity,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

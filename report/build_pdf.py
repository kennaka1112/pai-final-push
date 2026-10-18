#!/usr/bin/env python3
"""report.md から提出用のレポートPDFを作る。

Markdownの一部（見出し・段落・箇条書き・表・画像・コードブロック・水平線）だけを
解釈する簡易レンダラ。日本語はWindows同梱の游ゴシックを埋め込む。

  使い方: python build_pdf.py report.md 出力.pdf [--account アカウント名]
          [--repo-url URL] [--video-url URL]
"""
import argparse
import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, HRFlowable, Image,
                                ListFlowable, ListItem, PageTemplate,
                                Paragraph, Preformatted, Spacer, Table,
                                TableStyle)

FONT_DIR = r"C:\Windows\Fonts"
FONTS = [("JP", "YuGothM.ttc", 0), ("JP-Bold", "YuGothB.ttc", 0)]


def register_fonts():
    for name, filename, idx in FONTS:
        path = os.path.join(FONT_DIR, filename)
        if not os.path.exists(path):
            raise SystemExit(f"フォントが見つかりません: {path}")
        pdfmetrics.registerFont(TTFont(name, path, subfontIndex=idx))
    pdfmetrics.registerFontFamily("JP", normal="JP", bold="JP-Bold",
                                  italic="JP", boldItalic="JP-Bold")


def styles():
    base = dict(fontName="JP", leading=15.5, alignment=TA_LEFT,
                wordWrap="CJK", textColor=colors.HexColor("#1a1a1a"))
    return {
        "title": ParagraphStyle("title", fontName="JP-Bold", fontSize=18,
                                leading=25, spaceAfter=4, wordWrap="CJK",
                                textColor=colors.HexColor("#14213d")),
        "subtitle": ParagraphStyle("subtitle", fontName="JP", fontSize=9.5,
                                   leading=14, spaceAfter=12, wordWrap="CJK",
                                   textColor=colors.HexColor("#5a6472")),
        "h2": ParagraphStyle("h2", fontName="JP-Bold", fontSize=13, leading=19,
                             spaceBefore=14, spaceAfter=5, wordWrap="CJK",
                             textColor=colors.HexColor("#14213d")),
        "h3": ParagraphStyle("h3", fontName="JP-Bold", fontSize=11, leading=16,
                             spaceBefore=9, spaceAfter=3, wordWrap="CJK",
                             textColor=colors.HexColor("#28334a")),
        "body": ParagraphStyle("body", fontSize=9.5, spaceAfter=5, **base),
        "cell": ParagraphStyle("cell", fontSize=8.5, leading=12.5, **
                               {k: v for k, v in base.items() if k != "leading"}),
        "cellh": ParagraphStyle("cellh", fontName="JP-Bold", fontSize=8.5,
                                leading=12.5, wordWrap="CJK",
                                textColor=colors.HexColor("#14213d")),
        "code": ParagraphStyle("code", fontName="JP", fontSize=8.5,
                               leading=13, textColor=colors.HexColor("#28334a"),
                               backColor=colors.HexColor("#f1f3f7"),
                               borderPadding=6, leftIndent=2, rightIndent=2),
        "caption": ParagraphStyle("caption", fontName="JP", fontSize=8.5,
                                  leading=12, spaceAfter=8, wordWrap="CJK",
                                  textColor=colors.HexColor("#5a6472")),
    }


def inline(text):
    """**強調** と `コード` と [text](url) を Paragraph のマークアップへ。"""
    text = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r'<font name="JP-Bold">\1</font>', text)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier" size="8.5">\1</font>', text)
    return text


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def build_table(rows, st, width):
    head, body = rows[0], rows[1:]
    data = [[Paragraph(inline(c), st["cellh"]) for c in head]]
    data += [[Paragraph(inline(c), st["cell"]) for c in r] for r in body]
    ncol = len(head)
    # 1列目をやや広く、残りを均等に
    if ncol >= 3:
        w = [width * 0.28] + [width * 0.72 / (ncol - 1)] * (ncol - 1)
    else:
        w = [width / ncol] * ncol
    t = Table(data, colWidths=w, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef1f6")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor("#8d99ae")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c8cedb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def parse(md, st, width, base_dir):
    out = []
    lines = md.split("\n")
    i = 0
    first_h1 = True
    while i < len(lines):
        ln = lines[i]

        if not ln.strip():
            i += 1
            continue

        if ln.startswith("```"):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append(Preformatted("\n".join(buf), st["code"]))
            out.append(Spacer(1, 5))
            continue

        if ln.startswith("# "):
            out.append(Paragraph(inline(ln[2:]), st["title"] if first_h1 else st["h2"]))
            first_h1 = False
            i += 1
            continue
        if ln.startswith("## "):
            out.append(Paragraph(inline(ln[3:]), st["h2"]))
            i += 1
            continue
        if ln.startswith("### "):
            out.append(Paragraph(inline(ln[4:]), st["h3"]))
            i += 1
            continue

        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", ln)
        if m:
            caption, src = m.group(1), m.group(2)
            path = os.path.normpath(os.path.join(base_dir, src))
            if os.path.exists(path):
                from reportlab.lib.utils import ImageReader
                iw, ih = ImageReader(path).getSize()
                w = min(width, 150 * mm)
                out.append(Image(path, width=w, height=w * ih / iw))
                if caption:
                    out.append(Spacer(1, 3))
                    out.append(Paragraph(inline(caption), st["caption"]))
            i += 1
            continue

        if ln.strip() in ("---", "***"):
            out.append(Spacer(1, 4))
            out.append(HRFlowable(width="100%", thickness=0.6,
                                  color=colors.HexColor("#c8cedb")))
            out.append(Spacer(1, 6))
            i += 1
            continue

        if ln.lstrip().startswith("|") and i + 1 < len(lines) and \
                re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            rows = [split_row(ln)]
            i += 2
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            out.append(build_table(rows, st, width))
            out.append(Spacer(1, 8))
            continue

        if re.match(r"^\s*\d+\. ", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\. ", lines[i]):
                text = re.sub(r"^\s*\d+\. ", "", lines[i])
                i += 1
                while i < len(lines) and lines[i].startswith("   ") and                         not re.match(r"^\s*\d+\. ", lines[i]):
                    text += " " + lines[i].strip()
                    i += 1
                items.append(ListItem(Paragraph(inline(text), st["body"]),
                                      leftIndent=16))
            out.append(ListFlowable(items, bulletType="1", bulletFormat="%s.",
                                    bulletFontName="JP", bulletFontSize=9,
                                    leftIndent=16))
            out.append(Spacer(1, 4))
            continue

        if re.match(r"^\s*[-*] ", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*] ", lines[i]):
                text = re.sub(r"^\s*[-*] ", "", lines[i])
                i += 1
                # 続く字下げ行は同じ項目に連結する
                while i < len(lines) and lines[i].startswith("  ") and \
                        not re.match(r"^\s*[-*] ", lines[i]):
                    text += " " + lines[i].strip()
                    i += 1
                items.append(ListItem(Paragraph(inline(text), st["body"]),
                                      leftIndent=12))
            out.append(ListFlowable(items, bulletType="bullet", start="•",
                                    bulletFontName="JP", bulletFontSize=8,
                                    leftIndent=12))
            out.append(Spacer(1, 4))
            continue

        # 通常の段落（空行まで連結）
        buf = [ln.strip()]
        i += 1
        while i < len(lines) and lines[i].strip() and \
                not re.match(r"^(#|\||```|!\[|\s*[-*] |---)", lines[i]):
            buf.append(lines[i].strip())
            i += 1
        out.append(Paragraph(inline("".join(buf)), st["body"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--account", default="")
    ap.add_argument("--repo-url", default="")
    ap.add_argument("--video-url", default="")
    args = ap.parse_args()

    md = open(args.src, encoding="utf-8").read()
    md = md.replace("__ACCOUNT__", args.account or "（アカウント名）")
    md = md.replace("__REPO_URL__", args.repo_url or "（提出時に記載）")
    md = md.replace("__VIDEO_URL__", args.video_url or "（提出時に記載）")

    register_fonts()
    st = styles()

    doc = BaseDocTemplate(args.dst, pagesize=A4,
                          leftMargin=20 * mm, rightMargin=20 * mm,
                          topMargin=18 * mm, bottomMargin=18 * mm,
                          title="PAI最終課題 説明資料", author=args.account or "")
    width = doc.width

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont("JP", 8)
        canvas.setFillColor(colors.HexColor("#8d99ae"))
        canvas.drawCentredString(A4[0] / 2, 10 * mm, str(canvas.getPageNumber()))
        canvas.restoreState()

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="n")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=footer)])

    story = parse(md, st, width, os.path.dirname(os.path.abspath(args.src)))
    # 1行目のサブタイトル行だけ小さく見せる
    doc.build(story)
    print(f"saved: {args.dst}")


main()

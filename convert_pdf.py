#!/usr/bin/env python3
"""
PDF 파일을 마크다운(.md) 또는 텍스트(.txt) 파일로 변환하는 스크립트
"""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("pdfplumber가 설치되지 않았습니다. 설치 중...")
    import subprocess
    subprocess.check_call(["pip", "install", "pdfplumber"])
    import pdfplumber


def convert_pdf_to_text(pdf_path: Path, output_path: Path | None = None) -> None:
    """PDF 파일을 텍스트로 변환한다."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    print(f"PDF 변환 중: {pdf_path.name}...")

    text_content = []
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"총 {total_pages}페이지 발견")

        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text:
                text_content.append(f"## 페이지 {page_num}\n\n{text}\n")
            if page_num % 10 == 0:
                print(f"진행 중... {page_num}/{total_pages} 페이지")

    full_text = "\n".join(text_content)

    # 출력 경로 결정
    if output_path is None:
        output_path = pdf_path.parent / f"{pdf_path.stem}.md"

    # 파일 저장
    output_path.write_text(full_text, encoding="utf-8")
    print(f"✅ 변환 완료: {output_path}")
    print(f"   총 {len(full_text)} 문자 추출됨")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PDF 파일을 텍스트/마크다운으로 변환"
    )
    parser.add_argument(
        "pdf_file",
        type=Path,
        help="변환할 PDF 파일 경로",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="출력 파일 경로 (기본: PDF와 같은 이름의 .md 파일)",
    )
    parser.add_argument(
        "--format",
        choices=["md", "txt"],
        default="md",
        help="출력 형식 (기본: md)",
    )

    args = parser.parse_args()

    # 출력 경로 설정
    output_path = args.output
    if output_path is None:
        if args.format == "md":
            output_path = args.pdf_file.parent / f"{args.pdf_file.stem}.md"
        else:
            output_path = args.pdf_file.parent / f"{args.pdf_file.stem}.txt"

    try:
        convert_pdf_to_text(args.pdf_file, output_path)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())


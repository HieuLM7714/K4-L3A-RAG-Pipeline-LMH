"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX.
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại.

Cài đặt:
    Dependency MarkItDown đã được khai báo trong pyproject.toml.
    
-> Hoặc dùng công cụ nào bạn quen khác Markitdown
"""

from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def convert_legal_docs() -> None:
    """Convert PDF/DOCX vào standardized/legal."""
    import pypdf

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in legal_dir.iterdir():
        if path.name.startswith("."):
            continue
        if path.suffix.lower() == ".pdf":
            try:
                reader = pypdf.PdfReader(str(path))
                pages_text = []
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        pages_text.append(text.strip())
                full_text = "\n\n".join(pages_text)
                
                title = path.stem.replace("_", " ").title()
                header = f"# {title}\n\n**Source:** {path.name}\n\n**Type:** legal\n\n---\n\n"
                output_file = output_dir / f"{path.stem}.md"
                output_file.write_text(header + full_text, encoding="utf-8")
                print(f"Converted legal PDF: {output_file.name} ({len(full_text)} chars)")
            except Exception as err:
                print(f"Error converting {path.name}: {err}")
                raise err


def convert_news_articles() -> None:
    """Convert JSON vào standardized/news."""
    import json

    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in news_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            header = (
                f"# {data['title']}\n\n"
                f"**Source:** {data['url']}\n\n"
                f"**Crawled:** {data['date_crawled']}\n\n---\n\n"
            )
            output_file = output_dir / f"{path.stem}.md"
            full_content = header + data.get("content_markdown", "")
            output_file.write_text(full_content, encoding="utf-8")
            print(f"Converted news article: {output_file.name} ({len(full_content)} chars)")
        except Exception as err:
            print(f"Error converting {path.name}: {err}")
            raise err



def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()

"""
Task 2 — Crawl bài viết/thông báo.

Hướng dẫn:
    1. Điền tối thiểu 5 URL công khai vào ARTICLE_URLS.
    2. Crawl từng URL bằng Crawl4AI.
    3. Lưu mỗi bài thành một JSON trong data/landing/news/.
    4. Giữ đủ url, title, date_crawled và content_markdown.

Cài browser trước khi chạy:
    python -m playwright install chromium
    
-> Dùng Firecrawl or bất cứ công cụ nào bạn quen    
"""

import asyncio
import json
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    "https://huongdan.ktxhcm.edu.vn/huong-dan/tan-sinh-vien",
    "https://huongdan.ktxhcm.edu.vn/huong-dan/hd-tra-cuu-bhyt",
    "https://huongdan.ktxhcm.edu.vn/huong-dan/huong-dan-thuc-hien-dang-ky-hoat-dong",
    "https://huongdan.ktxhcm.edu.vn/huong-dan/huong-dan-khao-sat",
    "https://huongdan.ktxhcm.edu.vn/huong-dan/huong-dan-tra-phong-menu",
]


def html_to_markdown(html_element) -> str:
    """Chuyển đổi DOM HTML thành Markdown đơn giản, sạch sẽ."""
    for tag in html_element(["script", "style", "nav", "footer", "header", "svg"]):
        tag.decompose()

    lines = []
    for elem in html_element.find_all(["h1", "h2", "h3", "h4", "p", "li", "tr"]):
        text = elem.get_text(separator=" ", strip=True)
        if not text:
            continue
        if elem.name == "h1":
            lines.append(f"# {text}\n")
        elif elem.name == "h2":
            lines.append(f"## {text}\n")
        elif elem.name == "h3":
            lines.append(f"### {text}\n")
        elif elem.name == "h4":
            lines.append(f"#### {text}\n")
        elif elem.name == "li":
            lines.append(f"- {text}")
        elif elem.name == "tr":
            cells = [c.get_text(strip=True) for c in elem.find_all(["td", "th"])]
            if cells:
                lines.append(" | ".join(cells))
        else:
            lines.append(f"{text}\n")

    # Loại bỏ dòng trùng lặp liên tiếp
    result = []
    last_line = None
    for line in lines:
        if line != last_line:
            result.append(line)
            last_line = line
    return "\n".join(result)


async def crawl_article(url: str) -> dict:
    from datetime import datetime
    import requests
    import urllib3
    from bs4 import BeautifulSoup

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers, verify=False, timeout=20)
    response.encoding = "utf-8"
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Tìm title
    title_tag = soup.find("h2", {"itemprop": "name"}) or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Thông tin hướng dẫn KTX"
    if " - " in title:
        title = title.split(" - ")[0].strip()

    # Tìm body
    article_body = soup.find("div", {"itemprop": "articleBody"}) or soup.find("div", class_="item-page") or soup.find("body")
    content_markdown = html_to_markdown(article_body) if article_body else soup.get_text(strip=True)

    return {
        "url": url,
        "title": title,
        "date_crawled": datetime.now().isoformat(),
        "content_markdown": content_markdown,
    }



async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for index, url in enumerate(ARTICLE_URLS, 1):
        try:
            article = await crawl_article(url)
            output = DATA_DIR / f"article_{index:02d}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved: {output}")
        except Exception as error:
            print(f"Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())

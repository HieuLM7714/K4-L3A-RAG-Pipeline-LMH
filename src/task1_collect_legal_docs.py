"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Hướng dẫn:
    1. Chọn chủ đề của nhóm.
    2. Tìm tối thiểu 3 tài liệu PDF/DOCX từ nguồn công khai.
    3. Lưu file gốc vào data/landing/legal/.
    4. Đặt tên không dấu và thể hiện đúng nội dung.

Ví dụ tài liệu: học phí, học bổng, ký túc xá, quy trình đăng ký.
Nếu website chặn crawler, hãy chọn nguồn công khai khác; không vượt WAF.
"""

from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải ít nhất 3 PDF/DOCX từ nguồn công khai."""
    import requests
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    sources = {
        "quy_dinh_danh_gia_ren_luyen_ktx.pdf": "https://drive.usercontent.google.com/download?id=1eDziLilYXWPDhSKKpHRKsBEznZ7lVY1C&export=download",
        "quy_che_dao_tao_dai_hoc_dhqghcm.pdf": "https://daa.uit.edu.vn/sites/daa/files/202309/790-qd-dhcntt_28-9-22_quy_che_dao_tao.pdf",
        "quy_che_dao_tao_dai_hoc_hcmue.pdf": "https://ctsv.hcmue.edu.vn/storage/files/quyet-dinh-ban-hanh-quy-che-dao-tao-trinh-do-dai-hoc-tai-truong-dai-hoc-su-pham-thanh-pho-ho-chi-minh-ap-dung-tu-khoa-tuyen-sinh-2021-tro-ve-sau.pdf",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for filename, url in sources.items():
        file_path = DATA_DIR / filename
        if file_path.exists() and file_path.stat().st_size > 1024:
            print(f"Already exists: {filename} ({file_path.stat().st_size} bytes)")
            continue

        print(f"Downloading {filename} from {url}...")
        try:
            response = requests.get(url, headers=headers, timeout=60, verify=False, stream=True)
            response.raise_for_status()
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
            print(f"Saved: {file_path} ({file_path.stat().st_size} bytes)")
        except Exception as err:
            print(f"Failed to download {filename}: {err}")
            raise err


if __name__ == "__main__":
    setup_directory()
    download_documents()


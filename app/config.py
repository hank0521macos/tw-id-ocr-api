import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Google Drive
GOOGLE_DRIVE_FOLDER_ID = os.getenv(
    "GOOGLE_DRIVE_FOLDER_ID", "1ev22-d-ZC3CnDl0NANzYeWuKi3CgUcxP"
)

# Service Account 認證
# 優先用 GOOGLE_SERVICE_ACCOUNT_JSON 環境變數（JSON 字串，適合 Railway 等雲端部署）
# 其次用 GOOGLE_SERVICE_ACCOUNT_FILE 環境變數（檔案路徑，適合本地開發）
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    str(BASE_DIR / "nchucems-1761097035404-fbe46545f56f.json"),
)

# 暫存目錄（下載圖片用，預設專案目錄下的 downloads/）
TEMP_DIR = Path(os.getenv("TEMP_DIR", str(BASE_DIR / "downloads")))
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# 下載目錄（改用 TEMP_DIR）
DOWNLOAD_DIR = TEMP_DIR

# 排程間隔（分鐘）
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", "10"))

# Database
# "postgresql://postgres:1234@localhost:5433/postgres"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://railway:a81leynywszzo5edkae8v0pgyzxwb8zl@yamanote.proxy.rlwy.net:55822/railway",
)

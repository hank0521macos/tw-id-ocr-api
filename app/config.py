import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Google Drive
GOOGLE_DRIVE_FOLDER_ID = os.getenv(
    "GOOGLE_DRIVE_FOLDER_ID", "1ev22-d-ZC3CnDl0NANzYeWuKi3CgUcxP"
)

# Service Account 認證（hard coded）
GOOGLE_SERVICE_ACCOUNT_INFO = {
    "type": "service_account",
    "project_id": "nchucems-1761097035404",
    "private_key_id": "fbe46545f56fd0d46c4b61eeeb918d1a95336d5c",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDaDMH1MMXgJ6G6\n2WorFcszxxay1nZhjbPb8IS9aFsXDJcZgGqaf0XofxxxCq5Cx9ch/7zWFc6w1dRB\nHLPVOLpltzzVUkhsvLbY0d50x9geiv8vu2Epj+fPOzQsVBSdSM8pEyRtFNRDgRw/\no4Vrg+O4wQNcXmd5ojsnaSQUcWxNbyhJ7lKghKPIqv6OduZNn828sJU3DYv53giT\nHo5+OSRPFiYiGEzlUu1i9RJrCcz7y8632PZIYlibA3CIOL6Zw/bLZbD7oHyvrLTW\nButC0TdcnSWtxr5ONtsRRPpeWMjQUPakLfzuX9jhGOojJEPOqJaaVsB7whKUHlF2\nUthhYj5HAgMBAAECggEABt2S99TmzhWBXqA82wlvIfy5Rr1A8fZjvN+YVlxkTdf8\nI/XqpV2vhlAGRbrn3LttFyl1uSnrnZ7F9ZzhPqvwFobL+A2EsUPJ4A7Pmc63C9Ml\nkMuuFgBtdJVxIZouIfuqZikvou2ed1en24sbBtUaxPTy1aQ1TtugUC/bznb5yYBR\nG/+R634b54hhtw06IUj031GcC0APwtPbrQqMPgqKP3nGWnipyugkhSisZP2N41aT\nw+VTFY9JaYe96CmT5Rn2N+EVWEYz8VL9O6GJgt/0O2cKlTYqiUfqvMftOIIcchsE\nLjuhEhsATOoV8VUx7c+ZYTBrlvmhE7WQykp1YeGVtQKBgQDt9nVNhvCJd5R6Eu0b\nIgOR2qjglX6kgklJ4ha2UzS36HXn4pte3HYIMTX9uZU5OiHha2nNWJcE+Ktkl5am\n/gRriR5cCgyXbwJTCr8+btNVENQT0MTsN6nGe1jYqlw9JcnIvAlSylzDM56Ama9F\nRl1eAdojj945eGt4siMM1tkUDQKBgQDqk+ZzsU029Q+p1U25vP/F/aLMh72Muu5w\nyy4FIQ6vRJGAR6yJWbJZ9dzpMIARYbT0nxwaf3kT47R63MkKT8dR9mC8jWR6Lz5R\nV0+4r9UN+7tsxMjIqn/te1pcFPYJv1AfbDrVeIz9fwgLseJCdICq8bYkiH1t4KC7\n4MB9ppPiowKBgHCjzxbpnwaTMhcuykmjqijqZjIY0Z+xhFuSx8l6TWQYh2dCXuVi\nWgS6tqHprPcvy0XXAHgRTTsvMoIlN0zIxPLaLyLGJvuvslv4pFo7P5Huq1TN58kg\n+B5Z2M6Gpa7UKlX4nDkyTQKhdo/NL6gNDLkpC0b2HOz7UXQKbojvUkYpAoGBAMOh\nlQ/nTf4HYojA25GLjcQRQzRQAETdoP1wdXDRoO2Kwc25+KqTo6pi4VmYmTXlxoQ8\nLbPrm4562ImemAuBfTldwE9/m8xKmi48IsBj48tFpYmQk+LGTuo/dZxV3ttCMhAC\nsw5U+0BuMMeQEqJZhvUJoF3XdsOsEmCdj+s6gRsBAoGBAMxLNgU9iHLA8kJPuUFr\ntoYody3nDYP/aYsofqfpCm6kUMGq42TFnmq9OAQTEcF5OKZ0XSg1KIBk0NRomlgM\nzv+AU4iwIMpxOD5EB7tnV/+qGRUlNiJtR2gTz+HgnZ90vTRMp++fwe8ZcfSyNAfU\nA6039jrMFnKspxv8xshrkeIy\n-----END PRIVATE KEY-----\n",
    "client_email": "drive-bot@nchucems-1761097035404.iam.gserviceaccount.com",
    "client_id": "116784582491069771688",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/drive-bot%40nchucems-1761097035404.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com",
}

# 暫存目錄（下載圖片用，預設專案目錄下的 downloads/）
TEMP_DIR = Path(os.getenv("TEMP_DIR", str(BASE_DIR / "downloads")))
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# 下載目錄（改用 TEMP_DIR）
DOWNLOAD_DIR = TEMP_DIR

# 排程間隔（分鐘）
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", "10"))

# Database
# "postgresql://railway:a81leynywszzo5edkae8v0pgyzxwb8zl@yamanote.proxy.rlwy.net:55822/railway"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://railway:a81leynywszzo5edkae8v0pgyzxwb8zl@yamanote.proxy.rlwy.net:55822/railway",
)

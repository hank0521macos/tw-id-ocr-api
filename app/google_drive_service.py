import logging
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.config import (
    GOOGLE_SERVICE_ACCOUNT_INFO,
    GOOGLE_DRIVE_FOLDER_ID,
)

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# 身分證圖片關鍵字
ID_CARD_KEYWORDS = ["身分證正面", "身分證反面"]


class GoogleDriveService:
    def __init__(self):
        self.service = None

    def authenticate(self):
        """Service Account 認證，從 hard coded dict 讀取"""
        logger.info("載入 Service Account 認證...")
        creds = service_account.Credentials.from_service_account_info(
            GOOGLE_SERVICE_ACCOUNT_INFO, scopes=SCOPES
        )
        self.service = build("drive", "v3", credentials=creds)
        logger.info("Google Drive API 連線成功")

    def _ensure_authenticated(self):
        if not self.service:
            self.authenticate()

    def list_folders(self, parent_id: str) -> list[dict]:
        """列出指定目錄下的所有子資料夾"""
        self._ensure_authenticated()
        query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = (
            self.service.files()
            .list(q=query, fields="files(id, name)", pageSize=1000)
            .execute()
        )
        folders = results.get("files", [])
        logger.info(f"資料夾 {parent_id} 下找到 {len(folders)} 個子資料夾")
        return folders

    def list_id_card_images(self, folder_id: str) -> list[dict]:
        """列出資料夾中的身分證圖片"""
        self._ensure_authenticated()
        query = (
            f"'{folder_id}' in parents "
            f"and mimeType contains 'image/' "
            f"and trashed=false"
        )
        results = (
            self.service.files()
            .list(
                q=query,
                fields="files(id, name, modifiedTime, mimeType)",
                pageSize=1000,
            )
            .execute()
        )
        all_files = results.get("files", [])

        # 篩選含身分證關鍵字的圖片
        id_card_files = [
            f for f in all_files
            if any(kw in f["name"] for kw in ID_CARD_KEYWORDS)
        ]
        return id_card_files

    def download_file(self, file_id: str, dest_path: Path) -> Path:
        """下載檔案到指定路徑"""
        self._ensure_authenticated()
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        request = self.service.files().get_media(fileId=file_id)
        with open(dest_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        logger.info(f"已下載: {dest_path}")
        return dest_path

    def scan_all_id_cards(self) -> list[dict]:
        """
        掃描 Drive 資料夾，回傳所有身分證圖片的 metadata（不下載）

        回傳：
        [{"file_id", "file_name", "modified_time", "store_name", "side", "business_folder", "person_folder"}]
        """
        self._ensure_authenticated()
        logger.info(f"開始掃描 Google Drive 資料夾: {GOOGLE_DRIVE_FOLDER_ID}")
        results = []

        # 第一層：業務目錄
        business_folders = self.list_folders(GOOGLE_DRIVE_FOLDER_ID)

        for biz_folder in business_folders:
            biz_name = biz_folder["name"]
            logger.info(f"掃描業務目錄: {biz_name}")

            # 第二層：入駐(人名)-身分證正、反面、門牌
            person_folders = self.list_folders(biz_folder["id"])

            for person_folder in person_folders:
                person_name = person_folder["name"]

                if "身分證" not in person_name:
                    continue

                logger.info(f"  掃描人員資料夾: {person_name}")
                images = self.list_id_card_images(person_folder["id"])

                for img in images:
                    file_name = img["name"]
                    # 從檔名解析店名和正反面
                    # 例: "小韓室飯捲-桃園大竹店_身分證正面.jpg"
                    store_name = file_name.rsplit("_", 1)[0] if "_" in file_name else file_name
                    side = "front" if "身分證正面" in file_name else "back"

                    results.append({
                        "file_id": img["id"],
                        "file_name": file_name,
                        "modified_time": img["modifiedTime"],
                        "store_name": store_name,
                        "side": side,
                        "business_folder": biz_name,
                        "person_folder": person_name,
                    })

        logger.info(f"掃描完成，共找到 {len(results)} 張身分證圖片")
        return results

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.models import StandardResponse
from app.database import init_db
from app.routes.ocr import router as ocr_router
from app.routes.stores import router as stores_router
from app.routes.lookup import router as lookup_router
from app.google_drive_service import GoogleDriveService
from app.log_handler import memory_handler

# 設定日誌：stdout + memory buffer
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# 把 memory handler 掛到 root logger，所有 app log 都會被捕獲
logging.getLogger().addHandler(memory_handler)
logger = logging.getLogger(__name__)


drive_service = GoogleDriveService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("初始化資料庫...")
    init_db()
    logger.info("恢復卡住的 task...")
    from app.ocr_processor import recover_stale_tasks
    recover_stale_tasks()
    yield


app = FastAPI(
    title="Taiwan ID Card OCR API",
    description="Upload Taiwan ID card image to extract ID number and name",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ocr_router)
app.include_router(stores_router)
app.include_router(lookup_router)


@app.get("/health", response_model=StandardResponse, tags=["Health"])
async def health_check():
    return StandardResponse(
        data={"status": "ok", "service": "tw-id-ocr", "version": "1.0.0"},
        success=True,
        message="Service is running.",
    )


@app.get("/api/drive/list", response_model=StandardResponse, tags=["Google Drive"])
async def list_drive_folders():
    """列出 Google Drive 資料夾結構（測試連線用）"""
    try:
        if not drive_service.service:
            drive_service.authenticate()

        from app.config import GOOGLE_DRIVE_FOLDER_ID
        tree = []
        biz_folders = drive_service.list_folders(GOOGLE_DRIVE_FOLDER_ID)
        for biz in biz_folders:
            sub_folders = drive_service.list_folders(biz["id"])
            tree.append({
                "name": biz["name"],
                "id": biz["id"],
                "sub_folders": [{"name": s["name"], "id": s["id"]} for s in sub_folders],
            })

        return StandardResponse(
            data=tree,
            success=True,
            message=f"Found {len(biz_folders)} business folders.",
        )
    except Exception as e:
        logger.error(f"列出目錄失敗: {e}", exc_info=True)
        return StandardResponse(data=None, success=False, message=f"List failed: {str(e)}")


@app.post("/api/drive/download", response_model=StandardResponse, tags=["Google Drive"])
async def manual_download():
    """手動觸發下載 Google Drive 圖片（掃描 → 寫入 ocr_tasks → 下載）"""
    try:
        from app.drive_downloader import download_new_images
        count = download_new_images(drive_service)
        return StandardResponse(
            data={"downloaded": count},
            success=True,
            message=f"Downloaded {count} new images.",
        )
    except Exception as e:
        logger.error(f"手動下載失敗: {e}", exc_info=True)
        return StandardResponse(data=None, success=False, message=f"Download failed: {str(e)}")


@app.post("/api/ocr/process", response_model=StandardResponse, tags=["OCR"])
async def manual_ocr():
    """手動觸發 OCR 處理（撈 status=downloaded，正反面一起處理）"""
    try:
        from app.ocr_processor import process_downloaded_images
        count = process_downloaded_images()
        return StandardResponse(
            data={"processed": count},
            success=True,
            message=f"Processed {count} images.",
        )
    except Exception as e:
        logger.error(f"手動 OCR 失敗: {e}", exc_info=True)
        return StandardResponse(data=None, success=False, message=f"OCR failed: {str(e)}")


@app.post("/api/ocr/process/front", response_model=StandardResponse, tags=["OCR"])
async def manual_ocr_front():
    """手動觸發正面 OCR 處理"""
    try:
        from app.ocr_processor import process_downloaded_images
        count = process_downloaded_images(side="front")
        return StandardResponse(
            data={"processed": count},
            success=True,
            message=f"Processed {count} front images.",
        )
    except Exception as e:
        logger.error(f"手動正面 OCR 失敗: {e}", exc_info=True)
        return StandardResponse(data=None, success=False, message=f"OCR front failed: {str(e)}")


@app.post("/api/ocr/process/back", response_model=StandardResponse, tags=["OCR"])
async def manual_ocr_back():
    """手動觸發反面 OCR 處理"""
    try:
        from app.ocr_processor import process_downloaded_images
        count = process_downloaded_images(side="back")
        return StandardResponse(
            data={"processed": count},
            success=True,
            message=f"Processed {count} back images.",
        )
    except Exception as e:
        logger.error(f"手動反面 OCR 失敗: {e}", exc_info=True)
        return StandardResponse(data=None, success=False, message=f"OCR back failed: {str(e)}")


@app.get("/api/logs", response_model=StandardResponse, tags=["Logs"])
async def get_logs():
    """取得最近 500 筆 log"""
    logs = memory_handler.get_logs()
    return StandardResponse(
        data={"total": len(logs), "logs": logs},
        success=True,
        message=f"{len(logs)} log entries.",
    )


@app.delete("/api/logs", response_model=StandardResponse, tags=["Logs"])
async def clear_logs():
    """清除 log buffer"""
    memory_handler.clear()
    return StandardResponse(data=None, success=True, message="Logs cleared.")


@app.get("/logs", response_class=HTMLResponse, include_in_schema=False)
async def logs_page():
    """Log 即時查看頁面"""
    return """<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>OCR Service Logs</title>
<style>
  body { background: #1e1e1e; color: #d4d4d4; font-family: 'Consolas', monospace; margin: 0; padding: 20px; }
  h1 { color: #569cd6; font-size: 18px; margin: 0 0 10px; }
  .toolbar { margin-bottom: 10px; }
  .toolbar button { background: #333; color: #d4d4d4; border: 1px solid #555; padding: 6px 14px; cursor: pointer; margin-right: 8px; border-radius: 4px; }
  .toolbar button:hover { background: #444; }
  .toolbar span { color: #888; font-size: 13px; }
  #log-container { background: #111; border: 1px solid #333; border-radius: 4px; padding: 12px; height: calc(100vh - 110px); overflow-y: auto; white-space: pre-wrap; word-break: break-all; font-size: 13px; line-height: 1.6; }
  .log-error { color: #f44747; }
  .log-warning { color: #cca700; }
  .log-info { color: #d4d4d4; }
</style>
</head><body>
<h1>OCR Service Logs</h1>
<div class="toolbar">
  <button onclick="fetchLogs()">Refresh</button>
  <button onclick="clearLogs()">Clear</button>
  <button id="autoBtn" onclick="toggleAuto()">Auto: OFF</button>
  <span id="status"></span>
</div>
<div id="log-container"></div>
<script>
let autoRefresh = false, timer = null;
function colorize(line) {
  if (line.includes('ERROR')) return '<span class="log-error">' + line + '</span>';
  if (line.includes('WARNING')) return '<span class="log-warning">' + line + '</span>';
  return '<span class="log-info">' + line + '</span>';
}
async function fetchLogs() {
  document.getElementById('status').textContent = 'Loading...';
  const res = await fetch('/api/logs');
  const json = await res.json();
  const container = document.getElementById('log-container');
  container.innerHTML = json.data.logs.map(l => colorize(l.replace(/</g,'&lt;'))).join('\\n');
  container.scrollTop = container.scrollHeight;
  document.getElementById('status').textContent = json.data.total + ' entries - ' + new Date().toLocaleTimeString();
}
async function clearLogs() {
  await fetch('/api/logs', {method:'DELETE'});
  fetchLogs();
}
function toggleAuto() {
  autoRefresh = !autoRefresh;
  document.getElementById('autoBtn').textContent = 'Auto: ' + (autoRefresh ? 'ON (3s)' : 'OFF');
  if (autoRefresh) { timer = setInterval(fetchLogs, 3000); }
  else { clearInterval(timer); }
}
fetchLogs();
</script>
</body></html>"""

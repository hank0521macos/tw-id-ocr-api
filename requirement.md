# TW-ID-OCR - 台灣身分證 OCR API（簡易版）

## 專案目標

建立一個簡單的 API，上傳身分證圖片，返回識別的姓名和身分證字號。

## 技術需求

- Python 3.14.3
- FastAPI（Web API 框架，內建 Swagger UI）
- PaddleOCR（OCR 引擎，繁體中文）
- Uvicorn（ASGI 伺服器）

## 專案結構
```
tw-id-ocr/
├── uploads/           # 暫存上傳圖片
├── requirements.txt
├── README.md
├── app.py            # FastAPI 主程式
└── ocr_service.py    # OCR 處理邏輯
```

## 功能需求

### 1. API 端點

**啟動服務**：
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Swagger UI**：
- 訪問 `http://localhost:8000/docs` 查看 API 文件
- 訪問 `http://localhost:8000/redoc` 查看 ReDoc 文件

**端點 1：健康檢查**
```
GET /health
```

**Response**：
```json
{
  "data": {
    "status": "ok",
    "service": "tw-id-ocr",
    "version": "1.0.0"
  },
  "success": true,
  "message": "Service is running."
}
```

**端點 2：上傳身分證識別**
```
POST /api/ocr
Content-Type: multipart/form-data
```

**Request**：
- `file`: 身分證圖片檔案（jpg/png，最大 10MB）

**Response（成功）**：
```json
{
  "data": {
    "id_number": "A123456789",
    "name": "王小明",
    "confidence": 0.92,
    "raw_text": "中華民國 身分證 統一編號 A123456789 姓名 王小明..."
  },
  "success": true,
  "message": "OCR recognition completed successfully."
}
```

**Response（失敗 - 無法識別）**：
```json
{
  "data": null,
  "success": false,
  "message": "Unable to extract ID number from image."
}
```

**Response（失敗 - 檔案格式錯誤）**：
```json
{
  "data": null,
  "success": false,
  "message": "Invalid file format. Only jpg/png allowed."
}
```

**Response（失敗 - 檔案過大）**：
```json
{
  "data": null,
  "success": false,
  "message": "File size exceeds 10MB limit."
}
```

## 程式需求

### 1. 標準化 Response 格式（app.py）

**定義 Pydantic Models**：
```python
from pydantic import BaseModel
from typing import Optional, Any

class StandardResponse(BaseModel):
    data: Optional[Any] = None
    success: bool
    message: str

class OCRResult(BaseModel):
    id_number: str
    name: str
    confidence: float
    raw_text: str
```

### 2. FastAPI 設定（app.py）

**API 基本資訊**：
```python
app = FastAPI(
    title="Taiwan ID Card OCR API",
    description="Upload Taiwan ID card image to extract ID number and name",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI
    redoc_url="/redoc"     # ReDoc
)
```

**CORS 設定（如需前端呼叫）**：
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. 端點實作要求

**健康檢查端點**：
```python
@app.get("/health", response_model=StandardResponse, tags=["Health"])
async def health_check():
    """
    健康檢查端點
    """
    return StandardResponse(
        data={"status": "ok", "service": "tw-id-ocr", "version": "1.0.0"},
        success=True,
        message="Service is running."
    )
```

**OCR 端點**：
```python
@app.post("/api/ocr", response_model=StandardResponse, tags=["OCR"])
async def ocr_id_card(
    file: UploadFile = File(..., description="身分證圖片檔案（jpg/png，最大10MB）")
):
    """
    上傳身分證圖片進行 OCR 識別
    
    - **file**: 身分證圖片檔案
    
    Returns:
    - **id_number**: 身分證字號
    - **name**: 姓名
    - **confidence**: OCR 信心度（0-1）
    - **raw_text**: 原始識別文字
    """
    # 實作邏輯...
```

### 4. OCR 服務邏輯（ocr_service.py）

**功能**：
```python
class OCRService:
    def __init__(self):
        """初始化 PaddleOCR（繁體中文）"""
        pass
    
    def process_image(self, image_path: str) -> dict:
        """
        處理圖片並提取資訊
        
        Returns:
            {
                'id_number': str,      # 身分證字號
                'name': str,           # 姓名
                'confidence': float,   # 平均信心度
                'raw_text': str        # 所有識別文字
            }
        """
        pass
    
    def _extract_id_number(self, text: str) -> str | None:
        """
        提取身分證號
        正則：r'[A-Z][12]\d{8}'
        """
        pass
    
    def _extract_name(self, text: str) -> str | None:
        """
        提取姓名
        找連續 2-4 個中文字
        正則：r'[\u4e00-\u9fa5]{2,4}'
        """
        pass
```

### 5. 錯誤處理

**需要處理的情況**：
- 檔案格式不正確（非 jpg/png）
- 檔案大小超過 10MB
- 圖片無法讀取
- OCR 識別失敗
- 無法提取身分證號或姓名

**所有錯誤都返回標準格式**：
```json
{
  "data": null,
  "success": false,
  "message": "錯誤訊息說明"
}
```

## requirements.txt
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
paddleocr==2.7.3
paddlepaddle==2.6.0
opencv-python==4.9.0.80
Pillow==10.2.0
```

## 測試方式

### 1. 使用 Swagger UI（推薦）

1. 啟動服務：`uvicorn app:app --reload`
2. 開啟瀏覽器：`http://localhost:8000/docs`
3. 找到 `/api/ocr` 端點
4. 點擊「Try it out」
5. 上傳身分證圖片
6. 點擊「Execute」查看結果

### 2. 使用 curl
```bash
curl -X POST "http://localhost:8000/api/ocr" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@身分證.jpg"
```

### 3. 使用 Python requests
```python
import requests

url = "http://localhost:8000/api/ocr"
files = {"file": open("身分證.jpg", "rb")}
response = requests.post(url, files=files)
print(response.json())
```

## 實作優先順序

1. ✅ 建立 FastAPI 專案，啟用 Swagger
2. ✅ 定義標準化 Response Model
3. ✅ 實作健康檢查端點
4. ✅ 實作檔案上傳與驗證
5. ✅ 整合 PaddleOCR
6. ✅ 實作身分證號和姓名提取邏輯
7. ✅ 錯誤處理與統一 Response 格式
8. ✅ 在 Swagger UI 測試所有功能

## 備註

- FastAPI 自動生成 Swagger UI，無需額外設定
- 所有 Response 都使用統一的 `{data, success, message}` 格式
- Swagger UI 提供互動式 API 測試介面
- 這是最簡化版本，後續可擴展更多功能
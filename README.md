# Football Analyst

Khung dự án hệ thống hỗ trợ huấn luyện viên phân tích trận đấu bóng đá bằng
Computer Vision và dữ liệu sự kiện.

## Yêu cầu

- Python 3.11
- Node.js LTS và npm
- PowerShell

## Backend

Từ thư mục gốc repository, tạo môi trường và cài dependency (chỉ cần thực hiện
lần đầu):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

Khởi chạy API:

```powershell
uvicorn backend.app.main:app --reload --port 8000
```

Kiểm tra endpoint:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

## Frontend

Mở một cửa sổ PowerShell khác:

```powershell
Set-Location frontend
npm install
npm run dev
```

Mở URL Vite hiển thị trong terminal (mặc định `http://localhost:5173`). Yêu cầu
`/api` từ frontend được chuyển tiếp đến `http://localhost:8000`.

## Kiểm thử

Từ thư mục gốc repository sau khi kích hoạt `.venv`:

```powershell
pytest -v
```

Frontend:

```powershell
Set-Location frontend
npm run build
```

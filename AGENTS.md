# Hướng dẫn dự án cho các agent

## Mô tả dự án

1. Đây là đồ án xây dựng hệ thống hỗ trợ huấn luyện viên phân tích trận đấu bóng đá.
2. Hệ thống kết hợp Computer Vision với dữ liệu sự kiện bóng đá.
3. Backend cung cấp dữ liệu và kết quả phân tích dưới dạng JSON.
4. Frontend trình bày trạng thái và kết quả cho người dùng.
5. Trạng thái hiện tại luôn nằm ở `docs/PROGRESS.md`; đọc nó trước khi làm.

## Công nghệ chốt cứng

- Python 3.11, FastAPI, Pydantic v2.
- Ultralytics YOLO, supervision/ByteTrack, OpenCV.
- scikit-learn, XGBoost, SHAP, statsbombpy, mplsoccer.
- Frontend: Vite, React, TypeScript, Tailwind CSS, shadcn/ui, Recharts, TanStack Query, react-router-dom.
- Chỉ thêm thư viện mới khi được kiến trúc sư cho phép.

## Môi trường và lệnh chuẩn

- Windows 11, PowerShell, Python 3.11, Node 24 LTS; không dùng Docker.
- Làm việc CHỈ trong `D:\projects\football-analyst`; không tạo file ngoài thư mục này.
- Backend:

  ```powershell
  .\.venv\Scripts\Activate.ps1
  uvicorn backend.app.main:app --port 8000
  ```

- Test từ gốc repo:

  ```powershell
  pytest -v
  ```

- Test mạng:

  ```powershell
  pytest -v -m network
  ```

- Frontend (luôn `cd frontend` trước):

  ```powershell
  npm run dev
  npm run build
  npm run lint
  ```

## Quy ước đã chốt

- Cache sự kiện dùng CSV vì môi trường không có `pyarrow`.
- Dữ liệu StatsBomb luôn tấn công về phía x tăng; dữ liệu tracking video thì không.
- Tên có dấu hiển thị sai trong PowerShell 5 là lỗi hiển thị, không phải lỗi dữ liệu; API trả UTF-8 đúng.
- Tên cầu thủ cho giao diện dùng `short_name` nếu đã có.

## Bàn giao giữa các agent

- Đầu phiên đọc `AGENTS.md`, `docs/PROGRESS.md` và `docs/DATA_CONTRACT.md`, rồi tóm tắt trạng thái.
- Chỉ làm đúng nhiệm vụ được giao.
- Cuối phiên cập nhật `docs/PROGRESS.md` và git commit; không commit khi test lỗi.
- Không tự thêm tính năng.
- Gặp mâu thuẫn thì dừng và hỏi.

## Cấu trúc thư mục

```text
backend/app/       FastAPI
backend/cv/        Computer Vision
backend/tactics/   Phân tích chiến thuật
backend/advisor/   Hỗ trợ/khuyến nghị
backend/common/   Schema và tiện ích dùng chung
frontend/          Ứng dụng web
data/raw/          Dữ liệu đầu vào cục bộ
data/processed/    Dữ liệu đã xử lý cục bộ
notebooks/         Notebook nghiên cứu
tests/             Kiểm thử
docs/              Tài liệu dự án
```

## Luật dự án

- (a) Backend trả JSON, không trả ảnh vẽ sẵn.
- (b) Tọa độ luôn theo hệ sân chuẩn được mô tả trong `docs/DATA_CONTRACT.md`.
- (c) Mỗi tính năng phải có test hoặc lệnh kiểm tra.
- (d) Không đổi hợp đồng dữ liệu nếu chưa được cho phép.
- (e) Cuối mỗi phiên làm việc phải cập nhật `docs/PROGRESS.md`.
- (f) Video được xử lý theo từng đoạn để tiết kiệm RAM.

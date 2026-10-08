# Hướng dẫn dự án cho các agent

## Mô tả dự án

1. Đây là đồ án xây dựng hệ thống hỗ trợ huấn luyện viên phân tích trận đấu bóng đá.
2. Hệ thống kết hợp Computer Vision với dữ liệu sự kiện bóng đá.
3. Backend cung cấp dữ liệu và kết quả phân tích dưới dạng JSON.
4. Frontend trình bày trạng thái và kết quả cho người dùng.
5. Bước 0 chỉ dựng khung; không triển khai logic CV, tactics hoặc advisor.

## Công nghệ chốt cứng

- Python 3.11, FastAPI, Pydantic v2.
- Ultralytics YOLO, supervision/ByteTrack, OpenCV.
- scikit-learn, XGBoost, SHAP, statsbombpy, mplsoccer.
- Frontend: Vite, React, TypeScript, Tailwind CSS, shadcn/ui, Recharts, TanStack Query.

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

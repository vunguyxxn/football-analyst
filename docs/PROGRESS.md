# Tiến độ dự án

## Trạng thái hiện tại

Khung bước 0 đã dựng và nghiệm thu được trên môi trường Windows; chưa triển khai
logic Computer Vision, tactics hoặc advisor.

## Đã làm

- Chốt cấu trúc backend FastAPI và frontend Vite + React + TypeScript.
- Chốt hợp đồng dữ liệu và hệ tọa độ sân chuẩn trong `DATA_CONTRACT.md`.
- Khởi tạo Git, `.gitignore` và môi trường ảo Python 3.11.
- Tạo API health check, schema Pydantic, phép chuyển tọa độ và 11 bài kiểm thử.
- Tạo frontend Vite + React + TypeScript; tích hợp Tailwind CSS, shadcn/ui,
  TanStack Query, Recharts, Framer Motion và lucide-react.
- Hoàn tất dark mode mặc định, màu nền xám than, nhấn xanh lá, và proxy `/api`.
- Xác minh endpoint `/api/health` trả `{"status":"ok"}`, frontend hiển thị
  `Backend: OK`, 11 test pass và build frontend thành công.

## Việc tiếp theo

- Triển khai các module CV, tactics và advisor theo đặc tả tiếp theo.

## Vấn đề tồn đọng

- Chưa có logic nghiệp vụ/CV; đây là chủ ý của bước 0.
- Không có lỗi tồn đọng trong phạm vi bước 0. Chưa cài PyTorch/CUDA hay
  dependency CV; sẽ thực hiện ở bước sau theo cấu hình GPU.

## Quyết định đã chốt

- Python 3.11; FastAPI; Pydantic v2.
- Gốc tọa độ sân chuẩn ở góc trái dưới, đơn vị mét, sân 105 × 68.
- Không cài PyTorch trong requirements ở bước này; phần CV có file dependency riêng.
- Frontend dùng dark mode mặc định, nền xám than và màu nhấn xanh lá.
- Tailwind CSS: `4.3.3`; shadcn CLI/UI: `4.21.4` (khởi tạo thành công ngày 2026-10-08).

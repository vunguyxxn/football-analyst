# Tiến độ dự án

## Trạng thái hiện tại

Bước 0, Module B1, giao diện bước 1.5 và bước 1.6 đã triển khai, kiểm thử.
Backend nạp StatsBomb Open Data, chuẩn hóa sự kiện và cung cấp pass network;
frontend có shell điều hướng, sân SVG và trang phân tích trận. Chưa triển khai
logic CV, xG, sơ đồ đội hình hoặc advisor.

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
- Module B1: loader StatsBomb dùng cache CSV trong
  `data/processed/events_{match_id}.csv` do môi trường không có pyarrow; bổ sung
  pass network và các endpoint competitions, matches, pass-network.
- Nghiệm thu trận World Cup 2018 Brazil–Bỉ (match ID `8650`): 3.589 sự kiện;
  tọa độ x nằm trong `[0.875, 105]`, y trong `[0, 67.15]`.
- `pytest -v`: 20 passed, 1 network test deselected. `pytest -v -m network`:
  1 passed, 20 deselected.
- Smoke test 3 API endpoint thành công; match ID không tồn tại trả HTTP 404.
- Bước 1.5: thêm React Router, shell dark mode, các trang trạng thái "Sắp có",
  component sân SVG theo hệ mét và trang Phân tích trận lấy dữ liệu thật từ API.
- Hợp đồng dữ liệu bổ sung hướng tấn công chuẩn hóa cho StatsBomb; tracking
  video không mặc định có hướng thống nhất.
- Nghiệm thu frontend: `npm run build` thành công; `npm run lint` thành công
  (còn một cảnh báo Fast Refresh có sẵn trong `components/ui/button.tsx`);
  `pytest -v`: 20 passed, 1 network test deselected.
- Kiểm tra giao diện trình duyệt ở 1440px và 768px, có dữ liệu thật Brazil–Bỉ;
  chiều rộng tài liệu không vượt viewport 768px. Đã xem trạng thái trống và
  trạng thái tải/lỗi khi backend tắt.
- Bước 1.6: loader giữ `player_nickname`; mỗi node pass network trả `short_name`
  duy nhất trong đội, ưu tiên nickname và phân biệt họ trùng nhau. Frontend dùng
  tên ngắn trên sân/bảng, giới hạn nhãn sân mặc định cho 6 cầu thủ chuyền nhiều
  nhất; tooltip vẫn hiển thị tên đầy đủ, số chuyền và số chạm.
- Kiểm thử bước 1.6: `pytest -v` — 21 passed, 1 network test deselected;
  `npm run build` thành công; `npm run lint` thành công (còn cảnh báo Fast
  Refresh đã có trong `components/ui/button.tsx`).
- Đã xác nhận dữ liệu thật cho Brazil (14 nút, 57 cạnh) và Bỉ (13 nút, 46 cạnh);
  ảnh nghiệm thu lưu tại `screenshots/pass-network-brazil.png` và
  `screenshots/pass-network-belgium.png`.

## Việc tiếp theo

- Tiếp tục các module CV, tactics và advisor theo đặc tả tiếp theo.

## Vấn đề tồn đọng

- Chưa có logic CV, xG, sơ đồ đội hình hoặc advisor; đây là ngoài phạm vi B1.
- Không có lỗi tồn đọng trong phạm vi bước 0. Chưa cài PyTorch/CUDA hay
  dependency CV; sẽ thực hiện ở bước sau theo cấu hình GPU.

## Quyết định đã chốt

- Python 3.11; FastAPI; Pydantic v2.
- Gốc tọa độ sân chuẩn ở góc trái dưới, đơn vị mét, sân 105 × 68.
- Không cài PyTorch trong requirements ở bước này; phần CV có file dependency riêng.
- Frontend dùng dark mode mặc định, nền xám than và màu nhấn xanh lá.
- Tailwind CSS: `4.3.3`; shadcn CLI/UI: `4.21.4` (khởi tạo thành công ngày 2026-10-08).

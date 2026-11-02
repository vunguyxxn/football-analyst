# Cải thiện giao diện — đợt 1, 02/11/2026

Triển khai theo `UI_UX_AUDIT.md`: khả năng đọc, phân cấp và responsive.
Không thêm dependency, đổi API, DATA_CONTRACT hoặc xử lý CV.

## Thay đổi

- Tổng quan có bốn lối vào chức năng thật, không dùng số thống kê giả.
- Chữ HTML nhỏ nâng lên 12 px, nội dung chính 14 px; giữ đơn vị chữ SVG theo
  hệ sân. Footer tăng tương phản; dùng SectionTabs, focus và surface chung.
- Mobile thay rail icon bằng menu có nhãn, backdrop, Escape, vòng Tab, khóa
  cuộn và trả focus. Nội dung phía sau dùng inert khi menu mở.
- Match đưa mạng chuyền lên trước KPI sự kiện. KPI gọn, lưới 2×2 mobile;
  bỏ mũi tên thiếu baseline, tooltip ghi số sự kiện thay cho lần chạm.
  Số dùng vi-VN, phân biệt số 0 và thiếu dữ liệu.
- Video ưu tiên chọn file, có hướng dẫn ba bước; nhập tracking là tùy chọn
  nâng cao. Không dựng panel rỗng trước khi có video. Tiến độ thu gọn khi có
  kết quả, hiển thị nhãn partial và giới hạn ngắn. Ba mục Không gian đội /
  Vận động / Hiệu chỉnh giữ component mounted, bảo toàn lựa chọn và tua video.
- Players có chọn nhanh/bộ lọc mobile; vai trò/index nguồn chuyển vào
  disclosure. Giữ short_name và phân biệt StatsBomb/Metrica.
- Reports ưu tiên gợi ý trước history/hash/phiên bản. Metadata và cơ chế lưu
  cũ vẫn giữ ở cuối trang, thu gọn; ngày mở không trở thành ngày tạo.
- Tactics có ba mục Bố trí / Hiển thị / Kế hoạch; công cụ mobile thành lưới,
  pha có hàng riêng, chế độ tập trung có nút thoát/Escape. Tablet đặt inspector
  dưới sân (đo sân khoảng 650 px tại viewport 1024×768). Không đổi đối tượng,
  undo, lưu trữ hoặc tọa độ.
- Reduced motion qua MotionConfig và CSS.

## Kiểm tra

- `cd frontend; npm run build`: đạt; còn warning bundle >500 kB.
- `cd frontend; npm run lint`: không lỗi; còn warning Fast Refresh có sẵn
  ở `components/ui/button.tsx`. Warning ref cleanup mới đã sửa.
- `cd frontend; npm test`: 32/32 đạt; cập nhật kỳ vọng số vi-VN.
- QA sáu trang ở 1440×1000, 390×844, 1024×768; chưa thấy tràn ngang toàn
  trang trong trạng thái đã xem. Đã thao tác chọn cầu thủ/bộ lọc, đổi nguồn,
  tab video, menu link/Escape/Tab/Shift+Tab/trả focus, inspector và focus sân.
- Ảnh/số đo local ở `data/processed/ui_refresh_20261102/`. Số đo lúc đang tải
  không dùng làm benchmark chiều dài/hiệu năng. Video mẫu UI vẫn là job cũ
  c140f8aefb4e4678b51fe6f633e1fc56, không đại diện chất lượng CV mới nhất.

## Phần còn lại

Chưa làm toàn bộ audit: zoom/pan sân, tương tác chart nâng cao, legend chuẩn
hóa và route code splitting. Chưa kiểm định WCAG đầy đủ, cảm ứng thật, mọi
luồng upload/GPU hoặc mọi lỗi. Không tuyên bố chất lượng CV được cải thiện.

Phạm vi 14 cầu thủ của mạng chuyền so với mô tả trước thay người đầu vẫn cần
xác minh riêng; phiên này không sửa thuật toán hoặc che bằng đổi nhãn.

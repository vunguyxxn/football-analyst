# Dọn workspace — 04/11/2026

Theo yêu cầu xóa file không cần thiết nhưng không ảnh hưởng ứng dụng.
Không thay đổi mã nguồn, thư viện, model, schema hoặc dữ liệu phân tích.

## Đã dọn

- 238 mục cũ trong `.tmp`: bộ cài wheel PyTorch/torchvision, file pip giải
  nén/tạm và kết quả pytest cũ trước 03/11. Giữ script nghiên cứu và các mục mới.
- 7 thư mục bytecode cache của mã dự án; pytest cache và 5 thư mục ảnh kiểm tra
  frontend/UI cũ. Giữ ảnh trong `docs/screenshots` phục vụ tài liệu.
- Hai video demo dư trong public và hai bản tương ứng trong dist:
  `e0eb4128f58d45ea85c4ef0000ca92df.mp4`,
  `f650e063b2eb493c9552d33f55bef9d6.mp4`. Đã xác nhận byte/hash trùng video
  hiện tại và không được mã ứng dụng/manifest hiện tại tham chiếu.
- Tổng 255 mục, 32.751 file; 4.779.857.623 byte, khoảng **4,45 GiB** theo kích
  thước file. Không coi đây là phép đo chính xác chênh lệch dung lượng ổ đĩa;
  cache và thư mục test nhỏ được sinh lại khi kiểm tra.

Mỗi đường dẫn xóa đã kiểm nằm trong workspace. Các symlink `*current` của
pytest chỉ được gỡ không đệ quy sau khi kiểm đích cuối nằm trong chính cây
temp được dọn; sau đó mới xóa cây. Không đi theo link ra dữ liệu khác.

## Giữ lại và xác minh

Giữ `.git`, môi trường Python/Node, toàn bộ `data/raw`, video jobs, các bộ train,
model/checkpoint và kết quả nghiên cứu. Giữ video demo hiện tại, các manifest,
video/tracking fallback v1 mà mã nguồn còn hỗ trợ, dữ liệu mẫu player/coach.
Build tạo lại dist từ public sau khi bỏ các bản sao dư.

- 14.064 file dữ liệu/tài nguyên được bảo vệ: không thiếu hoặc đổi kích thước.
- 226 file nguồn/tài nguyên public: SHA-256 không đổi so với bản đối chiếu.
- Python: **577 passed**, 1 test network không chạy, 4 warning có sẵn.
- Frontend: **32 test đạt**, build đạt, lint không lỗi; còn warning bundle và
  Fast Refresh có sẵn.
- Health, metric definitions, pass network và event metrics trả 200 qua
  FastAPI TestClient. Demo có căn cứ đọc lại nhất quán, giữ 13.978 dòng vị trí;
  video được manifest hiện tại trỏ tới vẫn tồn tại.

Không chạy lại GPU/upload hoặc đánh giá độ chính xác CV trong phiên dọn file.
Không xóa dataset/model chỉ vì không nằm trên luồng runtime: chúng còn phục vụ
huấn luyện, kiểm chứng và báo cáo đồ án.

Tổng hợp: `docs/fixtures/workspace_cleanup_20261104.json`.
Danh sách chi tiết local: `data/processed/cleanup_20261104/` (không commit).

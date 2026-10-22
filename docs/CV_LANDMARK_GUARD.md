# Chặn phép chiếu khi sai mốc sân — 22/10/2026

## Kết quả

Đã thêm chế độ `--landmark-checks` vào CLI bước 4, dùng mốc sân gán nhãn tay
theo lịch để phát hiện sai tọa độ mà optical flow/RANSAC vẫn cho qua. Không
đổi hệ sân 105 × 68 m, schema/API, dependency hoặc ngưỡng CameraMotion.

Chế độ này **chặn kết quả không đạt**, chưa sửa phép chiếu hoặc tự tìm mốc.
Không bật tùy chọn thì chế độ cũ giữ nguyên. Lượt replay trên ba đoạn cũ đã
chặn cả ba ở lần kiểm tra đầu và chưa xuất tọa độ nào; không tuyên bố độ
chính xác tăng hay toàn clip đã dùng được để đo chỉ số cầu thủ.

## Cơ chế

`backend/cv/landmark_guard.py` kiểm tra hash/kích thước, frame, cặp điểm ảnh
và tọa độ sân. Checkpoint phải sau mốc hiệu chỉnh đầu và trong cùng phạm vi.
Mỗi lần có ít nhất 2 mốc khác nhau, không trùng hoặc ngoài ảnh/sân. Mốc chỉ
phục vụ so sánh, không dùng để fit, clamp hoặc tự sửa ma trận hiện tại.

Ban đầu chờ kiểm chứng, không xuất TrackingRow. Sai số lớn nhất vượt ngưỡng
hoặc quá hạn kiểm chứng làm mất hiệu chỉnh, khóa phép chiếu đến mốc tay mới.
Mốc mới vẫn phải có checkpoint đạt trước khi xuất tọa độ. Các cặp tọa độ
không hữu hạn cũng bị chặn. Camera tiếp tục cập nhật lúc chờ, video vẫn ghi
đủ. Log chứa lý do và lỗi từng mốc; báo cáo lưu cấu hình kiểm chứng.

Mặc định: `max_error_m=1.0`, `max_gap_frames=30`. Đây là ngưỡng kỹ thuật của
baseline, không phải chuẩn độ chính xác đã được nghiệm thu. Khoảng giữa hai
checkpoint vẫn có thể sai mà không bị phát hiện ngay. Sai nhãn tay cũng có
thể gây từ chối nhầm. Cần dữ liệu xác minh đủ dày để có coverage liên tục;
chưa có giao diện gán nhãn checkpoint hoặc phát hiện vạch sân tự động.

Định dạng và lệnh chạy tại `CV_HOMOGRAPHY.md`, mục kiểm tra độ trôi bằng mốc
tay. Mọi đầu ra tracking vẫn tuân thủ hợp đồng hiện tại.

## Replay trên clip thật

Nguồn bản cắt hash
`86f6f04ce05ac464269dfa4d831bef0c12c3654acdd2fa3c1b6379f864597b2e`,
720p/60 FPS. Cấu hình hiệu chỉnh ba đoạn giữ nguyên tại
`docs/fixtures/vid1_11f23eea_homography_segments.json`.

Chuyển các nhãn khảo sát cũ thành checkpoint phục vụ runtime guard tại
`docs/fixtures/vid1_11f23eea_landmark_checks.json`. **Các nhãn này không còn
là tập đánh giá độc lập**. Replay này kiểm tra logic chặn bằng mốc có sẵn,
không đo precision/recall hoặc độ chính xác trên mẫu chưa thấy.

Chốt ngưỡng 1 m và thời hạn 90 frame trước replay. Tính lại optical flow trên
905 frame nguồn bằng bbox person cache của YOLO thật từ lượt trước, không
chạy YOLO mới, ByteTrack hoặc chỉ số cầu thủ. Video từng đoạn đọc lại đủ.

| Đoạn | Checkpoint đầu | Lỗi lớn nhất | Kết quả |
|---|---:|---:|---|
| Đầu, đổi hướng lia | 75 | 2,91 m | lost, không xuất tọa độ |
| Lia trái | 525 | 3,15 m | lost, không xuất tọa độ |
| Lia trở lại | 1125 | 1,56 m | lost, không xuất tọa độ |

Trước mỗi checkpoint là 75 frame `awaiting_landmark_check`; sau đó trạng
thái lost được giữ tới segment mới. Tổng 225 frame chờ + 680 lost = 905.
Trong cả ba đoạn: **0 detection được xuất tọa độ**. Đây là kết quả từ chối
chất lượng, không phải lỗi mất video hoặc một phép đo quãng đường bằng 0.
Không dùng bộ guard này để tuyên bố đã có dữ liệu di chuyển cầu thủ hợp lệ.

Artifacts cục bộ tại `data/processed/clip_11f23eea/landmark_guard_check/`:
`summary.json`, `camera_quality.jsonl`, ba video diagnostic và ảnh checkpoint.
Helper replay `.tmp/replay_landmark_guard.py` là script khảo sát workspace,
không phải công cụ đóng gói cho fresh checkout. Lệnh CLI dùng fixture thật
có trong `CV_HOMOGRAPHY.md`; lệnh CLI toàn clip chưa chạy trong lượt replay.

## Kiểm thử

Toàn bộ 99 test qua, 1 network test deselected, cảnh báo Starlette cũ.

- Chờ kiểm chứng, đạt ngưỡng, cấp phép có hạn, hết hạn và mốc mới.
- Sai số vượt ngưỡng vẫn bị chặn khi giả lập camera báo tracked; giữ nguyên
  ma trận đầu vào, không lấy nhãn kiểm chứng để fit lại.
- Checkpoint đến muộn không phục hồi chuỗi đã hết hạn; sai dữ liệu/hash/
  kích thước/phạm vi/mốc trùng bị từ chối.
- Tích hợp codec + ByteTrack thật, detector/camera được giả lập ổn định để
  kiểm tra output: không có tọa độ trước kiểm chứng hoặc sau hết hạn;
  chỉ frame 1–4 được xuất trong video kiểm soát, video vẫn đủ 23 frame.
- Hồi quy các chế độ cũ không bật guard.

## Việc tiếp theo

Hiệu chỉnh lại các đoạn bị từ chối, dùng mốc đang có làm dữ liệu phát triển
và chọn checkpoint/nhãn đánh giá mới. Để giảm công gán nhãn cần một bước
kiểm tra vạch sân từ ảnh; chưa được triển khai trong phiên này. Cơ chế guard
hiện tại giúp ngừng báo chỉ số khi thiếu bằng chứng chất lượng, không thay
thế cải thiện độ chính xác hoặc đánh giá định danh/vị trí chân cầu thủ.

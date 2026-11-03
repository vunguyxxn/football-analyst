# Mở rộng nhãn vai trò v9

Ngày 03/11/2026. Bổ sung nhãn trên ba clip v8, không thêm nguồn trận mới,
không huấn luyện hoặc đổi model đang chạy trong ứng dụng.

## Kết quả

| Phần | Vùng ảnh mới | Cầu thủ | Thủ môn | Trọng tài |
|---|---:|---:|---:|---:|
| Train candidate: match 117093, 118575 | 5 | 16 | 4 | 2 |
| Kiểm chứng: match 128057 | 2 | 15 | 0 | 1 |

Các số là quan sát trên ảnh, không phải số người khác nhau. Cộng v8 và v9:
train candidate 9 vùng với 46 cầu thủ, 6 thủ môn, 4 trọng tài;
kiểm chứng 4 vùng với 31 cầu thủ, 1 thủ môn, 3 trọng tài.

Chỉ 2/7 ảnh mới dùng toàn khung (117093-f749, 118575-f500). Năm vùng
còn lại cắt bỏ dải có người xa hoặc vai trò chưa rõ. Người bị cắt tại mép
ROI vẫn được giữ nhãn phần nhìn thấy. Không dùng phần ngoài ROI làm nền âm.
Có thêm thủ môn đỏ/vàng và trọng tài áo tối; thủ môn vàng xuất hiện hai
thời điểm của cùng trận, không phải hai nguồn độc lập.

## Quy trình và giới hạn

- Giữ nguyên split v8 theo toàn match ID; 128057 và mọi clip/hiệp cùng trận
  không được đưa vào train sau khi đã xem kết quả detector.
- Mốc đề xuất cố định: 0/250/500/749 phía train, 250/500 phía kiểm chứng.
  Nhận ROI sau khi xem ảnh bối cảnh, crop đánh số và overlay xuất nhãn.
  Ba mốc train 117093-f0/f250, 118575-f0 chưa hoàn tất rà, không dùng làm âm.
- Proposal YOLO11n COCO person, không dùng dự đoán vai trò v6/v7 để gán nhãn.
  Loại proposal trùng và nhân tố ngoài trận; không lấy nhãn machine của nguồn.
- Packet v9 khóa hash packet v8 và split. Export kiểm tra video SHA256,
  PNG decode, hình học ROI, sàng lọc gần trùng với 465 ảnh v6 khác nhau.
  Test bổ sung chặn tái sử dụng frame cũ hoặc đổi split khi tạo bản gia tăng.
- Đây là nhãn do agent rà với COCO hỗ trợ, chưa có người kiểm độc lập.
  Nguồn là footage thật với crop camera ảo lia/zoom, không phải broadcast gốc.
  V9 chưa chạy đánh giá detector; chưa có bằng chứng chất lượng model tăng.

Packet: `docs/fixtures/role_sources_review_v9.json`.
Snapshot: `docs/fixtures/role_source_release_v9.json`.
Ảnh và YOLO labels cục bộ: `data/processed/role_source_release_v9/`.
Provenance/license/split giữ theo `docs/ROLE_SOURCES_V8.md` và
`docs/fixtures/role_source_split_v8.json`.

## Tái tạo

Từ gốc repo, output phải chưa tồn tại:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.release_role_sources --packet docs/fixtures/role_sources_review_v9.json --output data/processed/role_source_release_v9
.\.venv\Scripts\python.exe -m pytest -q tests/test_role_source_release.py --basetemp .tmp/pytest-role-v9-targeted
```

Bước tiếp theo: ghép các vùng train v8/v9 vào một bản dataset mới với số lần
lấy mẫu được chốt trước; kiểm tra không rò match và giữ nguyên val/test cũ.
Khóa kế hoạch đánh giá ba lớp tại 640/1280 trước khi huấn luyện small.
Cần thêm nguồn broadcast lia thật và nhiều trận kiểm chứng để đo khác miền;
bốn vùng cùng một match chưa đủ kết luận tổng quát hóa.

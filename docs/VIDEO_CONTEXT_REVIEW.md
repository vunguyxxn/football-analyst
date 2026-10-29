# Rà nhóm áo, vai trò và hướng tấn công — 29/10/2026

## Phạm vi và kết quả

Clip Video Project15.mp4, job c140f8aefb4e4678b51fe6f633e1fc56, cùng
SHA256 f51735a042b493eba3cced891209fe1b6beb20ca80e20c340c7ede51900495d0.
Đã xem crop từ ảnh gốc ở lịch2/5/8s,31/35/39s,41/45/49s: ba thời điểm
ở mỗi đoạn trước đó đủ dữ liệu chiến thuật. Có180 mẫu người do detector
chọn, gán nhãn màu/vai trò bởi agent. Sheet crop giấu group dự đoán khi
rà nhưng agent đã thấy UI/dự đoán từ các bước trước: không blinded,
không nhãn HLV độc lập, không đo recall phát hiện người.

| Mẫu có nhãn | Đối chiếu nhóm màu gốc |
| --- | --- |
| 80 cầu thủ áo đỏ | 79 nhóm A, 1 chưa rõ |
| 85 cầu thủ áo trắng | 84 nhóm B, 1 chưa rõ |
| 9 trọng tài áo xanh nhạt | 4 lẫn nhóm B, 5 chưa rõ |
| 6 thủ môn áo xanh lá | 6 chưa rõ, không lẫn A/B |

Đúng nhóm163/165 mẫu cầu thủ sân, 2 chưa rõ. Không gọi là accuracy
toàn clip; nếu chỉ xem độ đúng nhóm cầu thủ thì sẽ bỏ qua lỗi đưa trọng
tài vào phân tích đội. Không thêm người bị detector bỏ sót hoặc đoán
danh tính/số áo. Hai nhãn chưa rõ vẫn giữ nguyên, không gán bù.

## Quỹ đạo vai trò đã rà

Rà tiếp crop ở đầu/cuối và mỗi60 khung có mặt trên các ID:

- Trọng tài:12 [0,75),49 [92,169),116 [175,371),157 [402,1571).
- Thủ môn xanh lá:196 [716,1107),275 [1108,1571).

Đây là suy vai trò theo cùng ID trong khoảng đã rà, không kiểm từng
khung và không loại được mọi nguy cơ đổi nhầm ID giữa hai mẫu. ID196
và275 không được ghép thành một danh tính thật; chỉ cùng loại vai trò.
Không áp dụng ID ngoài khoảng hoặc sang clip/job khác. Thủ môn áo đỏ
không thấy thì không tự tạo thêm. Quy tắc không phải bộ phân loại vai
trò học máy và không dùng cho upload bất kỳ.

Loại các quỹ đạo này trước tính heatmap, cự ly, đếm người và so hình
thái đội trong API tactics. Với artifact hiện hành, loại thêm542 lượt
vị trí trước đây thuộc A/B (trọng tài); thủ môn vốn unknown đã không
vào nhóm. Không xóa tracking, sửa tọa độ hoặc đổi DATA_CONTRACT. Khung
video, sân mini và báo cáo vận động tổng hợp vẫn dùng dữ liệu màu gốc;
panel chiến thuật ghi rõ phạm vi lọc vai trò để tránh nhầm hai loại số.

## Hướng và sơ đồ

Agent suy luận A áo đỏ tấn công theo x tăng, B áo trắng theo x giảm
trong0–10s và30–50s: nhóm trắng và thủ môn xanh lá ở khung thành bên
phải; xem ảnh gốc và diễn biến ở nhiều thời điểm. Chưa đối chiếu tên
trận/hiệp/đội hình chính thức, không gán trạng thái có bóng cho cả đoạn.
Ngoài khoảng đã rà, hướng vẫn unknown; không suy ra từ trung bình vận
tốc hoặc một đường chuyền.

partial_formation nhận hướng tùy chọn, chỉ so mẫu theo hướng đó khi
cả cửa sổ nằm trong phạm vi rà. Không tự đảo mẫu ngược hướng để có
điểm khớp đẹp hơn. Không có ngữ cảnh thì tiếp tục thử cả hai hướng như
trước. Bản đồ theo hệ sân gốc, không lật tọa độ heatmap.

Sáu kết quả đủ hỗ trợ hiện hành vẫn không chốt sơ đồ: A0–10/30–40/
40–50 khớp mẫu kém, B0–10/30–40 mơ hồ, B40–50 khớp kém. Ví dụ B30–40
mẫu5-3-2 đứng đầu có RMSE4,71m, nhưng vẫn không đủ phân biệt. Không
tính formation accuracy từ nhãn tự sinh. Ghi chú từ ảnh gốc chỉ mô tả
phần hình thái nhìn thấy, các vị trí ngoài camera vẫn là giả định.

## Khóa nguồn và kiểm thử

Fixture docs/fixtures/clip_f51735_context_review_v1.json lưu lịch,
180 nhãn frame/ID/box, bằng chứng quỹ đạo, hướng suy luận và ghi chú
ba cửa sổ. prepare kiểm nguồn thật/job, nhãn đủ mọi crop ở lịch mẫu,
trùng/sai box/vai trò mâu thuẫn và phạm vi quỹ đạo. Đọc chunk từng phần,
chỉ giữ box ở lịch mẫu và lịch rà vai trò; không giữ toàn video trong RAM.

Artifact job/tactical_context/report.json chứa audit và hash fixture,
toàn bộ chunk, tracking sân. API chỉ dùng nếu mọi hash/timing/job khớp
và nội dung rà còn đúng fixture. Sửa nhãn, đổi tracking/hiệu chỉnh hoặc
chunk phải chuẩn bị lại; dữ liệu lệch bị từ chối thay vì áp vai trò cũ.
Clip không có artifact rà không được tự gán áo đỏ/trắng hoặc hướng.

Lệnh tạo, output phải chưa tồn tại; lần sau dùng đường dẫn mới:

```powershell
.\.venv\Scripts\python.exe -m backend.tactics.video_context data/processed/video_jobs/c140f8aefb4e4678b51fe6f633e1fc56 docs/fixtures/clip_f51735_context_review_v1.json data/processed/context_review_new
.\.venv\Scripts\python.exe -m pytest tests/test_video_context.py tests/test_video_tactics.py -v --basetemp .tmp/pytest_video_context
```

Artifact đã kiểm tra được đặt ở job/tactical_context/report.json cho
API dùng. Không tự ghi đè nhãn hoặc kết quả trước khi khóa nguồn.
Crop/ảnh gốc tại data/processed/tactical_context_review_v1/; chỉ dùng
nghiệm thu nội bộ, không tải video ra bên ngoài.

15 test mới: phạm vi ID/hướng, không đổi dữ liệu nguồn, heatmap không
cộng trọng tài/ô giả định, so hướng bắt buộc, audit riêng sai vai trò,
nhãn thiếu/trùng/sai/mâu thuẫn/nguồn lạ/ghi đè audit, và từ chối context
cũ sau đổi nhãn/chunk/tracking. Chưa huấn luyện model mới hoặc dùng nhãn
này làm tập kiểm tra độc lập.

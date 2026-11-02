# Bổ sung nhãn trọng tài — đợt 2

Ngày 02/11/2026. Hoàn thành phần bổ sung/rà nhãn theo yêu cầu bước 1.
Không huấn luyện lại, thay weights hoặc thay luồng upload trong phiên này.

## Những gì đã làm

| Hạng mục | Số lượng | Ý nghĩa |
|---|---:|---|
| Khung video mới rà | 15 | Từ ba nguồn đã thuộc train; không phải video/trận mới độc lập |
| Lượt trọng tài mới gán nhãn | 30 | Áo xanh nhạt; lấy từ các frame chưa nằm trong các fixture vai trò trước |
| Nhãn trọng tài gốc rà lại | 17 | Có sẵn trong dữ liệu nguồn, không tính thành 17 nhãn mới |
| Mẫu cầu thủ đối chiếu | 30 vùng | Áo đỏ/trắng, vẫn mang lớp player, giúp phân biệt với trọng tài |
| Mẫu nhân viên/camera | 6 vùng | Vùng nền không có đối tượng mục tiêu; không gán thành player/referee |
| Trường hợp chưa chắc chắn | 7 | 5 nhãn nguồn quá mờ/nhỏ và 2 trường hợp chỉ thấy đầu/áo bị cắt |

Tổng **83 vùng ảnh đã rà**, gồm 47 lượt trọng tài. Đây là lượt quan sát,
không phải 47 người khác nhau. Các khung cùng clip có thể lặp lại một
trọng tài; không dùng con số này để suy độ đa dạng trận đấu.

Màu áo của 47 lượt được giữ: xanh nhạt 33, vàng 10, đỏ 3, đen 1.
30 lượt mới từ video cục bộ đều áo xanh nhạt; các màu còn lại được rà
từ nhãn gốc của tập train. Chưa có video cục bộ mới với trọng tài đổi
áo; không dùng đổi màu ảnh tổng hợp để giả làm mẫu thật.

Theo ảnh đã xem: 32 lượt có chiều cao bbox dưới 24 px khi quy về imgsz
640; 3 lượt bị che một phần; 2 lượt bị cắt ở mép ảnh. Góc quan sát gồm
8 trước, 23 bên, 14 sau và 2 chưa xác định rõ hướng. Các thuộc tính
mang tính mô tả của agent, chưa được người rà thứ hai xác nhận.

## Khung mới và nguồn được giữ nguyên

| Video | Frame mới |
|---|---|
| Video Project 15.mp4 | 330, 510, 690, 870, 1110, 1290, 1530 |
| Video Project 15 (1).mp4 | 150, 350, 650, 1000 |
| Video Project 15 (2).mp4 | 300, 700, 1750, 2250 |

Không lấy Project 12 hoặc 08fd33_4 vào đợt bổ sung train; không chuyển
nhóm nguồn validation/test của protocol v1 sang train. Nhãn nguồn gốc
được rà chỉ thuộc các prefix đã ở `red_stadiums/train`. Tên thư mục
train/test của bản dữ liệu gốc không thay thế phép chia theo nhóm nguồn
đã khóa trong protocol dự án.

Nguồn ảnh/nhãn bên ngoài vẫn là revision
`e8b8cea002692efd74c945fcdad63e729adc5671` của
[martinjolif/football-player-detection](https://huggingface.co/datasets/martinjolif/football-player-detection/tree/e8b8cea002692efd74c945fcdad63e729adc5671),
dataset card công bố CC BY 4.0, nguồn Football project/Roboflow.
Không tải thêm dữ liệu hoặc thêm dependency ở phiên này.

## Cách rà và phạm vi nhãn

Đề xuất người từ COCO11n hiện có, không dùng kết quả model vai trò để
quyết định nhãn. Agent đã xem 395 crop đề xuất, 22 nhãn trọng tài gốc,
và từng overlay của 83 vùng ảnh cuối. Loại các đề xuất lồng nhau cho
cùng người; giữ người bị che cùng đối tượng che khi còn nhận ra vai trò.
Ảnh mờ/chỉ thấy đầu mà chưa chắc vai trò được để trong `quarantine`.
Không biến các trường hợp đó thành âm tính hoặc nhãn player.

File `fixtures/referee_annotations_v2.json` lưu hash video/ảnh, frame,
ROI, bbox, lớp, màu áo, hướng nhìn, che khuất và hash crop gốc. Bbox dùng
pixel của ảnh gốc, gốc trái trên; không phải tọa độ mét sân. Không đổi
TrackingRow hoặc hợp đồng dữ liệu phân tích.

**Chỉ các vùng ROI được rà mới có nhãn. Phần ngoài ROI chưa gán nhãn.**
Không lấy cả frame vào train rồi coi mọi người chưa gán nhãn là nền.
Trong ROI có giữ các phần đối tượng lân cận bị cắt bởi mép crop; nhãn
được cắt về đúng ROI. Nhãn bbox có hỗ trợ của model, chưa vẽ/kiểm định
độc lập toàn bộ. 5 nhãn gốc bị nghi ngờ vẫn được giữ nguyên trong raw
và dataset v1; gói mới chỉ bỏ các vùng chưa rõ, chưa sửa lại cả frame
gốc hoặc tuyên bố dataset v1 đã sạch nhãn.

Trọng tài biên vẫn là lớp referee trong bộ nhãn ngữ nghĩa. Điều này
không cấp ID/phân tích sân cho người ngoài đường biên: bộ lọc biên sân
của sản phẩm giữ nguyên, không bị thay bằng gói nhãn này.

## Kiểm tra và dùng tiếp

Lệnh xác minh cả bytes nguồn, frame đã giải mã và crop đã rà:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.validate_referee_annotations `
  --packet docs/fixtures/referee_annotations_v2.json --verify-assets
```

Không có video/ảnh local vẫn có thể bỏ `--verify-assets` để kiểm cấu
trúc và phạm vi chia nguồn. Bộ kiểm từ chối nguồn test/validation,
video đổi tên nhưng hash không khớp nguồn đã khóa, frame đã gán nhãn
được tính mới, bbox vượt ROI, đổi vai trò chính, và nhãn quarantine
lọt vào đối tượng phụ trong một crop khác. Không chấp nhận tuyên bố
“đã kiểm độc lập” hoặc “cả frame sẵn sàng học” từ dữ liệu hiện tại.

Snapshot: `fixtures/referee_annotation_audit_v2.json`.
Ảnh/crop/sheet local: `data/processed/referee_annotation_v2/regions-0.jpg`,
`regions-1.jpg`, `regions-2.jpg` và các PNG gốc/crop theo ID. Chỉ metadata
tọa độ/nhãn và mã kiểm được commit, không commit video hoặc ảnh.

Bước 2 tiếp theo mới chuyển các ROI đủ điều kiện sang dataset phiên bản
mới và cân bằng mẫu trong train. Khi đó cần giữ số mẫu thật riêng với
số crop/lượt lặp, kiểm lại nhãn đối tượng bị cắt và giữ nguyên các vùng
chưa chắc chắn. Bộ nhãn còn lệch về áo xanh và mẫu đen chỉ có một lượt;
chưa thể dự đoán recall sẽ tăng bao nhiêu trước khi huấn luyện/đánh giá.

Kiểm tra mã: 13 test mới và toàn bộ **502 test Python đạt**, 1 network
test deselected, 4 warning thư viện hiện có. Kiểm bytes nguồn/ảnh/crop
đạt trên gói nhãn cuối; không dùng test mã để kết luận nhãn đã đúng độc lập.

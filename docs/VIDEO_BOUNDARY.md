# Lọc người ngoài sân theo vạch trắng

Ngày 29/10/2026, áp dụng cho upload và mẫu Video Project 15.

`backend/cv/pitch_boundary.py` dùng vùng cỏ lớn, cạnh Canny của vạch
trắng và đoạn thẳng Hough để giới hạn sân. Bắt buộc thấy biên dài phía
gần/xa; dùng biên cuối sân khi thấy nó nối vào góc sân. Không lấy vạch
giữa sân, vùng cấm địa hoặc khu kỹ thuật làm biên ngoài. Rà bản đầu
phát hiện threshold màu đơn thuần nhận nhầm lối đi nhạt màu; đã thay
bằng cạnh ảnh thật trước bản nghiệm thu cuối.

Giữ người khi **điểm giữa đáy box** nằm trong vùng sân, không dùng tâm
thân người hoặc kéo tọa độ ngoài sân vào biên. Thiếu biên thì frame
không có người được theo dõi; không dùng polygon cũ xuyên camera lia.
Upload lọc cả mẫu màu áo và detection **trước ByteTrack**, kiểm tra lại
sau tracking trước khi ghi JSON. Bộ đếm/báo cáo chỉ dùng quan sát còn lại.

DTO frame nội bộ có `pitch_boundary` (polygon pixel hoặc null) để vẽ
nét đứt trắng trên video. Không đổi TrackingRow/EventRow/DATA_CONTRACT;
lọc biên ảnh không tự tạo tọa độ mét hoặc homography.

## Xử lý lại mẫu

Lệnh tạo job mới, giữ job/artifact gốc và ID của quan sát được giữ lại;
không tuyên bố chạy lại detector/tracker cho cache:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.filter_job_boundary data/processed/video_jobs/e0eb4128f58d45ea85c4ef0000ca92df
```

Job cuối `c140f8aefb4e4678b51fe6f633e1fc56`, nguồn SHA256
`f51735a042b493eba3cced891209fe1b6beb20ca80e20c340c7ede51900495d0`.
1511/1571 frame có vùng biên;60 frame không rõ biên bỏ theo dõi. Loại
9219 lượt ngoài biên/không đủ căn cứ, giữ30499 lượt/150 ID (không phải
150 cầu thủ). Đây là đếm thuật toán, không phải accuracy gán nhãn.
Chiếu lại sân bằng mốc và landmark check cũ; replay liên kết bóng với
người đã lọc; không chép báo cáo cũ sang job mới.

Ảnh rà nội bộ ở `data/processed/boundary_review_video15_v2/`, các frame
0,300,750,904,1200,1350,1500. Đã xem trực tiếp frame0,904,1350 để xác
nhận người ở khu kỹ thuật/trợ lý trọng tài ngoài biên không còn khung.
Đây là rà mẫu, chưa phải đánh giá độc lập mọi frame.

## Giới hạn và kiểm tra

Vạch mờ, cận cảnh hoặc che khuất có thể mất vùng biên và bỏ sót người.
Đáy box là xấp xỉ chân, người sát vạch vẫn cần rà mẫu. Tỷ lệ frame có
polygon không phải accuracy. Heatmap/quãng đường vẫn chỉ ở đoạn hiệu
chỉnh tay30–50s, chưa kiểm chứng sai số thực địa độc lập.

`tests/test_pitch_boundary.py` kiểm tra cỏ ngoài sân, lối đi nhạt màu,
vạch song song, biên cuối sân so với vạch cấm địa, đổi kích thước,
điểm chân thay vì tâm thân, thiếu biên, giữ artifact gốc và tích hợp
upload xác nhận người ngoài sân không vào ByteTrack.

320 test Python qua/1 network deselected với
`pytest -q --basetemp .tmp/pytest_boundary_edges_full_20261029`;
14 test frontend qua; build/lint qua với cảnh báo bundle/Fast Refresh cũ.

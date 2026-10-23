# Bước 5: baseline hình dạng đội hình

Ngày 23/10/2026. Đây là CLI phân tích ngoại tuyến, chưa tích hợp API/frontend,
không thay đổi `DATA_CONTRACT.md`. Chưa nghiệm thu toàn bộ bước 5.

## Phương pháp và đầu vào

Tái sử dụng loader Metrica đã có: sân 105 × 68 m, gốc trái dưới; bỏ bóng,
điểm thiếu và điểm ngoài sân. Chỉ đọc một hiệp, một đội, một khoảng thời gian.
Không ghép danh tính Metrica với StatsBomb vì không phải cùng trận/cầu thủ.

Người chạy phải chỉ định ID thủ môn và hướng tấn công (+1 hoặc -1).
Không suy đoán thủ môn chỉ từ màu áo hoặc tự gán hướng theo tên đội.
Trong lần chạy dưới đây, cấu hình từ vị trí quan sát trong hiệp 1:
Game 1: A thủ môn 11, hướng +1; B thủ môn 1025, hướng -1.
Game 2: A thủ môn 11, hướng -1; B thủ môn 1025, hướng +1.
Đây là giả định cấu hình cần kiểm tra lại khi đổi trận/hiệp, không phải
metadata chính thức của nguồn. ID đội B được loader cộng 1000.

Mỗi cửa sổ mặc định 10 giây phải có đúng 11 ID, gồm thủ môn, và ít nhất
80% số khung dự kiến có đủ cả 11 người đồng thời. Có thêm ID trong cửa sổ
(ví dụ thay người) thì từ chối thay vì trộn hai cầu thủ. Dùng trung vị vị trí
trên cùng tập khung đủ người; bỏ thủ môn khi tính hình dạng, tâm đội,
chiều rộng và chiều sâu. Vị trí trung vị là đại diện cửa sổ, không phải
đội hình tại một khung hình cụ thể. Không tính quãng đường từ các trung vị.

Sắp 10 cầu thủ theo x cùng hướng tấn công. Tách tuyến khi khoảng cách x
liên tiếp >6 m; khoảng cách 4–6 m được xem là mơ hồ và từ chối kết luận.
Chỉ nhận hình dạng có 3 hoặc 4 tuyến, mỗi tuyến tối đa 5 người và độ trải
x trong tuyến không quá 12 m. Đây là quy tắc hình học ban đầu, chưa học từ
dữ liệu hoặc hiệu chỉnh bằng nhãn chiến thuật. Các tham số lưu trong JSON.
Không có điểm tin cậy giả lập hay ép về một danh sách sơ đồ quen thuộc.

`observed_shape` chỉ nói số người trong các tuyến quan sát được; ví dụ
3-3-3-1 không khẳng định HLV sử dụng sơ đồ đó. `unknown` có lý do cụ thể,
không đồng nghĩa lỗi tracking. Chuyển pha, dồn bóng và vị trí chồng tuyến
có thể khiến quy tắc này không nhận diện được.

Tọa độ xuất vẫn giữ hệ sân ban đầu, không lật cả dữ liệu hoặc thay hợp đồng.
Hướng chỉ dùng sắp tuyến từ phía phòng ngự tới phía tấn công.

## Chạy lại

Từ gốc repo trong PowerShell, dùng file đầu ra mới nếu đã tồn tại:

```powershell
.\.venv\Scripts\python.exe -m backend.tactics.formation --input data/raw/metrica/Sample_Game_2_RawTrackingData_Home_Team.csv --output data/processed/formation_v1/game2_A.json --game 2 --team A --goalkeeper-id 11 --attack-direction -1 --start 60 --stop 120 --window 10
.\.venv\Scripts\python.exe -m pytest -q tests/test_formation.py --basetemp .tmp/pytest_formation_check
```

CLI chỉ cho đường dẫn trong repo, không ghi đè, lưu SHA256 nguồn, cấu hình,
hiệp/đội/thời gian, số khung cùng hiện diện, tỷ lệ bao phủ, vị trí cầu thủ,
các tuyến và chỉ số không gian. Không xuất tên cầu thủ hoặc tốc độ suy đoán.
Cửa sổ dư ngắn hơn `--window` không xử lý; số giây dư được ghi rõ.
JSON là báo cáo nội bộ `offline_spatial_shape_v1`, không phải `AnalysisResult`.

## Kết quả thực chạy

Bốn file Metrica Game 1/2 Home/Away sẵn có, hiệp 1, giây 60–120, sáu cửa
sổ 10 giây mỗi đội. Nguồn và hash đã khóa trong `fixtures/metrica_benchmark.json`;
SHA256 thực tế cũng ghi ở từng báo cáo cục bộ `data/processed/formation_v1/`.

| Dữ liệu | Hình dạng được xuất | Cửa sổ chưa xác định |
|---|---|---|
| Game 1 A | Không có | 6/6 |
| Game 1 B | Không có | 6/6 |
| Game 2 A | 90–100s: 3-3-3-1; 110–120s: 3-2-5 | 4/6 |
| Game 2 B | 100–110s: 4-2-4 | 5/6 |

Tổng 3/24 cửa sổ có hình dạng, 21/24 chưa xác định. Đây là tỷ lệ xuất kết
quả, **không phải độ chính xác**. Tỷ lệ từ chối cao cho thấy baseline còn
hạn chế, chưa phù hợp để trình bày như nhận diện sơ đồ chiến thuật tin cậy.
Không điều chỉnh ngưỡng để ép những cửa sổ này thành kết quả đẹp.

Kiểm thử có sơ đồ biết trước 4-4-2, 4-3-3, 4-2-3-1, 3-5-2 và đổi hướng;
thiếu người, thay ID, thiếu khung đồng thời, vị trí lỗi, đội trộn, ID trùng;
chạy CLI qua CSV kiểm tra đổi tọa độ, truy nguồn và chống ghi đè.

## Còn lại của bước 5

Cần tập cửa sổ được gán nhãn sơ đồ độc lập và tiêu chí đánh giá thực tế.
Đã thêm tùy chọn so khớp mẫu và đánh giá giả lập có nhãn, nhưng chưa thay
baseline mặc định; xem `FORMATION_TEMPLATE_EVALUATION.md`.
Đã bổ sung tham chiếu sơ đồ/lineup StatsBomb theo thời điểm
và bộ đối chiếu nhãn cùng trận trong `STATSBOMB_FORMATION_REFERENCE.md`;
chưa có quan sát tracking cùng trận để đánh giá bộ nhận diện thực tế.
Không dùng trận khác làm nhãn Metrica.
Đã thêm hồ sơ thống kê và báo cáo hai đội ngoại tuyến ở `STEP5_PLAYER_PROFILES.md`;
tích hợp giao diện vẫn chưa làm. Bước 5b, xG và advisor chưa bắt đầu.

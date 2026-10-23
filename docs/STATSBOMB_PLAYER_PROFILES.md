# Bước 5: hồ sơ sự kiện cầu thủ cùng lineup StatsBomb

Ngày 23/10/2026. Bổ sung báo cáo ngoại tuyến từ chính cache sự kiện
StatsBomb, nối lineup bằng ID trong cùng trận. Không ghép với người/ID
Metrica, không đổi schema/API hoặc thêm thư viện. Chưa tích hợp giao diện.

## Chỉ số

Mỗi cầu thủ có ID, tên đầy đủ, `short_name` theo helper hiện có, số áo nếu
được khai báo, cờ xuất phát từ Starting XI hiệp 1, cùng các số liệu:

- Số sự kiện có ID cầu thủ được ghi nhận: không gọi là số lần chạm bóng.
- Số đường chuyền, đường chuyền hoàn thành và tỷ lệ hoàn thành.
- Số sự kiện Carry, số cú sút và số cú sút có outcome Goal.
- Index của từng sự kiện Pass/Carry/Shot để truy lại nguồn.
- Ngữ cảnh vai trò và sơ đồ tại các mốc sự kiện, cùng số sự kiện trong
  từng ngữ cảnh; có cả trạng thái chưa xác định.

Không tính quãng đường/tốc độ từ vị trí sự kiện thưa, không đo phút thi
đấu hoặc vị trí trung bình ngoài bóng. Không thêm mô hình xG của bước 6.

Đường chuyền hoàn thành theo quy ước cache/pass-network hiện tại: Pass
có `pass_outcome` là None/NaN. Nếu thiếu cả cột outcome thì số hoàn thành
và tỷ lệ là null, không tự tính 100%. Không có lần chuyền thì tỷ lệ cũng
là null. Không giới hạn chỉ trước lần thay người như pass network mặc định.

`shot_goals` chỉ đếm Shot có outcome Goal, không tính phản lưới nhà vào
đó và không phải tỷ số trận. Loại các kỳ ngoài hiệp 1–4, gồm loạt luân
lưu, khỏi tổng cầu thủ. Thiếu cột shot_outcome thì shot_goals là null.

## Ghép lineup và danh tính

Tái sử dụng timeline Starting XI/Tactical Shift/nhân sự đã có. Đi theo
`index` sự kiện để tránh lấy Tactical Shift xảy ra sau một Pass có cùng
timestamp làm vai trò cho Pass đó. Sau thay người/Player Off/On hoặc thẻ
đỏ, giữ ngữ cảnh unknown tới bản tactics hợp lệ; không gán vai trò cũ
cho cầu thủ thay vào. ID không nằm trong lineup hiện tại cũng là unknown.
Các ngữ cảnh là tham chiếu được ghi nhận, không phải vị trí vật lý thực.

Giữ cầu thủ trong lineup dù không có sự kiện, và cầu thủ thay vào dù
chưa có sự kiện. Khóa thống kê là player_id, không phải tên: hai người
trùng tên vẫn có hai hồ sơ, short_name thêm ID để phân biệt. ID của một
cầu thủ không được xuất hiện ở hai đội trong cùng báo cáo. Không tự tạo
ID theo tên khi thiếu ID; ghi số dòng có tên nhưng thiếu ID trong audit.

## Nghiệm thu trên cache thật

Trận Brazil–Bỉ, match ID 8650, nguồn StatsBomb Open Data đã dùng từ bước 1.
Đã xuất 27 hồ sơ và đối chiếu trực tiếp các tổng với cache:

| Đội | Cầu thủ có hồ sơ | Chuyền | Hoàn thành | Cú sút | Shot outcome Goal |
|---|---:|---:|---:|---:|---:|
| Brazil | 14 | 532 | 459 | 25 | 1 |
| Belgium | 13 | 385 | 310 | 8 | 1 |

Không đọc cột cuối thành tỷ số: phản lưới nhà không thuộc số Shot Goal.
Có 3.527 sự kiện quy cho ID cầu thủ, không có dòng có tên nhưng thiếu ID
và không có sự kiện kỳ luân lưu trong cache này. Tổng sự kiện hồ sơ khớp
số dòng có ID ở hiệp 1–4; tổng Pass/hoàn thành/Shot/Shot Goal khớp theo đội.

Ví dụ trong báo cáo:

| Cầu thủ | Chuyền | Hoàn thành | Cú sút | Shot Goal |
|---|---:|---:|---:|---:|
| Kevin De Bruyne | 42 | 33 | 3 | 1 |
| Neymar da Silva Santos Junior | 60 | 51 | 3 | 0 |
| Philippe Coutinho Correia | 75 | 66 | 6 | 0 |
| Roberto Firmino Barbosa de Oliveira | 18 | 13 | 2 | 0 |

Các số liệu mô tả dữ liệu sự kiện, không phải đánh giá tổng thể năng lực
cầu thủ hoặc khuyến nghị HLV. Không dùng các cầu thủ/trận này để gán nhãn
chất lượng nhận diện đội hình trong Metrica.

## Chạy lại

Từ gốc repo, dùng file đầu ra mới:

```powershell
.\.venv\Scripts\python.exe -m backend.tactics.statsbomb_profiles --input data/processed/events_8650.csv --match-id 8650 --output data/processed/formation_v1/statsbomb_8650_player_profiles_v1.json
.\.venv\Scripts\python.exe -m pytest -q tests/test_statsbomb_profiles.py --basetemp .tmp/pytest_statsbomb_profiles_check
```

CLI không gọi mạng, chỉ đọc cache trong repo, kiểm tra đúng match ID và
không ghi đè. Báo cáo JSON nội bộ `statsbomb_player_profiles_v1` lưu hash
nguồn, timeline, hồ sơ và audit; không thay hợp đồng `AnalysisResult`.
Các index chứng cứ luôn quy về cache có hash đã lưu, không phải số dòng CSV.

6 test mới kiểm tra số có đáp án, cầu thủ zero-event, hai ID trùng tên,
vai trò cùng timestamp không nhìn trước, thiếu outcome, loại luân lưu/
không tính own goal thành Shot Goal, khác trận/khác đội/ID lỗi và CLI UTF-8.
Toàn bộ dự án: **252 passed, 1 network deselected**, cảnh báo Starlette cũ.

## Phạm vi bước 5 hiện có

Đã có hồ sơ di chuyển và hình dạng trên Metrica; tham chiếu vai trò cùng
Game 3; lineup theo thời điểm và hồ sơ sự kiện cùng trận StatsBomb. Các
chức năng này đều chạy ngoại tuyến, có kiểm thử/lệnh nghiệm thu.
Nhận diện sơ đồ trong trận thật vẫn thử nghiệm, chưa đạt đánh giá chiến
thuật độc lập; không nâng trạng thái chất lượng chỉ vì thêm hồ sơ sự kiện.
Giao diện thuộc bước 8, fine-tune YOLO thuộc bước 5b.

# Bước 5: tham chiếu vai trò từ chính nguồn Game 3

Ngày 23/10/2026. Bổ sung Game 3 để đối chiếu với metadata do nhà cung cấp
phát hành, thay vì tiếp tục chỉ dùng nhãn nháp agent. Đây là nguồn khác
Game 1/2; không chuyển vai trò hay sơ đồ sang các trận đó.

## Nguồn và ý nghĩa tham chiếu

Nguồn: **Metrica Sports Sample Data**, commit
`e706dd506b360d69d9d123d5b8026e7294b13996`.
[README chính thức](https://github.com/metrica-sports/sample-data/blob/e706dd506b360d69d9d123d5b8026e7294b13996/README.md)
giới thiệu Game 3 theo định dạng EPTS.
[Metadata XML](https://github.com/metrica-sports/sample-data/blob/e706dd506b360d69d9d123d5b8026e7294b13996/data/Sample_Game_3/Sample_Game_3_metadata.xml)
có vai trò, bố trí chuẩn hóa của vai trò, số áo, hướng tấn công, ánh xạ
kênh và cấu trúc bản ghi theo khoảng frame.

XML có 35 cầu thủ và 11 khoảng định dạng. Hai đội có thủ môn số áo 11 và
28; hướng hiệp 1 lần lượt -1/+1. Không dùng thủ môn 25 của Game 1/2 cho
Game 3. Tọa độ vai trò trong metadata là bố trí khai báo, **không phải vị
trí thực tế của cầu thủ ở từng frame**.

Tách rõ hai cấp độ nhóm vai trò từ metadata:

| Đội | Theo `position_index` | Theo các độ sâu `position_x` của vai trò |
|---|---|---|
| A | 4-5-1 | 4-2-3-1 |
| B | 4-4-2 | 4-4-2 |

Các chuỗi này là kết quả đếm nhóm do bộ đọc suy ra, không phải trường
formation đã được nhà cung cấp gán theo từng thời điểm. A có hai nhóm
tiền vệ ở độ sâu khác nhau dù cùng chỉ số tuyến. Chọn **độ sâu vai trò**
làm tiêu chí đối chiếu trước lần chạy; vẫn lưu cả cấp độ thô, không chọn
nhãn nào khớp dự đoán hơn sau khi xem kết quả.

Metadata là nguồn vai trò có thể truy xuất độc lập với thuật toán của
dự án. Tuy nhiên nó chưa xác nhận sơ đồ quan sát trong mọi pha bóng;
bản ghi không phải nhãn chiến thuật từng frame hoặc bằng chứng sơ đồ
không thay đổi suốt trận. Giữ `is_frame_tactical_ground_truth: false`.

## Bộ đọc

`backend/tactics/metrica_game3.py` đọc đúng biến thể EPTS của file nguồn
đã khóa; không tuyên bố hỗ trợ mọi biến thể FIFA EPTS, không cài kloppy.

- Giải mã cột bằng `PlayerChannelRef → PlayerChannel → Player id → số áo`.
  Ví dụ cột đầu `player1_x/y` thuộc P3578, số áo 11; không phải số áo 1.
- Mỗi khoảng frame có danh sách cột riêng; tra lại khi thay người. Cửa
  sổ đi qua ranh giới định dạng không được dùng như một lineup duy nhất.
  Danh sách kênh là danh sách được khai báo, không thay kiểm tra hiện diện.
- Giữ ID cục bộ theo trận: số áo đội A, đội B cộng 1000. Không ánh xạ
  sang người thật, StatsBomb hoặc cùng số áo trong trận khác.
- Tọa độ tracking chuẩn hóa đổi thành x×105, (1−y)×68. Bỏ NaN/ngoài sân,
  không nội suy; giữ frame thật và tách segment khi thiếu frame.
- Thời gian là `(frame − frame_đầu_hiệp)/25`; hiệp 2 bắt đầu từ 0 theo
  quy ước bộ đọc này. Không nhầm với clock toàn trận của dữ liệu khác.
- Dữ liệu đọc tuần tự, chỉ giữ khoảng yêu cầu trong RAM; không tải cả
  53 MB tracking thành một bảng. Bỏ phần bóng, không thêm phân tích bóng.

Bộ nhận diện nhận tọa độ, ID thủ môn và hướng; nhãn độ sâu vai trò chỉ
dùng sau đó để đối chiếu, không đưa vào hàm nhận diện để ép kết quả.
Giữ nguyên thuật toán/ngưỡng và mặc định gap. Không đổi API/schema/thư viện.

## Kết quả lần đầu trên cùng trận

Hiệp 1, giây 60–180, 12 cửa sổ mỗi đội, tổng 24 cửa sổ:

| Phương pháp | Khớp bố trí vai trò khai báo | Khác bố trí vai trò | Chưa xác định |
|---|---:|---:|---:|
| Gap | 0 | 2 | 22 |
| Template | 0 | 0 | 24 |
| Aligned | 2 | 1 | 21 |

Aligned khớp 4-2-3-1 ở A 120–130s và A 150–160s. Ở B 70–80s, aligned
ra 4-1-4-1, khác bố trí vai trò 4-4-2. Không tự gọi khác biệt đó là lỗi
chiến thuật đã xác nhận: bố trí quan sát trong pha bóng có thể khác vai
trò khai báo. Không coi 21 lần chưa xác định là đúng hoặc loại khỏi mẫu
số để làm kết quả trông tốt hơn. Đây là đối chiếu metadata cùng trận,
**không phải accuracy nhận diện sơ đồ chiến thuật từng thời điểm**.

Game 3 chưa được dùng chỉnh thuật toán trước lần đối chiếu này. Kết quả
hiện đã được xem; không dùng lại như tập kiểm định chưa từng xem nếu sau
này tinh chỉnh theo chính các cửa sổ này.

## Truy nguồn và tái lập

Hai file cục bộ ở `data/raw/metrica/`: metadata 81.806 byte và tracking
53.443.115 byte. Lúc tải đã đối chiếu kích thước và Git blob SHA1 với
cây nguồn tại commit khóa, rồi lưu SHA256 vào
`fixtures/metrica_game3_sources.json`. CLI chạy ngoại tuyến kiểm tra hash.
XML nguyên bản và chín bản ghi tracking nhỏ được commit để kiểm thử
không cần tải dữ liệu lớn. `.gitattributes` giữ nguyên byte hai fixture,
tránh LF/CRLF làm sai hash. Không sửa manifest nguồn Game 1/2.

Từ gốc repo, dùng tên đầu ra mới:

```powershell
.\.venv\Scripts\python.exe -m backend.tactics.metrica_game3 --output data/processed/formation_v1/game3_role_comparison_60_180_v1.json
.\.venv\Scripts\python.exe -m pytest -q tests/test_metrica_game3.py --basetemp .tmp/pytest_game3_check
```

JSON lưu nguồn/hash, khoảng hiệp/thời gian, tham chiếu hai cấp độ và từng
dự đoán. Chỉ ghi file mới trong repo. Không tự tải file khi chạy CLI/test.

9 test mới: hash nguồn, hai cấp độ vai trò, ID thủ môn, ánh xạ cột khác
số áo, đổi tọa độ, clock hiệp 2, thay người, XML sai, thiếu/ngoài sân và
ngắt segment. Toàn bộ dự án: **246 passed, 1 network deselected**, cảnh báo
Starlette cũ. Chức năng bước 5 có thêm tham chiếu có nguồn rõ ràng; phần
nghiệm thu chiến thuật vẫn cần nhãn quan sát theo thời điểm phù hợp mục tiêu.

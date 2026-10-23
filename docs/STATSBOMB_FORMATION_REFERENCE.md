# Bước 5: tham chiếu sơ đồ StatsBomb theo thời điểm

Ngày 23/10/2026. Thêm module ngoại tuyến
`backend/tactics/statsbomb_formation.py`; không đổi API, schema hay thư viện.
Đọc cache CSV có sẵn, không gọi mạng khi chạy CLI hoặc test.

## Nguồn và quy ước

Dữ liệu: **StatsBomb Open Data**, trận Brazil–Bỉ World Cup 2018, match ID
8650. Tham khảo [đặc tả StatsBomb v1.1](https://github.com/statsbomb/open-data/blob/master/doc/StatsBomb%20Open%20Data%20Specification%20v1.1.pdf)
về `Starting XI`, `Tactical Shift` và cấu trúc `tactics`.
Hai loại sự kiện này cung cấp sơ đồ và vị trí/vai trò cầu thủ; chúng không
cung cấp vị trí tracking liên tục để đo độ đúng của bộ nhận diện Metrica.

Fixture `fixtures/statsbomb_8650_tactics.json` trích 14 sự kiện liên quan
từ cache cục bộ `events_8650.csv`, giữ ID sự kiện, index, hiệp, timestamp,
đội và tactics; có ghi hash cache nguồn. Đây là bản trích cache đã chuẩn
hóa của dự án, không tuyên bố là bản JSON gốc khóa theo commit upstream.
SHA256 cache khi chạy:
`3242a723defb57cdfc46121ded0a43c7e55ffd8e75ad90c321bbee4308a9e495`.

Cache có thể được sắp theo loại sự kiện; module bắt buộc sắp lại theo
`index`, kiểm tra trùng index và thứ tự thời gian của các mốc từng đội.
Dùng `(period, timestamp)`; timestamp là thời gian trong hiệp, không lấy
`minute` toàn trận làm số giây trong hiệp. Cùng timestamp thì mốc index
sau cùng có hiệu lực khi truy vấn. Không xử lý loạt luân lưu (hiệp 5).

## Hành vi

- `Starting XI`/`Tactical Shift` hợp lệ tạo mốc tham chiếu: đúng 11 cầu
  thủ, ID không trùng, đúng một thủ môn, tổng số người ngoài sân trong
  mã sơ đồ bằng 10. Chuyển `433` thành nhãn `4-3-3`.
- Sau `Substitution`, `Player Off`, `Player On`, thẻ đỏ hoặc thẻ vàng thứ
  hai: trạng thái chưa xác định cho tới mốc tactics hợp lệ tiếp theo.
  Không mặc định cầu thủ mới có vai trò cũ hoặc tự khôi phục sau Player On.
  Cách này thận trọng, có thể bỏ nhiều khoảng vẫn có sơ đồ trên thực tế.
- Sang hiệp mới, mốc trước đó được kế thừa nếu chưa có thay đổi được ghi
  nhận. Không diễn giải điều này thành xác nhận mọi điều chỉnh chiến thuật
  ngoài dữ liệu đều đã được quan sát.
- `reference_at` trả mốc có hiệu lực gần nhất, kể cả trạng thái chưa xác
  định. Không có mốc trước đó thì không suy diễn đội hình.
- `compare_window` chỉ cho cùng match ID, đội và hiệp được yêu cầu. Khoảng
  thời gian là `[start_s, stop_s)`; có mốc mới nằm bên trong thì không chấm.
  Cửa sổ thiếu tham chiếu hoặc nhận diện chưa xác định cũng không chấm.
  Nhãn quan sát khác nhãn tham chiếu được ghi không đồng ý, không sửa nhãn.

Đây là bộ đối chiếu **nhãn sơ đồ**. Caller phải cung cấp đúng thông tin
trận/đội/hiệp của quan sát; module không xác thực danh tính video từ nội dung.
Không ghép ID cầu thủ giữa Metrica và StatsBomb. Chưa có bộ quan sát tracking
cùng trận 8650 để báo cáo accuracy, precision hoặc recall thực tế.

## Chạy và kết quả

Từ gốc repo, dùng tên đầu ra mới nếu file đã tồn tại:

```powershell
.\.venv\Scripts\python.exe -m backend.tactics.statsbomb_formation --input data/processed/events_8650.csv --output data/processed/formation_v1/statsbomb_8650_reference.json --match-id 8650
.\.venv\Scripts\python.exe -m pytest -q tests/test_statsbomb_formation.py --basetemp .tmp/pytest_statsbomb_reference_check
```

CLI xuất 14 mốc từ cache thật: 2 Starting XI, 3 Tactical Shift, 5 thay
người và 4 Player Off/On. Đầu trận cả hai đội có nhãn 4-3-3 trong nguồn.
Bỉ thay người ở hiệp 2 giây 2227,360, trạng thái tạm chưa xác định; mốc
Tactical Shift ở giây 2234,280 cung cấp 5-3-2. Sau lần thay người tiếp theo,
mốc giây 2493,067 cập nhật lineup có Youri Tielemans. Không dùng thời gian
hiệp 1 bù giờ để ghi đè các mốc đầu hiệp 2.

Báo cáo JSON lưu hash và đường dẫn cache trong repo. CLI không ghi đè;
không chấp nhận đầu vào/đầu ra ngoài repo. Tactics trong cache pandas được
đọc bằng JSON hoặc `ast.literal_eval`, không thực thi mã.

12 test mới kiểm tra các mốc thật, thay người/thẻ đỏ, cùng timestamp,
thứ tự index, ranh giới cửa sổ, cùng trận, quan sát khác/thiếu, tactics
lỗi, timestamp lỗi và CLI. Các test xác nhận thao tác dữ liệu tham chiếu;
không phải bằng chứng mô hình nhận diện đạt độ chính xác chiến thuật.

## Việc tiếp theo

Đã có phần tham chiếu theo thời điểm cho bước 5. Còn bộ nhận diện tốt hơn
và tập quan sát gán nhãn độc lập để đánh giá; baseline Metrica vẫn giữ
nguyên 3/24 cửa sổ có kết quả. Chỉ số cầu thủ và giao diện chưa hoàn tất.
Không lấy nhãn 4-3-3 hoặc 5-3-2 của trận này làm nhãn cho Metrica khác trận.

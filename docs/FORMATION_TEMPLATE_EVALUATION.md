# Bước 5: so khớp mẫu và đánh giá hình dạng

Ngày 23/10/2026. Thêm phương pháp `template` bên cạnh `gap` hiện tại.
Giữ **gap làm mặc định**: chưa có bằng chứng thực tế để thay phương pháp.
Không đổi API/schema, không thêm thư viện, không sửa chính sách chuyển động.

## Phương pháp mới

`formation_templates.py` dùng sáu mẫu hình học do dự án tự định nghĩa:
4-3-3, 4-4-2, 4-2-3-1, 4-1-4-1, 5-3-2 và 3-5-2. Mẫu có các tuyến cách
đều theo chiều dọc, cầu thủ trong tuyến trải đều theo chiều ngang; một
cầu thủ trong tuyến đặt ở giữa. Đây không phải tọa độ chiến thuật chính
thức của StatsBomb hoặc bộ mẫu được học từ trận đấu.

Bỏ thủ môn, trừ tâm đội rồi chia từng trục cho độ lệch chuẩn để so hình
dạng tương đối. Hướng tấn công chỉ dùng cho phép so khớp nội bộ, tọa độ
xuất vẫn giữ nguyên hệ sân 105 × 68 m. Tìm phép ghép một-một 10 cầu thủ
với 10 vị trí mẫu có tổng bình phương khoảng cách nhỏ nhất bằng quy hoạch
động tập con (1024 trạng thái). Ghép chính xác trong bài toán hình học
này không có nghĩa vai trò cầu thủ ngoài thực tế đã được xác định đúng.

Điều kiện xuất kết quả:

- Các guard cũ vẫn áp dụng: đúng 11 ID gồm thủ môn, >=80% khung đồng thời
  đủ người, không trộn nhân sự thay người trong một cửa sổ.
- Độ sâu ít nhất 15 m, chiều rộng ít nhất 20 m; quá co cụm thì từ chối.
- RMSE trong hệ đã chuẩn hóa không quá 0,45.
- Điểm mẫu thứ hai trừ điểm mẫu tốt nhất ít nhất 0,08; gần nhau thì từ chối.

Các ngưỡng là heuristic ban đầu, chưa được hiệu chỉnh bằng nhãn độc lập.
Không dùng tỷ lệ 2/24 để điều chỉnh cho ra nhiều nhãn hơn. Điểm và chênh
lệch điểm không phải xác suất hay độ tin cậy đã được hiệu chuẩn.
Danh mục đóng có thể gán sai một đội hình nằm ngoài sáu mẫu nếu hình dạng
gần giống; điều kiện từ chối không bảo đảm phát hiện mọi mẫu ngoài danh mục.
Lấy trung vị cửa sổ và chuẩn hóa riêng từng trục cũng có thể làm mất khác
biệt chiến thuật, hoặc che khuất việc đổi vị trí trong cửa sổ.

## Bộ đánh giá và nguồn nhãn

`fixtures/formation_template_cases.json` có sáu bố trí tự dựng có nhãn theo
số người từng tuyến, một bố trí co cụm và một trường hợp thiếu cầu thủ.
Thêm nhiễu 0,75 m với seed 7/19/41, ba phép đổi hướng/co giãn tạo 72 ca:
54 ca có nhãn sơ đồ và 18 ca kỳ vọng chưa xác định. Trục x được co giãn
1,0 hoặc 0,8 hoặc 1,05 quanh tâm sân; trục y tương ứng 1,0/0,9/0,8.
Đây là các ca hình học gần giả thiết mô hình, không phải nhãn người dùng,
tập kiểm định thực tế độc lập hoặc bằng chứng khái quát hóa của mô hình.

`fixtures/metrica_formation_windows.json` khóa vị trí đại diện của 24 cửa
sổ đã chạy trước đó, hash hai báo cáo và hash bốn file nguồn. Các trường
tham chiếu đều là `label_status: unreviewed`, `shape: null`, không có tên
người đánh giá. **Null ở đây là chưa gán nhãn, không phải nhãn thật unknown.**
Kết quả gap cũ trong fixture là dự đoán, không được dùng làm nhãn để chấm
template. Không lấy nhãn StatsBomb khác trận thay cho nhãn Metrica.

Nhờ fixture, CLI đánh giá chạy ngoại tuyến không cần tải video hoặc bốn
CSV lớn. Lưu hash fixture và báo cáo đầu vào trong kết quả để truy nguồn.

## Kết quả

| Phép kiểm tra | Gap | Template |
|---|---:|---:|
| Đúng trong 54 ca giả lập có sơ đồ | 52 | 54 |
| Chưa xác định trong 54 ca có sơ đồ | 2 | 0 |
| Xuất sai nhãn trên 18 ca kỳ vọng chưa xác định | 0 | 0 |
| Xuất hình dạng trên 24 cửa sổ Metrica chưa gán nhãn | 3 | 2 |

Các kết quả đã xuất trên giả lập đều đúng trong phạm vi bộ ca này; không
diễn giải thành nhận diện chiến thuật thực tế đạt 100%. Báo cáo JSON có
ma trận nhầm lẫn, số ca không xuất nhãn và nguồn nhãn rõ ràng.

Hai kết quả template trên Metrica:

- Game 2 A, giây 70–80: 4-1-4-1, chênh điểm khoảng 0,091.
- Game 2 B, giây 110–120: 4-4-2, chênh điểm khoảng 0,081.

Đây là hai cửa sổ khác với ba kết quả gap. Chưa có nhãn thật để gọi bên
nào đúng. Trong 22 cửa sổ template chưa xác định: 12 khớp mẫu kém, 3 quá
co cụm, 2 mơ hồ giữa mẫu, 4 thiếu bao phủ đồng thời và 1 thiếu/đổi nhân sự.
Kiểm tra ngưỡng chênh điểm 0,04 / 0,08 / 0,12 cho số kết quả lần lượt
2 / 2 / 0; hai kết quả không ổn định khi yêu cầu phân biệt mẫu chặt hơn.
Không chọn ngưỡng 0,04 chỉ để tăng số kết quả.

## Lệnh chạy

Từ gốc repo, chọn tên đầu ra mới nếu đã tồn tại:

```powershell
# Đánh giá ngoại tuyến bằng fixture đã commit
.\.venv\Scripts\python.exe -m backend.tactics.evaluate_formation --output data/processed/formation_v1/template_comparison_frozen_v1.json

# Tính lại từ CSV thật với phương pháp mới, vẫn có hồ sơ cầu thủ
.\.venv\Scripts\python.exe -m backend.tactics.metrica_report --game 2 --home-goalkeeper 11 --away-goalkeeper 1025 --home-direction -1 --formation-method template --output data/processed/formation_v1/game2_tactics_templates_v1.json

# So trên các báo cáo khác cùng cấu trúc, nếu cần
.\.venv\Scripts\python.exe -m backend.tactics.evaluate_formation --reports data/processed/formation_v1/game1_tactics_profiles.json data/processed/formation_v1/game2_tactics_profiles.json --output data/processed/formation_v1/template_comparison_v1.json
```

Đã chạy lại CSV thật cả Game 1/2, xuất 44 hồ sơ với tùy chọn template.
Test kiểm tra phép ghép với vét cạn, các bố trí có nhãn, đổi hướng/thứ tự
ID, bảo toàn guard cửa sổ, từ chối mơ hồ, tái lập đánh giá và CLI ngoại tuyến.

## Kết luận sử dụng

Template là phương án thử nghiệm có thể giải thích và đối chiếu được;
chưa thay gap mặc định. Chưa nghiệm thu chất lượng chiến thuật của bước 5.
Bước cần thiết tiếp theo là gán nhãn cùng tập tracking theo một tiêu chí
thống nhất, tách phần dùng phát triển và phần đánh giá trước khi chỉnh
tham số. Nên có người đánh giá độc lập; nhãn tự dựng hoặc agent tự nhận
xét cần giữ rõ nguồn, không thay thế đánh giá độc lập.

Đã rà nháp 24 cửa sổ và kiểm tra thêm 15 ảnh thời điểm; kết quả đối chiếu
với nhãn agent ở `FORMATION_AGENT_REVIEW.md`. Không dùng các nhãn nháp đó
để đổi ngưỡng trong đợt này hoặc thay cho đánh giá độc lập.

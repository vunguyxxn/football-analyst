# Bước 5: báo cáo đội hình và chỉ số cầu thủ

Ngày 23/10/2026. CLI `backend/tactics/metrica_report.py` kết hợp bộ nhận
diện hình dạng đã có với hồ sơ cầu thủ của cả hai đội Metrica. Không đổi
API/schema; chưa tích hợp giao diện (thuộc bước 8). Dữ liệu JSON là báo
cáo nội bộ `offline_metrica_tactics_v1`, không gắn nguồn Metrica thành video.

## Chạy

Từ gốc repo, mỗi lần chạy dùng file đầu ra mới:

```powershell
.\.venv\Scripts\python.exe -m backend.tactics.metrica_report --game 1 --home-goalkeeper 11 --away-goalkeeper 1025 --home-direction 1 --output data/processed/formation_v1/game1_tactics_profiles.json
.\.venv\Scripts\python.exe -m backend.tactics.metrica_report --game 2 --home-goalkeeper 11 --away-goalkeeper 1025 --home-direction -1 --output data/processed/formation_v1/game2_tactics_profiles.json
.\.venv\Scripts\python.exe -m pytest -q tests/test_metrica_report.py --basetemp .tmp/pytest_player_profiles_check
```

Mặc định hiệp 1, giây 60–120, cửa sổ hình dạng 10 giây. Home=A, Away=B;
ID đội B cộng 1000 theo loader. Hướng Away ngược Home. Thủ môn và hướng
là cấu hình từ lần quan sát trước, cần kiểm tra lại nếu đổi hiệp/trận.
Các giả định được nêu ở `FORMATION_BASELINE.md`.

CLI đọc hai file CSV cục bộ, đối chiếu SHA256 với manifest Metrica đã khóa
`fixtures/metrica_benchmark.json` trước khi tính. Không tải dữ liệu, không
ghi đè, chỉ cho đường dẫn trong repo. Kết quả giữ hash từng nguồn, khoảng
thời gian, hiệp, đội, cấu hình, thống kê loader và cả cửa sổ chưa xác định.

## Chỉ số và ý nghĩa

Mỗi ID có nhãn đội/thủ môn, số mẫu, tỷ lệ khung có dữ liệu, vị trí trung vị
và heatmap 21 × 14 ô theo hệ sân 105 × 68 m, gốc trái dưới. Heatmap đếm
khung quan sát hợp lệ trong sân; không nội suy và không phải xác suất.
Vị trí trung vị/heatmap vẫn dùng các mẫu vị trí ngay cả khi khoảng chuyển
động liên quan bị loại bởi ngưỡng tốc độ.

Chuyển động tái sử dụng `PitchMetrics` với khoảng lấy mẫu tối thiểu 0,5 giây
(25 FPS có thể thành 0,52 giây), giới hạn 40 km/h. Mỗi khoảng được tính
bằng đoạn thẳng nối hai mốc, nên có thể bỏ qua đường cong khi đổi hướng.
Báo cáo xuất quãng đường quan sát được, thời gian thực sự đại diện bởi các
khoảng được nhận, tốc độ trung bình và tốc độ lớn nhất trên các khoảng đó.
Tốc độ lớn nhất này không phải tốc độ tức thời từng khung.

Thiếu dù chỉ một khung cũng ngắt chuỗi; đổi segment cũng ngắt. Không nối
qua khoảng mất dấu, không ngoại suy phần cuối chưa đủ 0,5 giây. Khoảng
vượt 40 km/h bị loại và ngắt chuỗi, không ép về 40. Không có khoảng hợp
lệ thì tốc độ là `null`; đứng yên có đủ thời gian thì tốc độ bằng 0.

Phân biệt ba đại lượng:

- `sample_coverage`: số khung có dữ liệu / số khung dự kiến trong cửa sổ.
- `observed_continuous_duration_s`: tổng thời gian giữa các cặp khung liền
  nhau cùng segment, trước khi kiểm tra tốc độ.
- `represented_motion_duration_s`: thời gian của các khoảng thực sự được
  nhận để tính chuyển động; `represented_window_fraction` chia cho toàn
  thời lượng yêu cầu. Không lấy quãng đường từng phần nhân bù lên 90 phút.

Hồ sơ là từng ID trong đúng trận/hiệp/đội đã chỉ định. Không gán tên thật
cho ID Metrica, không so xếp hạng cầu thủ khi mức bao phủ khác nhau mà bỏ
qua mức bao phủ. Số mét/km/h mô tả nguồn tọa độ Metrica, không chứng minh
độ chính xác vật lý của video hay của chính nguồn này.

## Nghiệm thu dữ liệu thật

Đã chạy hai trận, mỗi trận 22 hồ sơ, tổng **44 hồ sơ**; khoảng giây 60–120.
Các tỷ lệ dưới đây là giá trị thấp nhất trong 11 cầu thủ mỗi đội, còn tốc
độ là giá trị lớn nhất được nhận của đội. Không phải chỉ số toàn trận.

| Trận/đội | Bao phủ khung thấp nhất | Tỷ lệ thời gian chuyển động thấp nhất | Tốc độ lớn nhất (km/h) | Khoảng vượt ngưỡng bị loại |
|---|---:|---:|---:|---:|
| Game 1 A | 86,3% | 84,9% | 30,84 | 2 |
| Game 1 B | 82,7% | 82,3% | 21,04 | 0 |
| Game 2 A | 98,5% | 97,9% | 21,92 | 0 |
| Game 2 B | 100,0% | 99,7% | 27,34 | 0 |

Ví dụ để kiểm tra báo cáo:

| Trận/đội/ID | Quãng đường nhận (m) | Thời gian đại diện (s) | Tốc độ trung bình (km/h) |
|---|---:|---:|---:|
| Game 1 A / 4 | 117,83 | 55,64 | 7,62 |
| Game 1 B / 1024 | 103,45 | 59,80 | 6,23 |
| Game 2 A / 6 | 156,66 | 59,80 | 9,43 |
| Game 2 B / 1021 | 157,76 | 59,80 | 9,50 |

Các cửa sổ hình dạng vẫn cho kết quả cũ: 3/24 có hình dạng, 21/24 chưa xác
định. Báo cáo mới không điều chỉnh ngưỡng để tăng tỷ lệ xuất sơ đồ.

7 test mới: chuyển động có đáp án số biết trước, ngắt khoảng thiếu ngắn,
loại teleport, phân biệt đứng yên/thiếu thời gian, cắt cửa sổ, tọa độ lỗi,
kết hợp cả đội, CLI hai nguồn/khóa hash/truy nguồn/chống ghi đè.
Toàn bộ dự án: **195 passed, 1 network deselected**, cảnh báo Starlette cũ.

## Trạng thái bước 5

Đã có ba phần chạy ngoại tuyến: hình dạng đội hình Metrica; tham chiếu
và đối chiếu nhãn StatsBomb theo thời điểm; hồ sơ cầu thủ và báo cáo hai
đội. Đã kiểm tra chức năng bằng test và chạy dữ liệu thật.

**Chưa nghiệm thu chất lượng nhận diện sơ đồ chiến thuật.** Tỷ lệ từ chối
21/24 còn cao; thiếu nhãn sơ đồ độc lập trên cùng tập tracking để đánh giá
độ đúng. StatsBomb và Metrica khác trận nên không dùng thay nhãn cho nhau.
Giao diện thuộc bước 8; bước 5b, xG và advisor chưa bắt đầu.

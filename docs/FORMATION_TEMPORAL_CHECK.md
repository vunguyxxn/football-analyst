# Bước 5: kiểm tra độ ổn định trên cửa sổ mới

Ngày 23/10/2026. Đợt này kiểm tra giây **120–180**, hiệp 1, cả hai đội
Game 1/2 Metrica: 24 cửa sổ 10 giây không trùng 24 cửa sổ giây 60–120 đã
phát triển/rà nháp. Không có nhãn tham chiếu độc lập ở tập mới, không gọi
đây là đánh giá accuracy hoặc tập kiểm định chiến thuật có nhãn.

## Phép kiểm tra

Protocol được lưu trước lần chạy trong `fixtures/formation_stability_protocol.json`.
Giữ nguyên hai thuật toán, mẫu và ngưỡng hiện tại. Thủ môn/hướng hiệp 1
dùng cấu hình đã nêu ở `FORMATION_BASELINE.md`; chưa xác nhận bằng metadata
chính thức. Không cập nhật mặc định của CLI báo cáo hoặc API/schema.

Với mỗi cửa sổ đạt guard cũ (11 ID gồm thủ môn, >=80% khung đồng thời đủ
người), so nhãn từ vị trí trung vị với năm ảnh vị trí thực ở giây tương
đối 1, 3, 5, 7, 9. Chọn khung đủ người gần nhất, sai lệch thời gian tối
đa 0,08 giây; không chọn một khung xa hơn để lấp chỗ thiếu và không dùng
lại cùng một khung cho hai thời điểm. Khung phải nằm trong đúng cửa sổ.

Chỉ ghi `temporally_supported` nếu:

- Nhãn từ trung vị đã được xuất, không dùng ảnh thời điểm để ép một nhãn
  khi trung vị chưa xác định.
- Có đủ năm ảnh theo lịch. Một thời điểm thiếu dữ liệu làm phép kiểm tra
  không đạt, dù bốn ảnh còn lại giống nhau.
- Ít nhất 4/5 ảnh xuất chính nhãn trung vị. Ảnh đủ người nhưng thuật toán
  trả unknown vẫn nằm trong mẫu số 5, không loại đi để tăng tỷ lệ.

Ví dụ 3 ảnh là 4-4-2 và 2 ảnh unknown thì không đạt. Bốn ảnh 4-4-2 và một
ảnh unknown hoặc một nhãn khác thì đạt quy tắc 4/5, nhưng trường hợp khác
nhãn vẫn được ghi trong thống kê. Đây là quy tắc chẩn đoán heuristic,
không bảo đảm nhãn đúng hoặc sơ đồ được duy trì ở mọi khung chưa lấy mẫu.

Không có nhãn đạt quy tắc cũng không chứng minh HLV không có sơ đồ ổn
định; bộ nhận diện ảnh thời điểm có thể quá hạn chế hoặc quá nhạy ngưỡng.
Sự đồng thuận của cùng một thuật toán trên nhiều ảnh không phải nhãn thật.

## Kết quả thực chạy

| Phương pháp | Cửa sổ xuất nhãn trung vị | Nhãn đạt quy tắc 4/5 |
|---|---:|---:|
| Gap | 2/24 | 0/24 |
| Template | 3/24 | 0/24 |

Ba cửa sổ bị guard chất lượng loại trước phép kiểm tra: Game 1 A 170–180,
Game 1 B 120–130 và Game 2 A 130–140. Còn 21 cửa sổ, 105 thời điểm lên
lịch; 104 thời điểm có khung trong dung sai. Thời điểm thiếu ở cửa sổ
có trung vị unknown, không phải nguyên nhân loại năm nhãn trung vị bên dưới.

| Cửa sổ | Phương pháp | Nhãn trung vị | Ảnh đồng ý / 5 |
|---|---|---|---:|
| Game 1 A 120–130 | Gap | 1-4-1-4 | 0 |
| Game 1 A 130–140 | Gap | 3-2-5 | 0 |
| Game 1 A 140–150 | Template | 4-4-2 | 1 |
| Game 2 A 120–130 | Template | 4-1-4-1 | 2 |
| Game 2 B 160–170 | Template | 4-4-2 | 2 |

Gap ở Game 1 A 130–140 có một ảnh ra 3-3-3-1, bốn ảnh unknown. Các ảnh
còn lại không đồng ý với năm nhãn trung vị đều là unknown. Không sửa
ngưỡng để các nhãn này vượt kiểm tra và không tự gọi chúng là nhãn sai.

## Chạy lại và kiểm thử

Từ gốc repo, dùng file đầu ra mới:

```powershell
.\.venv\Scripts\python.exe -m backend.tactics.formation_stability --output data/processed/formation_v1/stability_120_180_v1.json
.\.venv\Scripts\python.exe -m pytest -q tests/test_formation_stability.py --basetemp .tmp/pytest_stability_check
```

CLI dùng bốn CSV sẵn có, kiểm tra SHA256 theo manifest đã khóa. JSON lưu
hash protocol, cấu hình, nguồn/audit loader, tọa độ và kết quả từng ảnh,
nhãn trung vị, số ảnh đồng ý và lý do chưa đạt. Chỉ ghi file mới trong
repo. Không tải dữ liệu, không thêm thư viện, không thay thuật toán gốc.

6 test mới: mẫu đứng yên biết trước; đổi bố trí thoáng qua trong khi trung
vị vẫn không đổi; mẫu số có unknown; không nâng nhãn trung vị unknown;
khoảng thiếu nhỏ/dung sai thời gian; guard chất lượng; protocol lệch mã,
hash nguồn sai và chống ghi đè. Kiểm thử chức năng này không đo accuracy.
Toàn bộ dự án: **224 passed, 1 network deselected**, cảnh báo Starlette cũ.

## Quyết định

Kết thúc đợt kiểm tra cửa sổ mới; không triển khai phép kiểm tra này làm
bộ lọc mặc định sản phẩm. Hiện nhận diện sơ đồ chỉ phù hợp để nghiên cứu/
minh họa có gắn nhãn thử nghiệm. Chức năng hồ sơ cầu thủ và tham chiếu
StatsBomb không bị thay đổi. Chất lượng chiến thuật bước 5 chưa nghiệm thu;
cần nhãn độc lập cùng tracking để đánh giá trước khi thay phương pháp.

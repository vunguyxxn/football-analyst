# Bước 5: thử nghiệm các tuyến nghiêng và lệch cánh

Ngày 23/10/2026. Thêm phương pháp **aligned** để giảm hạn chế của mẫu có
các tuyến thẳng, cố định tâm ngang. Giữ `gap` mặc định; aligned chỉ chạy
khi chọn rõ tùy chọn. Không đổi API/schema, không thêm thư viện.

## Cách làm

Vẫn dùng trung vị vị trí từ cùng tập khung đủ 11 người và >=80% bao phủ.
Bỏ thủ môn, trừ tâm đội và chuẩn hóa riêng từng trục. Giữ sáu sơ đồ trong
danh mục cũ. Với mỗi sơ đồ:

1. Thử năm độ nghiêng chung trong hệ chuẩn hóa: -0,4/-0,2/0/0,2/0,4.
2. Sắp cầu thủ theo tọa độ dọc đã hiệu chỉnh độ nghiêng, chia tuyến theo
   số người của sơ đồ. Đây là tìm kiếm có ràng buộc thứ tự, không phải phép
   ghép tối ưu tổng quát của template cũ.
3. Cho tâm mỗi tuyến dịch ngang riêng; khớp một thang chiều rộng chung.
   Không yêu cầu khoảng cách giữa các tuyến bằng nhau.
4. Chấm độ trải dọc còn lại trong tuyến và độ lệch ngang khỏi các vị trí
   đều nhau; thêm phạt dịch tâm ngang và phạt sơ đồ có tuyến thứ tư để
   tránh chỉ chọn mẫu linh hoạt hơn.

Cấu hình được lưu trong `formation_aligned.POLICY`: phạt dịch ngang 0,1,
phạt tuyến thứ tư 0,03 trong tổng sai số bình phương; khoảng cách tâm tuyến
tối thiểu 0,2 trong hệ chuẩn hóa; điểm sau căn không quá 0,4 và chênh giữa
hai mẫu ít nhất 0,05. Độ sâu/chiều rộng vẫn phải >=15/20 m. Không đủ tách
biệt thì trả unknown. Không cập nhật các tham số sau khi xem kết quả chạy.

Đây là các lựa chọn heuristic, chưa hiệu chuẩn bằng nhãn độc lập. Điểm
có thành phần phạt nên không gọi là RMSE vị trí vật lý hoặc xác suất đúng.
Độ nghiêng trong hệ chuẩn hóa không phải góc thật trên sân/camera. Tọa độ
và tâm tuyến xuất ra vẫn ở hệ sân gốc, không sửa dữ liệu tracking.

## Kiểm tra hình học

Giữ bộ 72 ca cũ (54 có sơ đồ, 18 kỳ vọng chưa xác định). Cả template và
aligned đúng 54/54 ca có sơ đồ, gap đúng 52/54; không phương pháp nào
xuất nhãn trên 18 ca kỳ vọng chưa xác định.

Bổ sung stress test từ cùng bố trí tự dựng: thay x mỗi cầu thủ ngoài sân
bằng `x + 0.35 * (y - 34)`, rồi dịch y từng tuyến từ -5 đến +5 m. Giữ thủ
môn và các ca unknown, thêm các biến thể nhiễu/hướng/co giãn cũ. Cấu hình
lưu tại `fixtures/formation_alignment_stress.json`, không phải nhãn thật
của trận đấu hoặc tập kiểm định độc lập.

| Stress test | Gap | Template | Aligned |
|---|---:|---:|---:|
| Nhận đúng trong 54 ca có sơ đồ | 0 | 28 | 54 |
| Từ chối trong 54 ca có sơ đồ | 54 | 26 | 0 |
| Xuất nhãn trên 18 ca kỳ vọng chưa xác định | 0 | 0 | 0 |

Các ca này được thiết kế để kiểm tra chính giả thiết tuyến nghiêng/dịch
ngang, nên thuận lợi cho mô hình mới. Không suy rộng thành accuracy trận thật.

## Đối chiếu dữ liệu đã xem

Trên 24 cửa sổ giây 60–120: gap xuất 3 nhãn, template 2, aligned 6. Số
nhãn tăng không tự nói lên chất lượng. Trên năm nhãn nháp agent:

| Phương pháp | Đồng ý nháp | Không đồng ý | Chưa xác định |
|---|---:|---:|---:|
| Gap | 0 | 1 | 4 |
| Template | 0 | 2 | 3 |
| Aligned | 1 | 2 | 2 |

Aligned đồng ý nháp 4-3-3 ở Game 2 B 100–110s; A 60–70s ra 4-3-3 khác
nháp 4-4-2; A 70–80s vẫn ra 4-1-4-1 khác nháp 4-4-2. Hai cửa sổ còn
lại chưa xác định. 19 cửa sổ không chấm giữ nguyên, không biến thành
nhãn đúng/sai. Năm nhãn nháp đã được dùng định hướng thiết kế nên chỉ
là bằng chứng phát triển, không phải tập kiểm định. Cờ nguồn nhãn giữ nguyên.

Trên 24 cửa sổ giây 120–180 và quy tắc đủ 5 ảnh, >=4/5 cùng nhãn trung vị:

| Phương pháp | Nhãn trung vị | Có hỗ trợ thời gian |
|---|---:|---:|
| Gap | 2 | 0 |
| Template | 3 | 0 |
| Aligned | 3 | 1 |

Một cửa sổ aligned đạt là **Game 2 B 140–150s, nhãn 4-3-3**, với 4/5 ảnh
đồng ý. Một nhãn trung vị khác thiếu một ảnh trong dung sai thời gian nên
không được nhận; nhãn còn lại không đủ đồng thuận. Không giảm yêu cầu 4/5.
Các cửa sổ 120–180 đã được xem chẩn đoán ở phiên trước; không gọi đây là
tập mới độc lập cho aligned. Độ ổn định không chứng minh đúng chiến thuật.

## Dùng và tái lập

Từ gốc repo, dùng tên đầu ra mới:

```powershell
.\.venv\Scripts\python.exe -m backend.tactics.metrica_report --game 2 --home-goalkeeper 11 --away-goalkeeper 1025 --home-direction -1 --formation-method aligned --output data/processed/formation_v1/game2_tactics_aligned_v1.json
.\.venv\Scripts\python.exe -m backend.tactics.evaluate_formation --include-aligned --output data/processed/formation_v1/aligned_comparison_with_stress_v1.json
.\.venv\Scripts\python.exe -m backend.tactics.review_formation --include-aligned --output-dir data/processed/formation_v1/aligned_draft_review_v1
.\.venv\Scripts\python.exe -m backend.tactics.formation_stability --include-aligned --output data/processed/formation_v1/aligned_stability_120_180_v1.json
```

Đã chạy hai CSV đội mỗi trận và xuất 44 hồ sơ. Đối chiếu toàn bộ trường
`players` của cả bốn đội với báo cáo cũ: giữ nguyên, phần tính chuyển động
không bị thay đổi. Artifacts mới đều nằm trong `data/processed/formation_v1/`.

13 test mới: sáu sơ đồ/đổi hướng/thứ tự ID, các ca nghiêng trước đây bị từ
chối, tọa độ lỗi/thiếu người/co cụm, guard cửa sổ và đồng thuận thời gian,
giữ mặc định cũ, nguồn nhãn nháp, CLI so sánh. Toàn bộ dự án:
**237 passed, 1 network deselected**, cảnh báo Starlette đã có.

Đã có tiến bộ chức năng trong phạm vi kiểm tra hình học và một cửa sổ
thời gian. Giữ aligned thử nghiệm vì vẫn không đồng ý với nháp ở hai ca
và thiếu nhãn chiến thuật độc lập. Chưa nghiệm thu chất lượng bước 5;
không tiếp tục chỉnh ngưỡng trên cùng các ca rồi báo đó là kiểm định.

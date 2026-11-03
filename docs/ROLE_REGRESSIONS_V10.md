# Rà hồi quy thủ môn và trọng tài v6 → v10 trên val

## Phạm vi và kết luận

Giữ nguyên 128 ảnh val, nhãn, weights, confidence0.25, NMS IoU0.7,
matching IoU0.5, max_det300 và hai size640/1280. Không mở test hoặc match
128057 trong audit này; không sửa nhãn, hạ ngưỡng hay train thêm.
Toàn bộ TP/FP/FN, ma trận nhầm lẫn và prediction dư của cả ba lớp đã tái
hiện chính xác snapshot so sánh v10, không chỉ đối chiếu keeper/ref.

Có **107 lượt v6 nhận đúng nhưng v10 mất**, tương ứng **96 nhãn khác nhau
trong 75 ảnh**. Một nhãn có thể bị mất ở cả hai size. Đây không phải tổng
lỗi của model hay 107 người khác nhau. Đã xem cả 107 crop đánh số trên
6 contact sheet; kiểm riêng mọi keeper không có đường viền che áo và
9 ảnh toàn cảnh đại diện/case cần xem ngữ cảnh. Chưa có người kiểm độc lập.

Nguyên nhân quan sát trực tiếp chủ yếu là **điểm lớp đúng thấp**, tiếp theo
là cạnh tranh vai trò và khung trùng. Không có bằng chứng rằng hiệu chỉnh
sân hay camera lia là bước gây mất trong phép chấm detector tĩnh này.
Chưa thể quy nguyên nhân huấn luyện cho riêng màu áo hoặc 9 ROI bổ sung:
dữ liệu, số bước cập nhật và ngữ cảnh cùng thay đổi; chưa có ablation.

## Mất và nhận lại theo từng nhãn

| Size | Vai trò | V6 đúng | Giữ được | Mất | V10 nhận lại từ lỗi v6 | V10 đúng | Chênh lệch |
|---|---|---:|---:|---:|---:|---:|---:|
| 640 | Thủ môn | 50 | 32 | 18 | 2 | 34 | −16 |
| 640 | Trọng tài | 63 | 22 | 41 | 3 | 25 | −38 |
| 1280 | Thủ môn | 22 | 19 | 3 | 15 | 34 | +12 |
| 1280 | Trọng tài | 91 | 46 | 45 | 55 | 101 | +10 |

V10 ở1280 vẫn mất45 referee cũ dù tổng TP tăng10: có55 trường hợp được
nhận lại. Chỉ xem chênh lệch tổng sẽ che khuất tập hồi quy này.

## Chẩn đoán trước/sau chọn lớp và NMS

Lấy đầu ra trực tiếp từ head YOLO11s đang chạy, gồm tọa độ và điểm sigmoid
ba lớp trước argmax/NMS. Điểm này không phải xác suất đúng đã hiệu chuẩn.
Dùng cùng preprocess/letterbox và đổi tọa độ về ảnh nguồn; kiểm replay
raw→postprocess ở hai weights × hai size trên ảnh đại diện: kết quả bằng
predict chuẩn (sai số cho phép1e-5). Phép ghép chính không thay đổi.

| Size / vai trò | Điểm lớp đúng dưới0.25 | Lớp đúng≥0.25 nhưng thua argmax | Có khung đúng lớp, thua ghép IoU | Không có raw box IoU≥0.5 |
|---|---:|---:|---:|---:|
| 640 / thủ môn | 12 | 5 | 1 | 0 |
| 640 / trọng tài | 39 | 1 | 0 | 1 |
| 1280 / thủ môn | 3 | 0 | 0 | 0 |
| 1280 / trọng tài | 40 | 0 | 5 | 0 |
| Tổng | 94 | 6 | 6 | 1 |

- **94/107 lượt:** không có raw box IoU≥0.5 với điểm lớp đúng đạt0.25.
  Đây là bằng chứng trực tiếp về score thấp quanh đúng nhãn, không chỉ
  suy từ việc thiếu prediction sau NMS. Không thử hạ ngưỡng để sửa điểm.
- **6 lượt argmax:** có điểm lớp đúng≥0.25 nhưng tại các box đủ IoU, lớp
  khác thắng. Cả6 đều bị ghép thành player. Ví dụ review63: điểm keeper
  tốt nhất vẫn0.4396 (v6 0.4363), nhưng player thắng; không thể gọi toàn
  bộ hồi quy là tụt score hoặc hạ confidence sẽ cứu được tất cả.
- **6 lượt khung cạnh tranh:** cùng một người có box player và box đúng
  vai trò còn tồn tại sau NMS. Player có IoU cao hơn nên được phép ghép
  cũ chọn; box đúng vai trò không ghép với nhãn nào. Có4/6 case box đúng
  vai trò còn có confidence cao hơn player. Review62: ref0.7301/IoU0.8229,
  player0.5484/IoU0.8358. Không thay phép chấm hoặc áp dedup để làm đẹp số.
- **1 lượt hình học:** review24 có raw box gần nhất IoU0.4941, sát dưới0.5;
  điểm ref của box đó0.1811 cũng dưới0.25. Đây là trường hợp vừa sát
  ngưỡng hình học vừa score thấp, không đủ căn cứ nói detector không thấy người.

Không case nào thuộc nhóm có raw box đúng lớp thắng argmax≥0.25 nhưng
bị mất hoàn toàn trước bước matching. Trong tập hồi quy đã rà, chưa thấy
NMS/max_det là lời giải thích chính. Phân loại trên có thứ tự ưu tiên;
score thấp và nhầm player có thể đồng thời xảy ra.

Median điểm raw lớp đúng tốt nhất trên box IoU≥0.5:

| Nhóm hồi quy | V6 | V10 |
|---|---:|---:|
| Keeper640 (18 nhãn) | 0.5732 | 0.2022 |
| Ref640 (v6:41, v10:40 nhãn có box đủ IoU) | 0.4141 | 0.0584 |
| Keeper1280 (3 nhãn) | 0.3980 | 0.1801 |
| Ref1280 (45 nhãn) | 0.4523 | 0.1175 |

## Kích thước và ảnh bối cảnh

- Keeper640: cả18 lượt mất đều cao<24px sau resize.16 bị ghép thành
  player,2 không có prediction được ghép. Ở1280 mất3 keeper, đều24–48px;
  1 thành player,2 không ghép được. Kích thước tính theo long-side resize,
  không phải chiều cao ảnh gốc.
- Ref640:25/41 lượt mất<24px,16/41 từ24–48px. Ref1280:2/45<24px,
  38/45 từ24–48px,5/45≥48px. Không chỉ người quá nhỏ mới có lỗi.
- Cả21 quan sát keeper bị mất ở hai size:8 áo vàng/xanh lá,7 xanh lam/
  xanh ngọc,5 sáng/xám/trắng,1 đỏ sẫm. Đây là nhóm màu nhìn gần đúng từ
  ảnh, có quan sát lặp; không phải nhãn màu mới hay thống kê tất cả train.
- 86 quan sát ref bị mất đều nhìn như áo tối; nhiều assistant ở mép xa,
  sau lưng là khán đài hoặc bảng quảng cáo. Vẫn có trọng tài giữa sân và
  assistant khá lớn bị mất. Chỉ bổ sung một màu áo sẽ chưa giải quyết
  được toàn bộ mẫu lỗi.

## Tệp bằng chứng và tái tạo

- `docs/fixtures/role_regressions_audit_v10.json`: toàn bộ107 lượt mất,
  GT/source hash, prediction v6/v10, raw score từng lớp, candidate khung
  đúng và nhãn được ghép; transition summary cả768 quan sát keeper/ref,
  thống kê cả ba lớp, bằng chứng replay và probe hình học.
- Cục bộ: `data/processed/role_regressions_audit_v10/result.json` chứa
  đủ768 dòng; `sheet-0.jpg`…`sheet-5.jpg`, `keeper-appearance.jpg`,
  `context-specials.jpg` để xem ảnh. Hash contact sheet ghi trong snapshot.
- `backend/cv/audit_role_regressions.py`: chạy lại audit từ weights và
  manifest khóa. Output phải chưa tồn tại.

```powershell
.\.venv\Scripts\python.exe -m backend.cv.audit_role_regressions
.\.venv\Scripts\python.exe -m pytest -q tests/test_role_regressions.py --basetemp .tmp/pytest-role-regressions-targeted
```

Đã kiểm lại hash weights và dataset cuối audit. 6 test đích và toàn bộ
570 test Python đạt (1 network deselected, 4 warning cũ). Snapshot giữ nguyên
GT do nguồn/agent cung cấp; việc xem ảnh ở đây không phải tái gán nhãn.

## Bước tiếp theo

Ưu tiên audit độ phủ **train hiện có** cho keeper nhỏ áo xanh/sáng, ref
áo tối ở biên xa và bối cảnh bảng quảng cáo: số đơn vị ảnh–nhãn độc lập,
match/source family và kích thước, tách số ảnh thật khỏi số lần lặp.
Dùng kết quả này để chốt nhóm thiếu trước khi tìm nguồn mới. Sáu case
khung cạnh tranh có thể nghiên cứu riêng sau đó, giữ phép chấm hiện tại.
Chưa tăng epoch, hạ ngưỡng hay đưa val/test/match128057 vào train.

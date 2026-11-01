# Kiểm chất lượng tọa độ, heatmap và vận động

Ngày 01/11/2026. Mục tiêu phiên này là mở rộng thời gian có dữ liệu hợp lệ
và rà kết quả của luồng upload, giữ nguyên hợp đồng TrackingRow và sân
105 × 68 m. Không triển khai lại chuyền/sút hay thêm thư viện.

## Thay đổi

Bộ kiểm vạch trước đây chỉ lấy pixel có saturation <100, value >150.
Ảnh nguồn cho thấy vạch trắng mảnh ở xa bị trộn với màu cỏ khi thu hình:
một số pixel sáng của vạch có saturation khoảng110–120 nên bị bỏ sót.

Nhánh kiểm trong ứng dụng giữ mask cũ và bổ sung bằng chứng tương phản
cục bộ: saturation <140, value >150, top-hat value ≥15 và black-hat
saturation ≥20 với kernel ellipse9×9. Vùng đó vẫn phải gần cỏ. Cần đồng
thời sáng hơn và ít bão hòa hơn lân cận; sọc cỏ sáng rộng hoặc chỉ khác
một thuộc tính không đủ. Đây là heuristic phát triển, chưa chuẩn hóa
mọi độ phân giải/điều kiện quay. Mask của hai fitter nghiên cứu giữ nguyên.

Khi fit bốn đường không có nghiệm đạt kiểm ứng dụng, thử thêm fitter
vòng tròn đã có. Fitter này vẫn phải vượt kiểm vạch vùng cấm riêng và
toàn bộ kiểm vạch của ứng dụng; không chấp nhận chỉ vì khớp vòng tròn.
Nếu bốn đường có nhiều nghiệm, từ chối thay vì dùng fallback để chọn đại.

Không đổi ngưỡng median4px, ≥65% mẫu trong5px, điều kiện đủ ba dấu/vạch
và hai họ x/y. Giữ kiểm mở/đóng, buffer một giây, optical flow, giới hạn
300frame và lọc vận động40km/h. Không điền vị trí qua khoảng thiếu dữ liệu.

Mỗi phiên bản mới ghi thêm `geometry.jsonl` nội bộ: ma trận theo thời
gian, segment và kết quả kiểm vạch khi đến lịch. Ghi nối tiếp để không
giữ cả lịch ma trận trong RAM; hash được lưu trong report. File này
không thêm endpoint và không đổi schema TrackingRow.

## Kết quả trên clip mẫu

Nguồn: `Video Project 15.mp4`, SHA256
`f51735a042b493eba3cced891209fe1b6beb20ca80e20c340c7ede51900495d0`.

| Chỉ số | Trước | Sau qua API |
|---|---:|---:|
| Thời gian clip |52,367s|52,367s|
| Thời gian hiệu chỉnh hợp lệ |15,10s|24,467s|
| Số vị trí xuất |8.336|13.584|
| Cửa sổ nhóm đủ dữ liệu chiến thuật |2|4|
| Mục gợi ý có căn cứ |2|4|

Đoạn mới43–52,367s được bổ sung tự động, không thêm mốc tay. Ba đoạn
cũ0–10,033s,22–24,033s,26–29,033s vẫn được giữ. Job kiểm hiện tại:
`2c8e7ffdb8fc432b9abab9e53bd53c8e`; phiên bản
`e0b9fa2caf0f41c2a5c2a50a7d72296c`. Trạng thái vẫn là `partial`:
24,467s là khoảng46,7% clip, không phải cả clip đã phân tích đầy đủ.

Chạy riêng nhánh hoàn toàn tự động, không nạp mốc tay của job, cũng
có24,467s và4cửa sổ chiến thuật; số vị trí13.578 khác nhẹ do mốc0 khác.
Không thay demo cũ hoặc chỉnh nhãn/ma trận theo kết quả kiểm mét.

## Đối chiếu và ý nghĩa số liệu

- Bộ mốc kiểm v4 giữ nguyên hash, gồm17checkpoint đang dùng và1checkpoint
  từng bị loại. Công cụ vẫn kiểm mốc lịch sử nếu kết quả mới phủ thời điểm đó.
  Có6/18khung có vị trí để đo; cả6max≤1m,12khung không đánh giá được.
  Không tính12khung này là đạt. Mốc đã được chọn trong quá trình phát triển
  bởi cùng agent; đây không phải nhãn độc lập hoặc kiểm mù.
- Audit heatmap theo từng ô21×14, từng track/segment và cộng lại từng nhóm:
  khớp các TrackingRow đã xuất. Tổng nhiệt là452,8giây-người, không phải
  thời lượng clip hay thời gian kiểm soát bóng. Có714frame chứa vị trí,
  tương đương23,8s; thấp hơn thời gian hiệu chỉnh do warm-up/lọc tracking.
- Audit kiểm timestamp, thứ tự ID, tọa độ trong sân, số lượng, segment,
  duration, quãng đường/tốc độ và trung bình. Không có lỗi nhất quán;
  tốc độ lớn nhất báo29,446km/h. Đây là kiểm giới hạn/nhất quán, chưa có
  quãng đường chạy được đo độc lập để kết luận độ chính xác vận động.
- Rà ảnh nguồn5s,45s,50s với vị trí chiếu ngược và sân2D: các điểm đã
  xuất bám vùng chân người và bố trí quan sát; không coi phép chiếu ngược
  là accuracy test vì dùng cùng ma trận. ID và nhóm áo chưa phải danh tính.
- Trên20ứng viên phát triển vượt kiểm mới, tạo80phép chiếu lệch±5m theo
  x/y: tất cả bị từ chối. Đây là kiểm âm nhân tạo trên cùng dữ liệu, không
  phải tỉ lệ false-positive ngoài thực tế. Không dùng kết quả để hạ ngưỡng.

## Lệnh kiểm lặp lại

Từ gốc repo, với các dữ liệu cục bộ còn tồn tại:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.audit_pitch_result `
  --result-dir data/processed/video_jobs/2c8e7ffdb8fc432b9abab9e53bd53c8e/pitch_runs/e0b9fa2caf0f41c2a5c2a50a7d72296c `
  --source "data/raw/Video Project 15.mp4" --fps 30 `
  --reference docs/fixtures/clip_f51735_landmark_checks_v4.json `
  --output data/processed/coverage_verification_v1/audit-rerun.json

.\.venv\Scripts\python.exe -m pytest -q -m "not network" `
  --basetemp=.tmp/pytest_quality_rerun
```

Audit không fit hoặc xuất lại vị trí; kiểm hash video/reference/artifact,
từ chối ghi đè báo cáo cũ, trả exit1 khi có lỗi nhất quán/mốc không đạt.
Chưa có mốc đo được sẽ ghi thiếu bằng chứng, không tự coi là đạt.

425test Python đạt,1network deselected;5test mới về vạch trộn màu, gate
fallback, ma trận lệch, audit nhiệt/vận động/mốc lịch sử và khóa hash.
Frontend không đổi; kiểm API/proxy được thực hiện, chưa có visual UI QA mới.
Bản khóa kết quả: `fixtures/upload_pitch_quality_v2.json`; chi tiết, ảnh
rà nội bộ và các thử nghiệm không công bố tại
`data/processed/coverage_verification_v1`.

Tiếp theo cần bộ clip và nhãn kiểm độc lập, đặc biệt các đoạn10–22s và
29–43s thiếu mốc. Không suy ra đủ11người hoặc kết luận sơ đồ toàn đội từ
khung quay chỉ một phần sân. Gợi ý hiện tại chỉ áp dụng cho nhóm nhìn thấy
trong cửa sổ đủ hỗ trợ, chưa chứng minh hiệu quả chiến thuật ngoài thực tế.

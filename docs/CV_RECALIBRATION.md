# Hiệu chỉnh lại các đoạn bị chặn — 22/10/2026

## Kết luận hiện tại

Giữ sân 105 × 68 m và guard **1 m / 90 frame**, không nới ngưỡng để có
output. Đã sửa được một lỗi mốc biên xa tại frame 1050, đưa đoạn cuối về
sai số trung bình 0,16 m, lớn nhất 0,52 m trên 8 mốc ở hai frame đánh giá
mới. Đoạn này được guard cấp phép liên tục từ frame 1080 đến 1350.

Hai đoạn đầu chưa đạt: hiệu chỉnh lại không cải thiện đồng đều, guard vẫn
chặn, và có mẫu sai trên 1 m ngay trong khoảng giữa hai checkpoint đã được
cấp phép. Không dùng các cửa sổ đó để tuyên bố chỉ số cầu thủ chính xác.
Đoạn cuối có thể dùng để thử tích hợp tracking/tọa độ trên phạm vi ngắn,
chưa nghiệm thu tốc độ/quãng đường, chưa xác nhận định danh cầu thủ.

Không đổi mã nguồn ứng dụng, schema/API, dependency, CameraMotion hay
LandmarkGuard trong phiên này. Các phương án bù camera tham chiếu trực tiếp
được thử trong helper khảo sát nhưng không đưa vào pipeline vì giảm mạnh
coverage hoặc không cải thiện nhất quán. Giữ kết quả thất bại để đối chiếu.

## Nguồn, mốc và dữ liệu phát triển

Nguồn bản cắt SHA256
`86f6f04ce05ac464269dfa4d831bef0c12c3654acdd2fa3c1b6379f864597b2e`,
1280 × 720/60 FPS; giây gốc = 10 + frame/60.

Phóng lớn các mốc biên, chọn các dải vạch rồi fit đường Welsch từ pixel ảnh
S < 140, V > 185 (HSV OpenCV), loại bbox person cache nới 12 px. Giao với
đường giữa sân được xác định từ vạch ảnh, không suy ngược từ homography.
Nhãn do agent quan sát và hỗ trợ bằng fit đường, chưa được rà soát độc lập.

- Đoạn cuối giữ mốc đầu 1050: giao biên xa sửa từ (821,207) thành khoảng
  (823,027;211,356), tức lệch khoảng 4 pixel theo chiều y ở nhãn cũ. Biên gần
  cũng được rà lại. Trên nhãn phát triển cũ, lỗi max giảm 1,79 → 0,58 m.
- Rà mốc cũ frame 0/450 chưa cải thiện đồng đều. Đặt mốc tay mới tại frame
  bị guard từ chối là 75/525, bổ sung góc sân, vùng cấm và hai mốc vòng tròn.
  Các frame/mốc cũ đã dùng chỉnh là dữ liệu phát triển, không còn held-out.
- Cấu hình và lịch checkpoint được khóa trước khi gán nhãn bộ đánh giá mới.
  Nhãn runtime ở frame 90/150/550/625/1080/1200 được lấy từ ảnh và fit vạch;
  một số checkpoint cũ được tái dùng và ghi rõ provenance. Chúng không tham
  gia tập đánh giá mới.

Fixture khảo sát:

```text
docs/fixtures/vid1_11f23eea_recalibrated.json
docs/fixtures/vid1_11f23eea_recalibrated_checks.json
```

Các segment đầu 75, 525, 1050 có lần lượt 228, 226, 301 frame. Hai segment
đầu là ứng viên chưa được chấp nhận; metadata `candidate_status` chỉ để ghi
kết luận khảo sát, không phải cờ mà CLI tự dùng để bỏ segment.

## Đánh giá hình học trên frame mới

Frame 120/255, 555/690, 1110/1260 không dùng fit hoặc làm runtime checkpoint.
Mỗi frame có 4 mốc: hai giao đường giữa sân với vòng tròn và với hai biên.
Biên được gán từ giao các vạch ảnh đã fit, vòng tròn chọn y bằng mắt và x
trên vạch giữa sân quan sát được. Không tạo nhãn bằng phép chiếu ngược của
ma trận đang đánh giá. Số lẻ fit không đồng nghĩa nhãn chính xác dưới pixel.

So sánh hai phép chiếu trên **cùng các mốc mới**. Cột mới là sai số mô hình
camera tính offline khi chưa áp guard, kể cả ở frame mà guard sẽ chặn;
không có nghĩa hệ thống đã xuất tọa độ tại các frame đó.

| Đoạn | Số mốc theo thời gian | Trung bình cũ → mới | Max cũ → mới |
|---|---:|---:|---:|
| Đầu, hiệu chỉnh lại ở 75 | 8 | 0,30 → 0,71 m | 0,43 → 1,59 m |
| Lia trái, hiệu chỉnh lại ở 525 | 8 | 1,12 → 0,61 m | 2,47 → 1,84 m |
| Lia trở lại, sửa mốc 1050 | 8 | 0,54 → 0,16 m | 1,76 → 0,52 m |

Bốn giao cung vùng cấm ở frame 555/690 không dùng fit đoạn giữa, là kiểm tra
hình học bổ sung: trung bình **0,51 → 0,82 m**, max **0,79 → 1,23 m**.
Do đó không chấp nhận ứng viên đoạn giữa chỉ vì trung bình mốc giữa sân
tốt hơn. Đoạn đầu bị hồi quy trên bộ mới, cũng không chấp nhận. Giữ toàn bộ
kết quả, không chỉ báo phần cải thiện ở đoạn cuối.

Mốc ở frame khác vẫn cùng loại landmark/cùng video, không phải đánh giá
trận độc lập hay ground truth đo đạc thực địa. Đoạn cuối chưa có mốc hình
học độc lập bổ sung ngoài các loại đã hiệu chỉnh; kết quả là sơ bộ.

## Replay guard và coverage

Đọc lại 755 frame của ba phạm vi mới, tính optical flow bằng bbox person
YOLO thật đã cache từ lượt khảo sát trước. Không chạy YOLO mới, ByteTrack,
phân đội hoặc chỉ số cầu thủ. Không xuất file tracking với ID giả; chỉ đếm
detection có thể chiếu được và kiểm tra trạng thái. Ba video giải mã đủ.

| Đoạn | Frame chờ | Frame cấp phép | Frame lost | Cửa sổ cấp phép |
|---|---:|---:|---:|---|
| Đầu | 15 | 60 | 153 | 90–149 |
| Lia trái | 25 | 75 | 126 | 550–624 |
| Lia trở lại | 30 | 271 | 0 | 1080–1350 |

Đoạn đầu lost tại frame 150 do lỗi mốc 1,58 m, đoạn giữa tại 625 do 2,43 m;
không tự khôi phục bằng mốc kiểm tra sau đó. Đoạn cuối không lost. Tổng 70
frame chờ + 406 cấp phép + 279 lost = 755. `Cấp phép` chỉ là trạng thái
guard, không bảo đảm mọi frame trong cửa sổ đều sai số dưới 1 m.

Cụ thể, trong cửa sổ được cấp phép, frame đánh giá 120 có mốc sai 1,31 m,
frame 555 có mốc hình học bổ sung sai 1,23 m. Guard không phát hiện ngay vì
không có checkpoint tại chính các frame này. Hai frame mới của đoạn cuối
1110/1260 có max 0,39/0,52 m. Kết quả này cho thấy giới hạn quan trọng của
kiểm chứng thưa: không dùng coverage để thay cho đo độ chính xác.

## Artifact và bước tích hợp tiếp theo

Artifacts cục bộ ở `data/processed/clip_11f23eea/recalibration_check/`:

```text
new_evaluation.json
guard_summary.json
recalibrated_guard_quality.jsonl
early_pan_guarded.mp4
left_pan_guarded.mp4
return_pan_guarded.mp4
evaluation_{120,255,555,690,1110,1260}.jpg
return_calibration.json
return_checks.json
```

Hai file `return_*.json` được lọc từ fixture đã commit để chỉ có segment
1050–1350 và checkpoint tương ứng, đã kiểm tra bằng loader. Có thể tái tạo:

```python
import json
from pathlib import Path

out = Path("data/processed/clip_11f23eea/recalibration_check")
cal = json.loads(Path("docs/fixtures/vid1_11f23eea_recalibrated.json").read_text())
checks = json.loads(Path("docs/fixtures/vid1_11f23eea_recalibrated_checks.json").read_text())
cal = {k: cal[k] for k in ("source_sha256", "image_size", "segments")}
cal["segments"] = [s for s in cal["segments"] if s["name"] == "return_pan"]
checks = {k: checks[k] for k in ("source_sha256", "image_size", "max_error_m", "max_gap_frames", "checkpoints")}
checks["checkpoints"] = [r for r in checks["checkpoints"] if 1050 < r["frame"] < 1351]
out.mkdir(parents=True, exist_ok=True)
(out / "return_calibration.json").write_text(json.dumps(cal, indent=2), encoding="utf-8")
(out / "return_checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
```

Lệnh tích hợp sản phẩm sẵn có để thử riêng đoạn cuối, cần tên đầu ra mới:

```powershell
$env:YOLO_CONFIG_DIR = "$PWD\data\processed"
$env:MPLCONFIGDIR = "$PWD\.tmp\matplotlib"
.\.venv\Scripts\python.exe -m backend.cv.track_video data/processed/clip_11f23eea/vid1_11f23eea_clean.mp4 data/processed/clip_11f23eea/return_pitch_full.mp4 --weights data/raw/yolo11n.pt --device 0 --image-size 1280 --team-samples docs/fixtures/vid1_11f23eea_team_samples.json --calibration data/processed/clip_11f23eea/recalibration_check/return_calibration.json --pitch-output data/processed/clip_11f23eea/return_pitch_full --compensate-camera --landmark-checks data/processed/clip_11f23eea/recalibration_check/return_checks.json
```

Lệnh tích hợp trên chưa chạy trong phiên này; lượt replay camera đã chạy.
CLI sẽ ghi toàn video nhưng chỉ cấp phép chiếu đoạn cuối sau checkpoint,
không biến hai đoạn đầu chưa đạt thành dữ liệu hợp lệ. Bước tiếp theo là
thử tracking + phân đội + tọa độ/heatmap trong cửa sổ này, kiểm tra ID/điểm
chân và noise trước khi diễn giải tốc độ/quãng đường. Không coi đây là đã
nghiệm thu toàn clip hoặc chuyển bước 5.

Helper khảo sát nằm ở `.tmp/` (`refit_boundaries.py`, `build_reanchors.py`,
`build_recalibrated_guard.py`, `replay_recalibrated.py`,
`evaluate_recalibration.py`); không phải công cụ đóng gói cho fresh clone.
Không commit video hoặc cache. Hồi quy toàn bộ 99 test qua, 1 network test
deselected, còn cảnh báo Starlette cũ.

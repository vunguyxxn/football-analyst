# Ổn định nhãn vai trò theo track

Ngày: 22/10/2026. Bổ sung tổng hợp nhãn màu áo theo từng ID sau ByteTrack,
giữ NMS, bộ lọc người trong sân, hiệu chỉnh và guard. Không đổi classifier
màu áo, dependency, schema hoặc API. Không nhận diện danh tính cầu thủ thật.

## Quy tắc

`backend/cv/team_smoother.py` dùng lịch sử quá khứ, không nhìn frame tương lai:

- Cửa sổ 0,5 giây, tối thiểu 3 frame; ở 60 FPS là 30 frame.
- Cần ít nhất `max(3, ceil(FPS × 0,1))` phiếu cùng nhãn và >=70% lịch sử
  hiện có. Ở 60 FPS cần 6 phiếu. Đầu track chưa đủ phiếu trả `unknown`.
- `unknown` không bỏ phiếu cho đội nhưng vẫn nằm trong mẫu số, làm giảm độ
  chắc chắn. Khi nhãn hiện tại mâu thuẫn với nhãn thắng cũng trả `unknown`.
- Không khóa cứng nhãn đầu tiên. Bằng chứng mới kéo dài có thể đổi nhãn sau
  giai đoạn chưa chắc chắn. Không trộn lịch sử giữa hai ID.
- Lịch sử cũ rơi khỏi cửa sổ; track vắng đủ một cửa sổ bị xóa kể cả frame
  không có detection hoặc không có hình học hợp lệ. Khi trở lại phải tích
  lũy bằng chứng mới. Lịch sử được giữ xuyên các chunk xử lý.

Mỗi frame vẫn lấy màu áo riêng như trước; bộ mới bỏ phiếu trên các nhãn màu
áo, không fit lại K-means hoặc lấy màu từ ảnh đã vẽ khung. Nhãn đã ổn định
được dùng chung cho video, `TrackingRow.team` và tổng nhãn CLI/heatmap đội.
Không sửa các dòng quá khứ sau khi có thêm bằng chứng.

Thử chỉ lấy nhãn thắng lịch sử cho thấy có thể gán B cho cầu thủ A khi ID
được tracker dùng sang người khác. Vì vậy bản cuối yêu cầu nhãn hiện tại
đồng thuận, còn mâu thuẫn thì `unknown`. Đây là từ chối dự đoán chưa chắc,
không phải sửa hoàn toàn ID switch hoặc phục hồi màu áo bị che khuất.

## Kiểm tra trên dữ liệu thật

Dùng đầu ra trước sửa `id_deduplicated/tracking.jsonl` của cùng bản cắt
`86f6f04c...`, 5.215 quan sát / 30 ID, frame 1081–1350. Replay theo thứ tự
thời gian bằng chính TrackRoleSmoother, không đổi ID, tọa độ hoặc số dòng.

| Diagnostic toàn cửa sổ | Trước | Sau |
|---|---:|---:|
| Chuyển trực tiếp giữa hai nhãn đã biết khác nhau | 43 | 0 |
| Mọi lần đổi nhãn, gồm unknown | 103 | 92 |
| Quan sát unknown | 99 (1,90%) | 624 (11,97%) |
| Quan sát A / B / trọng tài | 2450 / 2354 / 312 | 2220 / 2232 / 139 |

Chuyển nhãn đã biết bằng 0 phần lớn do quy tắc đi qua `unknown`, không tự
chứng minh màu áo đúng. Vẫn có nhấp nháy đã biết/unknown. Các số theo đội là
nhãn dự đoán, không phải số lượng cầu thủ thực hay accuracy.

Fixture `vid1_11f23eea_track_roles.json` tham chiếu 49 bbox/định danh cục bộ
của bộ kiểm tra ID trước đó, bổ sung vai trò theo màu đã xác nhận. Bộ này
được dùng phát triển/hồi quy, không gọi là kiểm tra độc lập. Sau khi khóa
quy tắc cuối, vẽ thêm 21 bbox tại frame 1170/1230/1290 từ ảnh nguồn không
overlay; không dùng các nhãn mới để chỉnh ngưỡng. Cả hai bộ chỉ gán nhãn
7 người, do agent quan sát, chưa được người độc lập rà soát.

Ghép bbox dự đoán của replay NMS với bbox nhãn bằng IoU >=0,3 như lượt kiểm
tra ID; lấy bbox IoU cao nhất cho một người để đối chiếu vai trò.

| Kết quả nhãn | 49 mẫu cũ trước/sau | 21 mẫu mới trước/sau |
|---|---:|---:|
| Mẫu ghép được | 48 / 48 | 21 / 21 |
| Đúng | 46 / 45 | 19 / 18 |
| Sai nhưng vẫn gán nhãn đã biết | 2 / 0 | 2 / 0 |
| Unknown | 0 / 3 | 0 / 3 |

Bộ mới cả ba mẫu trọng tài đều bị từ chối: hai mẫu trước gán sai A, một mẫu
trước nhận đúng trọng tài. Vì vậy không tuyên bố tăng accuracy tổng thể hoặc
đã đạt recall trọng tài. Đổi lại, không còn nhãn đội sai trên các mẫu đã
ghép này; phạm vi bằng chứng vẫn nhỏ, cùng clip và nhãn chưa độc lập. Giữ
khả năng trả unknown thay vì ép nhãn để tăng coverage.

## Kiểm thử và artifacts

`tests/test_team_smoother.py` kiểm tra tích lũy phiếu, nhiễu/unknown, bằng
chứng mới sửa nhãn đầu sai, tách ID, hết hạn, giới hạn bộ nhớ và thời gian.
Test pipeline dùng codec/ByteTrack thật kiểm tra bộ lọc ngoài sân, tổng nhãn
đã ổn định và giữ lịch sử xuyên chunk. Classifier riêng và cách fit từ dữ
liệu calibration giữ nguyên.

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_team_final
```

Kết quả: **115 passed, 1 network test deselected**, cảnh báo Starlette cũ.
Helper `.tmp/replay_team_smoothing.py`, `.tmp/evaluate_team_smoothing.py`,
`.tmp/evaluate_new_role_samples.py` và kết quả cục bộ
`data/processed/clip_11f23eea/team_stability_check/` không được đóng gói cho
fresh clone. Không commit media/cache. Chưa nghiệm thu tốc độ/quãng đường.

## Chạy lại pipeline đầy đủ

Chạy lệnh ở `CV_TRACKING_ID_CHECK.md` với video đầu ra `team_roles_final.mp4`
và thư mục `--pitch-output .../team_roles_final`, các cờ khác giữ nguyên.
Khi có `--team-samples` bộ tổng hợp được bật tự động, không cần cờ mới.

Lượt cuối hoàn thành 1.800 frame / 3 chunk trên CUDA device 0, 6,78 FPS.
Guard giữ 1.499 ngoài hiệu chỉnh / 30 chờ / 271 cấp phép. Có 5.215 dòng,
30 ID, chỉ frame 1081–1350. A/B/referee/unknown = 2220/2232/139/624.
Đối chiếu toàn bộ khóa frame+ID và tọa độ với lượt trước: không đổi; nhãn
khớp chính xác replay nhân quả ở trên. Thống kê chuyển động không đổi.

Giải mã lại nguồn và video đầy đủ đều 1.800 frame, cửa sổ 271 frame, cùng
1280 × 720 / 60 FPS. Schema, khóa, phạm vi, thời gian, tổng samples/heatmap
và tổng nhãn CLI đều qua. Đã xem 1140/1230/1290: trường hợp nhãn mâu thuẫn
chuyển thành unknown, người ngoài sân vẫn không có khung; các cầu thủ dễ
quan sát giữ nhãn. Chưa coi đây là mọi người/mọi frame đều đúng.

Artifacts cuối trong `data/processed/clip_11f23eea/team_roles_final/`: JSONL,
metrics, validation, ảnh `check_*.jpg`, heatmap QA và `accepted_window.mp4`.
Video đầy đủ `team_roles_final.mp4`, stdout `team_roles_final_run.json` ở
cạnh thư mục. Helper `.tmp/validate_team_roles.py`, `.tmp/compare_team_pipeline.py`
kiểm tra cục bộ, không đóng gói cho fresh clone. Lượt thử `team_stabilized`
đã dừng khi thay quy tắc mâu thuẫn, không phải đầu ra nghiệm thu.

Nghiệm thu chức năng tổng hợp/từ chối nhãn và tính nhất quán đầu ra. Chưa
nghiệm thu accuracy/recall trọng tài toàn clip; vẫn cần cải thiện bằng chứng
màu áo ở xa và đánh giá nhiều clip. Không chuyển bước 5 hoặc diễn giải các
chỉ số chuyển động như số liệu thực địa. Bước 4 còn nhiễu điểm chân/tọa độ.

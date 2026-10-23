# Bộ lọc tọa độ v3: tốc độ, khôi phục sau lỗi và nhiễu tương quan

Ngày: 23/10/2026. Tiếp tục kiểm chứng bước 4, chưa nghiệm thu độ chính xác
thực địa. Không đổi schema/API, dependency, YOLO/ByteTrack, nhãn đội hoặc
camera guard. `--smooth-pitch` vẫn tùy chọn, tắt mặc định.

## Thay đổi và giới hạn

- Tăng cửa sổ fit tuyến tính nhân quả từ 0,2 lên 0,4 s, vẫn ước lượng tại
  thời điểm hiện tại. Chờ tối thiểu 3 điểm/span 0,08 s; không cần chờ đủ
  0,4 s mới xuất. Fit vẫn dùng tọa độ thô đã qua gate, không frame tương lai.
- Khi thời gian từ điểm thô được chấp nhận cuối trong (0,25; 0,8] s và còn
  vận tốc fit, kiểm tra residual so `last_xy + velocity*dt` bằng ngưỡng
  `0,5 + 6*dt²/2` mét. Đây là dung sai heuristic cho chuyển động thay đổi,
  không phải gia tốc tối đa thực nghiệm. Không học vận tốc từ điểm bị loại.
- Ngoài khoảng đó, gate khoảng cách v2.1 giữ nguyên:
  `40/3,6 * min(dt,0,25) + 0,5 m`. Hết 0,8 s không tiếp tục ngoại suy chạy
  mãi. Khoảng mất quan sát thật >0,25 s vẫn khởi tạo mới theo cơ chế cũ.
- Lỗi vẫn ngắt anchor metrics và xóa lịch sử fit. Nếu điểm quan sát quay
  về phù hợp dự báo thì warm-up lại; không xuất điểm dự báo trong lúc lỗi,
  không cộng phần đường thiếu. Xóa vận tốc cũ khi bắt đầu chuỗi khôi phục.
- Giữ cơ chế ứng viên khởi tạo v2.1, không tự xác nhận một vị trí xa chỉ
  vì nhiều điểm lặp lại. Fit dùng điểm trừ trung bình để giảm triệt tiêu
  số thực; kiểm tra tọa độ hằng tại biên sân vẫn xuất đúng.

Cửa sổ dài hơn làm phản ứng khi dừng/rẽ chậm hơn và có thể khuếch đại nhiễu
tương quan. Sai ID gần nhau, trôi chậm hoặc chuỗi sai nhất quán vẫn có thể
qua gate; dự báo ngắn không xác minh danh tính. Không ép tốc độ về 40 km/h,
không ép điểm vượt biên vào sân. PitchMetrics vẫn lấy mẫu >=0,5 s riêng.

## Protocol phát triển và holdout

Nguồn [Metrica Sports Sample Data](https://github.com/metrica-sports/sample-data),
commit e706dd506b360d69d9d123d5b8026e7294b13996; cùng bốn CSV khóa SHA256,
105 × 68 m, gốc trái dưới sau chuyển đổi, 25 FPS. Metrica là tọa độ tham
chiếu công bố, không ground truth tuyệt đối. Không đánh giá detector hay
homography trên các CSV này.

- Phát triển trên [60,120), các seed 1729/2718/3141; thêm thử hồi phục ID 4
  Game 2 ở [300,360) vốn đã được dùng xem lỗi từ phiên trước. Không coi
  các cửa sổ này là holdout mới. V2.1 phát triển được lấy từ artifact cũ;
  chạy thêm correlated_noise cho cả v2.1/v3 với cùng protocol.
- Khóa v3, rồi kiểm tra hiệp 1 [420,480), seed 2449/3162/3873. Manifest
  `metrica_holdout_v3.json` được tạo trước chạy, không chỉnh tham số theo
  kết quả này. SHA256 file bộ lọc tại thời điểm chạy:
  `7dc8d24554b7c64497db9849c5534cfde437439a4df65d5555907daf1f69f837`.
- So baseline v2.1 ở commit ca85b08 với v3: mỗi bộ 32 lượt (clean một lượt
  mỗi trận; 5 tình huống lỗi × 3 seed × 2 trận), tổng 64 lượt holdout.
  Có 65.944 điểm tham chiếu phân biệt, 22 trajectory/trận. Audit raw count,
  raw RMSE, số lỗi và reference count khớp giữa hai bộ; tổng metrics/RMSE
  khớp tổng từng trajectory, JSON hữu hạn.
- Giữ clean, noise sigma 0,15 m, spikes 1%, gaps và relocation 0,6 s như
  benchmark trước. Thêm `correlated_noise`: nhiễu AR(1) từng trajectory,
  `rho = exp(-dt/0,2)`, innovation nhân `sqrt(1-rho²)` để giữ độ lệch chuẩn
  biên 0,15 m/trục. Khởi tạo lại nhiễu ở gap tự nhiên, không sửa reference.
  Đây là mô phỏng tương quan thời gian, chưa phải mô hình sai số camera đo
  từ video, chưa mô phỏng dịch camera chung giữa nhiều cầu thủ hay ID swap.

## Kết quả holdout [420,480)

Số là median độc lập qua seed; clean chỉ một lượt. RMSE tại timestamp hiện
tại. Raw-common là cùng frame/ID được v3 giữ, giúp phân biệt bỏ điểm với
thay tọa độ. Tập v2.1/v3 có thể khác; bảng coverage phải đọc kèm.

| Trận / tình huống | Raw-all (m) | RMSE v2.1 (m) | RMSE v3 (m) | Raw-common v3 (m) |
|---|---:|---:|---:|---:|
| 1 / clean | 0.0000 | 0.0051 | 0.0178 | 0.0000 |
| 1 / noise | 0.2119 | 0.1536 | 0.1215 | 0.2119 |
| 1 / spikes | 1.2282 | 0.1543 | 0.1243 | 0.2119 |
| 1 / gaps | 0.2119 | 0.1539 | 0.1222 | 0.2119 |
| 1 / relocation | 1.2974 | 0.1537 | 0.1218 | 0.2119 |
| 1 / correlated_noise | 0.2121 | 0.2169 | 0.2170 | 0.2121 |
| 2 / clean | 0.0000 | 0.0088 | 0.0263 | 0.0000 |
| 2 / noise | 0.2124 | 0.1539 | 0.1222 | 0.2123 |
| 2 / spikes | 1.3265 | 0.1550 | 0.1254 | 0.2124 |
| 2 / gaps | 0.2125 | 0.1542 | 0.1227 | 0.2125 |
| 2 / relocation | 1.2994 | 0.1541 | 0.1225 | 0.2125 |
| 2 / correlated_noise | 0.2110 | 0.2156 | 0.2162 | 0.2110 |

Bảng sau theo thứ tự **v2.1 → v3**. Bias phần được cộng so đường tham chiếu
đúng khoảng anchor thực sự được cộng, không thay đường cong bằng dây cung.
MAE tốc độ có trọng số thời gian. Bias toàn cửa sổ gồm tác động mất điểm và
đuôi chưa đủ cadence; coverage điểm không thay cho thời gian metrics.

| Trận / tình huống | Điểm giữ (%) | Thời gian metrics (%) | MAE tốc độ (km/h) | Bias distance toàn cửa sổ (%) | Bias distance phần được cộng (%) |
|---|---:|---:|---:|---:|---:|
| 1 / clean | 99.87 → 99.87 | 99.73 → 99.73 | 0.04 → 0.06 | -0.79 → -0.51 | -0.41 → -0.13 |
| 1 / noise | 99.83 → 99.83 | 99.61 → 99.61 | 0.83 → 0.66 | 1.78 → 1.12 | 2.47 → 1.80 |
| 1 / spikes | 97.17 → 97.17 | 90.59 → 90.59 | 0.84 → 0.69 | -8.55 → -9.07 | 2.58 → 1.84 |
| 1 / gaps | 96.43 → 96.43 | 94.41 → 94.41 | 0.83 → 0.66 | -2.75 → -3.59 | 2.57 → 1.68 |
| 1 / relocation | 98.69 → 98.69 | 97.88 → 97.88 | 0.81 → 0.65 | 0.71 → -0.09 | 2.55 → 1.73 |
| 1 / correlated_noise | 99.87 → 99.87 | 99.73 → 99.73 | 1.13 → 1.17 | 4.41 → 4.93 | 4.81 → 5.33 |
| 2 / clean | 99.72 → 99.72 | 99.55 → 99.55 | 0.06 → 0.08 | -1.42 → -1.11 | -0.55 → -0.23 |
| 2 / noise | 99.66 → 99.66 | 99.35 → 99.35 | 0.86 → 0.66 | -0.15 → -0.41 | 0.99 → 0.72 |
| 2 / spikes | 96.57 → 96.57 | 89.16 → 89.16 | 0.89 → 0.70 | -10.22 → -10.39 | 0.91 → 0.72 |
| 2 / gaps | 96.25 → 96.25 | 94.22 → 94.22 | 0.84 → 0.66 | -5.13 → -5.36 | 0.91 → 0.66 |
| 2 / relocation | 98.52 → 98.52 | 97.62 → 97.65 | 0.85 → 0.66 | -1.61 → -1.86 | 0.97 → 0.71 |
| 2 / correlated_noise | 99.70 → 99.71 | 99.51 → 99.51 | 1.17 → 1.19 | 1.29 → 1.70 | 2.20 → 2.61 |

- Noise độc lập: MAE tốc độ giảm khoảng 0,83/0,86 → 0,66/0,66 km/h, RMSE
  vị trí 0,154 → 0,121/0,122 m. Lag lưới vẫn chọn 0 ms ở cả hai bộ;
  lưới 40 ms không chứng minh mọi chuyển động không có trễ.
- Clean lại xấu hơn: RMSE ~0,005/0,009 → 0,018/0,026 m; không thể gọi
  v3 tốt hơn cho mọi đầu vào. Bảng ghi cả MAE tốc độ clean tăng.
- Cả sáu lượt relocation vẫn loại toàn bộ 330/330 điểm lỗi mỗi lượt;
  không cộng quãng đường qua burst. Game 2, seed 3873, ID 1024: coverage
  49,87% → 98,53%. Minimum coverage trajectory qua các lượt relocation
  Game 2 tăng 49,87% → 95,53%; median coverage tổng chỉ đổi rất ít.
- Correlated_noise không cải thiện: RMSE v3 ~0,216–0,217 m, cao hơn raw
  ~0,211–0,212 m và hơi cao hơn v2.1. MAE tốc độ tăng ~1,13/1,17 →
  1,17/1,19 km/h. Bias distance cũng tăng. Minimum coverage vẫn có ID
  chỉ đạt 84,33%. Không dùng kết quả noise độc lập để tuyên bố xử lý được
  nhiễu camera/bbox thực tế.
- Spikes vẫn thiếu khoảng 9–10% distance toàn cửa sổ; phục hồi vị trí
  không tự khôi phục phần đường không quan sát. Không lấy bias thấp hơn
  riêng lẻ làm chứng nhận chính xác khi coverage khác.

## Trường hợp phát triển đã biết và replay clip

ID 4 Game 2 tại [300,360), ba seed cũ: coverage v2.1 ~70,84–70,98% tăng lên
98,24–98,52%, không giữ điểm relocation lỗi. Đây là kiểm tra hồi quy trên
trường hợp đã biết, không gộp vào holdout cuối.

Replay cùng 5.215 điểm thô / 30 ID của `team_roles_final` trên clip clean
SHA256 `86f6f04ce05ac464269dfa4d831bef0c12c3654acdd2fa3c1b6379f864597b2e`.
Không chạy lại YOLO/CUDA hoặc ghi đè video/ảnh cũ.

| Mục | v2.1 | v3 |
|---|---:|---:|
| Dòng lọc / ID có tọa độ | 4.730 / 27 | 4.735 / 27 |
| Cặp frame liên tiếp | 4.658 | 4.665 |
| Cặp suy tốc độ >40 km/h | 98 | 30 |
| p95 tốc độ từng frame (diagnostic) | 31,17 | 24,24 km/h |

Trên đúng cùng 4.658 cặp, v2.1 có 98 cặp >40/p95 31,17, v3 có 30/p95
24,20 km/h; raw cùng cặp có 605/p95 69,20. Không coi tốc độ từng frame là
tốc độ thực. Nhãn từng raw row không đổi; v3 xuất A/B/ref/unknown =
2109/2097/139/390, frame 1086–1350. Diagnostic có 358 warming_up,
122 jump_rejected, 206 yêu cầu ngắt mốc. Schema, frame/ID/nhãn/timestamp,
accepted keys, tổng samples và heatmap đều khớp 4.735 điểm.

Test tổng hợp chạy 2 m/s rồi dừng ở giây 1: v3 sai lệch tối đa 0,1116 m;
sau dừng 250 ms còn tối đa 0,0692 m, sau 400 ms bằng 0 trong sai số số thực.
Ngưỡng test sau 250 ms đổi từ 0,02 sang 0,08 m và bổ sung hội tụ sau 400 ms:
ghi rõ đánh đổi do cửa sổ dài hơn, không coi phản ứng dừng cũ còn được giữ.
Chuyển động thẳng đều vẫn khớp tọa độ trong 1e-10 m.

## Kiểm tra và tái tạo

148 test qua, 1 network deselected, cảnh báo Starlette có sẵn. Thêm kiểm
tra runner 8 m/s hồi phục sau burst 0,6 s ở 25/60 FPS mà không cộng đường
thiếu; dự báo hết hạn; tọa độ hằng tại biên sân; tương quan/độ lệch chuẩn
nhiễu AR và reset ở gap. Pipeline codec/ByteTrack vẫn qua.

Tải bốn CSV theo lệnh có hash trong `METRICA_BENCHMARK.md`. Từ gốc repo,
đầu ra phải là file mới (đổi tên nếu đã tồn tại):

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_pitch_v3_final
.\.venv\Scripts\python.exe -m backend.cv.metrica_benchmark --data-dir data/raw/metrica --output data/processed/metrica_benchmark_v3/development.json
.\.venv\Scripts\python.exe -m backend.cv.metrica_benchmark --data-dir data/raw/metrica --manifest docs/fixtures/metrica_correlated_development.json --output data/processed/metrica_benchmark_v3/development_correlated.json
.\.venv\Scripts\python.exe -m backend.cv.metrica_benchmark --data-dir data/raw/metrica --manifest docs/fixtures/metrica_holdout_v3.json --output data/processed/metrica_benchmark_v3/holdout.json
```

Baseline v2.1 dùng mã từ Git ca85b08 trong tiến trình riêng; không thay file
production và dùng cùng mã đánh giá/AR hiện tại. Ví dụ PowerShell:

```powershell
@'
import json, subprocess, sys, types
from pathlib import Path
from backend.cv import metrica_benchmark as bench
source = subprocess.check_output(['git','show','ca85b08:backend/cv/pitch_smoother.py'], text=True, encoding='utf-8')
module = types.ModuleType('baseline_filter')
sys.modules[module.__name__] = module
exec(compile(source, 'ca85b08:pitch_smoother.py', 'exec'), module.__dict__)
bench.PitchSmoother = module.PitchSmoother
output = Path('data/processed/metrica_benchmark_v3/holdout_baseline.json')
report = bench.run('data/raw/metrica', 'docs/fixtures/metrica_holdout_v3.json', output)
report['filter']['implementation_commit'] = 'ca85b08'
output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
'@ | .\.venv\Scripts\python.exe -
```

Artifacts ignored: `data/processed/metrica_benchmark_v3/` gồm development,
development_correlated, development_correlated_baseline, holdout,
holdout_baseline, summary, known_id4_development JSON; replay ở
`data/processed/clip_11f23eea/pitch_smoothing_v3_check/` gồm tọa độ,
quality/metrics/summary/comparison. Helper replay/audit cục bộ ở `.tmp/`;
tests và manifest đã commit, dữ liệu lớn/video vẫn giữ cục bộ.

## Trạng thái nghiệm thu

V3 cải thiện nhiễu độc lập và hồi phục ngắn so v2.1, chưa xử lý tốt nhiễu
tương quan, rẽ/dừng hoặc ID đổi gần nhau. Holdout chỉ tách thời gian trong
cùng hai trận; chưa chứng minh tổng quát camera/trận khác. Giữ smoothing
tùy chọn; chưa nghiệm thu bước 4 thực địa và chưa chuyển bước 5.

Tiếp theo cần đánh giá mốc gán nhãn độc lập trên video và chốt phần chỉ số
nào đủ tin cậy để dùng báo cáo. Nếu video chưa đạt, lộ trình đã có phương
án dùng Metrica cho phân tích chiến thuật; không cần khẳng định sai số video
bằng sai số CSV hoặc tiếp tục chỉnh trên holdout này rồi gọi là độc lập.

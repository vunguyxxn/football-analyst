# Bộ lọc tọa độ v2.1: giảm trễ và xử lý nhảy vị trí kéo dài

Đây là báo cáo v2.1 tại commit `ca85b08`. Mã hiện tại đã dùng v3;
xem `METRICA_FILTER_V3.md`. Các số và kết luận dưới đây giữ nguyên cho v2.1.

Ngày: 23/10/2026. Phạm vi: PitchSmoother và kiểm chứng cùng PitchMetrics;
không đổi YOLO/ByteTrack, phân đội, camera guard, dependency, schema/API.
`--smooth-pitch` vẫn tùy chọn, tắt mặc định. Chưa nghiệm thu bước 4 thực địa.

## Phương pháp

- Thay trung vị ba điểm + EMA bằng hồi quy tuyến tính x/y theo timestamp
  trên lịch sử tối đa 0,2 s, đánh giá tại thời điểm hiện tại. Không dùng
  frame tương lai. Giữ warm-up ít nhất 3 điểm và span 0,08 s.
- Gate khoảng cách so với điểm thô được chấp nhận cuối:
  `40/3,6 * min(dt, 0,25) + 0,5 m`. Khi đã có tọa độ xuất, lỗi vượt gate
  bị loại và ngắt metrics; lặp lại ba điểm xa không tự xác nhận lại.
  Thời gian chờ không làm bán kính gate lớn vô hạn.
- Trước tọa độ xuất đầu tiên, lịch sử chỉ là ứng viên. Gate thất bại thì
  bắt đầu warm-up lại, tránh khóa ID vào một điểm lỗi lúc khởi tạo.
- Sau lỗi, xóa lịch sử fit; khi trở lại gần mốc cũ phải warm-up lại.
  Gap quan sát thật >0,25 s, ID hoặc segment mới mở chuỗi mới, không nối
  quãng đường cũ. Không ép tọa độ vào sân hay ép vận tốc về 40 km/h.

Fit đầu mút có thể overshoot khi dừng/rẽ và nhạy nhiễu hơn EMA. Gate bảo
thủ có thể loại chuyển động thật sau đoạn lỗi dài, hoặc giữ lỗi dịch chậm/
ID nhầm gần nhau. Chuỗi sai nhất quán ngay từ đầu vẫn không thể xác minh
chỉ từ tọa độ. Không coi bộ lọc là nhận diện danh tính hoặc chứng nhận vị trí.

## Phát triển và tách cửa sổ đánh giá

Nguồn và định nghĩa chỉ số như `METRICA_BENCHMARK.md`: bốn CSV Metrica ở
commit e706dd506b360d69d9d123d5b8026e7294b13996, khóa SHA256, sân 105 × 68 m,
25 FPS gốc. Đây là tọa độ tham chiếu công bố, không phải ground truth tuyệt đối.
Ghi nhận nguồn: [Metrica Sports Sample Data](https://github.com/metrica-sports/sample-data).

1. Dùng [60,120) giây để phát triển v2. Không coi đây là holdout nữa.
2. Khóa v2 rồi thử [180,240), seed 1618/5772/8119. Phát hiện một số ID
   chỉ có 1–3 điểm warm-up rồi bị loại gần hết cửa sổ khi nhiễu lớn xuất
   hiện trong khởi tạo. Ví dụ Game 2, seed 1618, ID 1015 không xuất điểm nào.
   Do dùng phát hiện này để sửa, cửa sổ đó trở thành dữ liệu phát triển.
   Manifest và artifact thử nghiệm được giữ, không chỉ báo kết quả tốt.
3. Chốt v2.1 với khởi tạo ứng viên, không chỉnh tham số sau khi xem kết quả
   [300,360) giây, seed 1414/1732/2236, hiệp 1 ở cả hai trận. Manifest
   `docs/fixtures/metrica_holdout_v2_1.json` được tạo trước lượt này.
   Mã PitchSmoother khóa SHA256
   `a4f17fb993a0d2108c3c1680788238924652e8622e1399a981c1bc38e4e9aa1d`
   tại thời điểm chạy; method `causal_linear_endpoint_v2_1` trong JSON.

Chạy baseline v1 từ Git db575e4 và v2.1 trên đúng manifest holdout cuối:
26 lượt mỗi bộ (clean một seed/trận, bốn lỗi × ba seed/trận), tổng 52 lượt.
Chạy thêm 26 lượt v2.1 trên cửa sổ phát triển để đối chiếu lịch sử. Dữ liệu
và RNG đầu vào raw được audit khớp giữa v1/v2.1. Holdout là tách thời gian
trong cùng hai trận, chưa chứng minh tổng quát sang trận/camera khác.

## Kết quả holdout cuối [300,360)

Số trong bảng là median độc lập qua ba seed, clean chỉ một lượt. RMSE dùng
đúng timestamp hiện tại. Raw-common chỉ lấy frame/ID được v2.1 xuất;
v1 và v2.1 có tập điểm giữ lại khác nhau, phải đọc cùng coverage.

| Trận / lỗi | RMSE raw-all (m) | v1 (m) | v2.1 (m) | Raw-common v2.1 (m) | Coverage v2.1 |
|---|---:|---:|---:|---:|---:|
| 1 / clean | 0.0000 | 0.1940 | 0.0034 | 0.0000 | 99.85% |
| 1 / noise | 0.2123 | 0.2167 | 0.1541 | 0.2123 | 99.79% |
| 1 / spikes | 1.2728 | 0.2176 | 0.1549 | 0.2124 | 96.93% |
| 1 / gaps | 0.2123 | 0.2176 | 0.1543 | 0.2122 | 96.35% |
| 1 / relocation | 1.3052 | 1.1734 | 0.1542 | 0.2124 | 98.64% |
| 2 / clean | 0.0000 | 0.2168 | 0.0051 | 0.0000 | 99.85% |
| 2 / noise | 0.2118 | 0.2376 | 0.1534 | 0.2117 | 99.81% |
| 2 / spikes | 1.3085 | 0.2384 | 0.1542 | 0.2118 | 96.80% |
| 2 / gaps | 0.2120 | 0.2365 | 0.1536 | 0.2120 | 96.48% |
| 2 / relocation | 1.3021 | 1.1774 | 0.1536 | 0.2119 | 97.48% |

| Trận / lỗi | Coverage điểm v1 → v2.1 (%) | Thời gian metrics (%) | MAE tốc độ (km/h) | Bias toàn cửa sổ (%) | Bias phần được cộng (%) |
|---|---:|---:|---:|---:|---:|
| 1 / noise | 99.82 → 99.79 | 99.42 → 99.38 | 0.58 → 0.85 | -0.68 → 1.45 | 0.43 → 2.81 |
| 1 / spikes | 98.85 → 96.93 | 91.77 → 89.94 | 0.58 → 0.85 | -8.42 → -8.30 | 0.63 → 3.04 |
| 1 / relocation | 99.41 → 98.64 | 97.71 → 97.67 | 0.57 → 0.84 | -1.84 → 0.41 | 0.36 → 2.92 |
| 2 / noise | 99.82 → 99.81 | 99.57 → 99.57 | 0.57 → 0.84 | -0.30 → 1.41 | 0.21 → 1.89 |
| 2 / spikes | 98.80 → 96.80 | 91.40 → 89.38 | 0.59 → 0.86 | -8.37 → -8.94 | 0.44 → 1.72 |
| 2 / relocation | 99.41 → 97.48 | 97.86 → 96.68 | 0.58 → 0.84 | -2.54 → -2.54 | 0.14 → 1.94 |

Các chỉ số metrics dùng cadence >=0,5 s như trước. Thời gian đại diện khác
coverage điểm; bias toàn cửa sổ gồm phần bị bỏ và đuôi chưa đủ cadence.
Bias phần được cộng so đúng đường tham chiếu giữa anchor thực sự được cộng,
không lấy khoảng cách hai đầu thay cho đường cong. MAE tốc độ trọng số thời gian.

Holdout có 65.443 điểm tham chiếu phân biệt. Với noise, RMSE raw-common
khoảng 0,212 m giảm còn 0,153–0,154 m; baseline v1 là 0,217/0,238 m.
Lag lưới v2.1 chọn 0 ms, so v1 thường 120 ms (relocation Game 1: 80 ms).
Lưới chỉ có độ phân giải 40 ms; không khẳng định độ trễ thật bằng 0 trong
mọi chuyển động hoặc áp kết quả 25 FPS trực tiếp cho video 60 FPS.

Cả sáu lượt relocation cuối loại 330/330 điểm lỗi lớn; v1 giữ 264/330.
Đây là fault injection cụ thể, không phải chứng minh phát hiện mọi ID switch.
Đổi lại, MAE tốc độ noise tăng khoảng 0,57–0,58 → 0,84–0,85 km/h và bias
covered-distance dương lớn hơn. Với spikes, coverage điểm chỉ còn khoảng
96,8–96,9%, thời gian metrics khoảng 89–90%; vẫn thiếu khoảng 8–9% đường
tham chiếu toàn cửa sổ. Không nghiệm thu bằng RMSE vị trí riêng lẻ.

Không còn trajectory không xuất được điểm nào trên holdout cuối. Tuy nhiên
Game 2, relocation, ID 4 chỉ giữ khoảng 70,8–71,0% điểm ở cả ba seed:
gate bảo thủ vẫn có thể mất nhiều phần chuyển động thật sau lỗi. Coverage
trung bình cao không bảo đảm từng cầu thủ được theo dõi đủ.

## Replay clip thật và kiểm tra

Replay đúng 5.215 dòng thô / 30 ID của `team_roles_final`, không chạy lại
detector hoặc bù camera. Bản cắt clean nguồn SHA256
`86f6f04ce05ac464269dfa4d831bef0c12c3654acdd2fa3c1b6379f864597b2e`.

| Mục | v1 | v2.1 |
|---|---:|---:|
| Điểm được xuất | 4.935 | 4.730 |
| ID có tọa độ | 27 | 27 |
| Cặp frame liên tiếp | 4.847 | 4.658 |
| Cặp suy ra >40 km/h | 16 | 98 |
| p95 tốc độ từng frame | 23,47 | 31,17 km/h |

V2.1 có 363 warming_up, 122 jump_rejected, 206 yêu cầu ngắt mốc (gồm
khởi tạo/gap), không còn trạng thái reacquiring. Dữ liệu lọc frame 1086–1350;
A/B/referee/unknown = 2109/2097/139/385. Kiểm tra schema, nhãn/khóa thô,
diagnostic accepted, samples và heatmap đều khớp 4.730 dòng. Bbox/video cũ
không đổi; chưa xuất lại video CUDA ở phiên này vì chỉ đổi tọa độ.

Vị trí tham chiếu cải thiện không đồng nghĩa tốc độ từng frame ít nhiễu hơn:
clip này v2.1 giữ ít điểm hơn và còn nhiều cặp nhanh hơn v1. Chưa có vị trí
thực độc lập trong clip để tính sai số thật; không coi đây là nghiệm thu
quãng đường/tốc độ, không lấy số thấp hơn làm bằng chứng đúng hơn.

Kiểm thử: chuyển động đều/đứng yên có nhiễu, dừng/rẽ qua trajectory Metrica,
timestamp không đều và cả hai trục, teleport đơn/kéo dài/trở về/gap/segment,
nhiễu khi khởi tạo ở 25 và 60 FPS, không ép tốc độ, pipeline codec/ByteTrack.
Test clip tĩnh chấp nhận sai số số thực 1e-10 m thay vì yêu cầu distance == 0
tuyệt đối sau hồi quy; không nới kiểm tra chuyển động vật lý.

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_pitch_v21_final
```

143 passed, 1 network deselected; một cảnh báo Starlette có sẵn.

## Tái tạo và artifact

Dùng lệnh tải có hash trong `METRICA_BENCHMARK.md`. Tại gốc repo, đầu ra
phải là file mới (đổi tên khi đã tồn tại):

```powershell
.\.venv\Scripts\python.exe -m backend.cv.metrica_benchmark --data-dir data/raw/metrica --output data/processed/metrica_benchmark_v2/development_final.json
.\.venv\Scripts\python.exe -m backend.cv.metrica_benchmark --data-dir data/raw/metrica --manifest docs/fixtures/metrica_holdout_v2_1.json --output data/processed/metrica_benchmark_v2/holdout_final.json
```

Để chạy đúng v1 trên holdout cuối mà không thay file production, có thể nạp
mã từ commit baseline trong một tiến trình Python riêng (chạy từ gốc repo).
Đây chỉ là cách tái tạo so sánh, không đường chạy của ứng dụng:

```powershell
@'
import json, subprocess, sys, types
from pathlib import Path
from backend.cv import metrica_benchmark as bench
source = subprocess.check_output(['git','show','db575e4:backend/cv/pitch_smoother.py'], text=True, encoding='utf-8')
module = types.ModuleType('baseline_filter')
sys.modules[module.__name__] = module
exec(compile(source, 'db575e4:pitch_smoother.py', 'exec'), module.__dict__)
module.PitchSmoother.method = 'median3_ema_v1'
bench.PitchSmoother = module.PitchSmoother
output = Path('data/processed/metrica_benchmark_v2/holdout_final_baseline.json')
report = bench.run('data/raw/metrica', 'docs/fixtures/metrica_holdout_v2_1.json', output)
report['filter'].update(time_constant_s=module.PitchSmoother.time_constant_s, implementation_commit='db575e4')
output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
'@ | .\.venv\Scripts\python.exe -
```

Artifact cục bộ (không commit CSV/video/cache):

- `data/processed/metrica_benchmark_v2/`: development/holdout thử v2 và
  baseline tương ứng; development_final.json, holdout_final.json,
  holdout_final_baseline.json và comparison_final_summary.json cho bản cuối.
- `data/processed/clip_11f23eea/pitch_smoothing_v2_1_check/`: tracking.jsonl,
  quality.json, metrics.json, summary.json. Giữ nguyên bộ v1 và thử v2.
- Helper replay/audit cục bộ ở `.tmp/`; kiểm tra cốt lõi đã có trong tests.

## Quyết định

Giữ bộ lọc tùy chọn để đánh giá tiếp. V2.1 giải quyết hai tình huống thử
giảm trễ vị trí và bỏ relocation lớn; chưa nghiệm thu chỉ số thực địa hoặc
chuyển bước 5. Bước tiếp theo nên kiểm tra đánh đổi sai số tốc độ/coverage,
nhiễu tương quan camera/bbox, rẽ/dừng mạnh, ID đổi gần nhau và mốc gán nhãn
độc lập trên video; không điều chỉnh tiếp trên holdout cuối rồi gọi nó là độc lập.

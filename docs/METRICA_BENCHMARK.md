# Đánh giá bộ lọc và chỉ số bằng tọa độ tham chiếu Metrica

Đây là báo cáo baseline v1 tại commit `db575e4`. Bộ lọc hiện tại đã thay đổi;
kết quả và protocol phát triển/holdout v2 nằm trong `METRICA_FILTER_V2.md`.
Đánh giá mới nhất (v3, có nhiễu tương quan theo thời gian) nằm trong
`METRICA_FILTER_V3.md`.
Chạy lệnh bên dưới trên mã hiện tại sẽ đánh giá bộ lọc hiện tại, không tái
tạo số baseline v1 trừ khi dùng đúng phiên bản Git.

Ngày: 22/10/2026. Đây là phép đánh giá bộ lọc tọa độ và PitchMetrics trên
quỹ đạo tham chiếu có chuyển động bóng đá, không phải phép đo YOLO,
ByteTrack, phân đội hoặc homography của video `vid1.mp4`. Không chỉnh bộ
lọc để khớp kết quả đánh giá, không đổi dependency/hợp đồng/API.

## Nguồn và khả năng tái tạo

Nguồn: [Metrica Sports Sample Data](https://github.com/metrica-sports/sample-data),
commit `e706dd506b360d69d9d123d5b8026e7294b13996`. Theo
[README tại commit này](https://github.com/metrica-sports/sample-data/blob/e706dd506b360d69d9d123d5b8026e7294b13996/README.md),
dữ liệu hai trận CSV được ẩn danh, tọa độ 0–1 có gốc trái trên, sân 105 × 68 m.
Chuyển đổi nội bộ `x_m = 105*x`, `y_m = 68*(1-y)`, không tự lật hướng tấn công.
Lượt này không có phép đo độc lập để kiểm chứng sai số của nguồn; dùng từ
**tham chiếu**, không coi sai số bằng 0 trong test là chứng nhận Metrica tuyệt đối.

Manifest `docs/fixtures/metrica_benchmark.json` khóa bốn CSV Home/Away của
Game 1/2 bằng URL commit và SHA256, cùng cấu hình thí nghiệm. Không commit
CSV, không tải video. Loader dùng thư viện chuẩn CSV, đọc header ba dòng,
bỏ bóng, bỏ cặp tọa độ thiếu/không hữu hạn/ngoài sân; không ép vào đường biên.
Các đoạn thiếu tự nhiên của cùng người được tách trước mọi phép so sánh.
NaN của các cột cầu thủ không ra sân không được coi là detection thất bại.

Home ánh xạ A, Away ánh xạ B. ID Home lấy số trong header Player; Away cộng
1000 để tránh trùng. Đây là định danh cục bộ dữ liệu ẩn danh, không liên kết
với cầu thủ StatsBomb hoặc danh tính trong video.

Tải có kiểm tra hash, từ PowerShell tại gốc repo:

```powershell
$metricaManifest = Get-Content docs/fixtures/metrica_benchmark.json -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path data/raw/metrica -Force | Out-Null
foreach ($metricaSpec in $metricaManifest.files) {
    $metricaTarget = Join-Path (Resolve-Path data/raw/metrica).Path $metricaSpec.filename
    if (-not (Test-Path -LiteralPath $metricaTarget)) {
        Invoke-WebRequest -Uri $metricaSpec.url -OutFile $metricaTarget
    }
    $metricaHash = (Get-FileHash -LiteralPath $metricaTarget -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($metricaHash -ne $metricaSpec.sha256) { throw "Metrica SHA256 mismatch" }
}
.\.venv\Scripts\python.exe -m backend.cv.metrica_benchmark --data-dir data/raw/metrica --output data/processed/metrica_benchmark/results.json
```

Đầu ra phải là file mới, chương trình không ghi đè. Chạy lại dùng tên JSON
khác. SHA sai thì dừng trước đánh giá. Không cần thư viện hoặc API mới.

## Thiết kế khóa trước khi chạy

- Lấy hiệp 1, thời gian [60,120) giây ở cả hai trận, toàn bộ người có đủ
  dữ liệu hợp lệ trong cửa sổ. Cadence suy từ frame/time CSV và được kiểm
  tra nhất quán; không nội suy lên 60 FPS của video.
- `clean`: giữ nguyên tọa độ tham chiếu, chỉ một lượt vì không ngẫu nhiên.
- `noise`: cộng Gaussian độc lập sigma 0,15 m trên mỗi trục.
- `spikes`: noise như trên + xác suất 1% dịch điểm khoảng (±10, ±8) m hướng
  vào sân. Không đổi tọa độ tham chiếu hoặc ID.
- `gaps`: noise + ba đoạn mất quan sát dài 0,6 giây tại giây 75/90/105.
- `relocation`: noise + dịch vị trí liên tục 0,6 giây từ giây 90 bằng cùng
  vector (±10, ±8) m. Kiểm tra lỗi vị trí kéo dài, không chỉ điểm lẻ.
- Các trường hợp có lỗi chạy seed 1729/2718/3141, dùng RNG tách theo trận/ID;
  mẫu nhiễu nền cùng seed được giữ tương ứng giữa các tình huống. Điểm bị
  nhiễu ra ngoài sân được bỏ như đầu vào pipeline, ghi số lượng riêng.

Giữ nguyên PitchSmoother từ commit `d221430`: trung vị 3 + EMA tau 0,08 s,
gate 40 km/h + 0,5 m, gap 0,25 s, xác nhận lại 3 điểm, chờ span 0,08 s.
Giữ cách lấy mẫu metrics >=0,5 s, gap tối đa 1 s, ngưỡng 40 km/h. Các
trường hợp này không mô phỏng đầy đủ tương quan nhiễu bbox/camera của video.

## Định nghĩa phép đo

- RMSE vị trí thô trên mọi quan sát đầu vào; RMSE lọc trên điểm được xuất.
  Báo thêm RMSE thô trên đúng các frame/ID lọc giữ lại để không nhầm hiệu
  quả bỏ điểm với hiệu quả thay tọa độ.
- Coverage điểm = số quan sát / số điểm tham chiếu hợp lệ. Không gọi phần
  đầu khởi tạo, điểm bị loại hay gap là đã có vị trí đo.
- Quãng đường tham chiếu là tổng đoạn nối các frame gốc liên tiếp trong
  cùng đoạn hợp lệ. Không nối khoảng thiếu tự nhiên, không phải tổng trận.
- Sai lệch full-distance = (distance metrics - reference toàn cửa sổ) /
  reference. Nó gồm cả tác động bỏ điểm và phần đuôi chưa đủ chu kỳ lấy mẫu.
- Sai lệch covered-distance chỉ so với đường tham chiếu trên **đúng các
  khoảng thực sự được production metrics cộng**. Tham chiếu cộng đường
  gốc bên trong khoảng, không chỉ lấy dây cung đầu/cuối để che mất lỗi cắt góc.
- Speed MAE theo các khoảng được cộng = sai khác tốc độ trung bình đường
  tham chiếu và tốc độ metrics, trọng số thời gian. Không là sai số tốc độ
  tức thời hay tốc độ đỉnh ngoài các khoảng đó.
- Represented time = tổng duration metrics / duration tham chiếu hợp lệ.
  Với bản thô, metrics có thể nối qua gap nhân tạo dưới ngưỡng 1 s; vì vậy
  đây là thời gian được đại diện bởi các cặp đo, không bảo đảm có quan sát
  ở mọi thời điểm trong khoảng.
- Apparent lag: so sánh vị trí lọc tại t với vị trí tham chiếu t-lag trên
  lưới 0–6 frame, cùng tập điểm cho tất cả lag. Đây là diagnostic theo lưới,
  không phải độ trễ hệ thống đo độc lập hoặc thao tác chỉnh lại output.

Tham chiếu và tọa độ bị nhiễu tách biệt trong bộ nhớ, không sửa reference.
Các phép tính thực sự gọi PitchSmoother và PitchMetrics đang dùng; lớp audit
chỉ ghi lại các khoảng metrics đã cộng, không triển khai một bộ tính khác.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_metrica_full
```

**135 passed, 1 network test deselected**, cảnh báo Starlette cũ. Test mới
kiểm tra đổi hệ tọa độ, bỏ bóng/NaN/ngoài sân, tách khoảng thiếu tự nhiên,
seed tái lập và không sửa tham chiếu, lỗi kéo dài/gap, đường cong chuẩn có
độ dài biết trước, độ trễ/coverage và nguồn sai hash/đầu ra đã tồn tại.

## Kết quả thực chạy

Đủ **26 lượt**, 22 quỹ đạo mỗi trận, hai cửa sổ 60 giây, **65.051 điểm**
tham chiếu phân biệt, tần số thực 25 FPS. Các số sau là median ba seed
trong từng trận; clean chỉ một lượt. Range từng seed được giữ trong JSON,
không dùng các median này như khoảng tin cậy thống kê.

Game 1 có 926 điểm ngoài sân bị loại, Game 2 có 23; reference và mẫu số chỉ
gồm các đoạn hợp lệ còn lại. NaN của cầu thủ dự bị không được tính như
detection thất bại.

| Trận | Tình huống | RMSE thô (m) | RMSE thô cùng điểm giữ (m) | RMSE lọc (m) | Điểm giữ (%) | Lag lưới (ms) |
|---|---|---:|---:|---:|---:|---:|
| 1 | clean | 0,000 | 0,000 | 0,183 | 99,75 | 120 |
| 1 | noise | 0,212 | 0,212 | 0,202 | 99,42 | 120 |
| 1 | spikes | 1,289 | 0,212 | 0,203 | 98,41 | 120 |
| 1 | gaps | 0,212 | 0,212 | 0,203 | 96,02 | 120 |
| 1 | relocation | 1,318 | 1,187 | 1,184 | 99,01 | 80 |
| 2 | clean | 0,000 | 0,000 | 0,249 | 99,87 | 120 |
| 2 | noise | 0,212 | 0,212 | 0,267 | 99,83 | 120 |
| 2 | spikes | 1,239 | 0,212 | 0,268 | 98,91 | 120 |
| 2 | gaps | 0,212 | 0,212 | 0,267 | 96,42 | 120 |
| 2 | relocation | 1,299 | 1,168 | 1,181 | 99,43 | 120 |

| Trận | Tình huống | Bias quãng đường toàn cửa sổ thô (%) | Bias toàn cửa sổ lọc (%) | Bias phần được đo lọc (%) | Thời gian đại diện lọc (%) | MAE tốc độ thô → lọc (km/h) |
|---|---|---:|---:|---:|---:|---:|
| 1 | clean | -3,86 | -4,34 | -1,87 | 99,27 | 0,110 → 0,220 |
| 1 | noise | 4,40 | -3,24 | 0,28 | 99,02 | 1,234 → 0,610 |
| 1 | spikes | 3,26 | -10,72 | 0,58 | 91,09 | 1,250 → 0,619 |
| 1 | gaps | 2,95 | -7,72 | -0,05 | 94,04 | 1,195 → 0,620 |
| 1 | relocation | 2,44 | -4,83 | 0,25 | 97,31 | 1,241 → 0,614 |
| 2 | clean | -0,71 | -0,86 | -0,57 | 99,72 | 0,031 → 0,233 |
| 2 | noise | 2,25 | -0,49 | 0,05 | 99,45 | 1,140 → 0,580 |
| 2 | spikes | 1,36 | -7,80 | 0,49 | 92,03 | 1,142 → 0,594 |
| 2 | gaps | 0,07 | -5,80 | -0,24 | 94,36 | 1,131 → 0,592 |
| 2 | relocation | 0,81 | -1,77 | -0,03 | 97,79 | 1,124 → 0,572 |

## Kết luận và giới hạn sử dụng

1. **Không cải thiện mọi trường hợp.** Clean không có nhiễu được thêm;
   raw RMSE bằng 0 do định nghĩa tham chiếu, còn lọc có lệch 0,183/0,249 m.
   Với noise nhẹ Game 2, RMSE tăng 0,212 → 0,267 m, dù MAE tốc độ trung bình
   giảm. Chỉ số chuyển động mượt hơn không chứng minh vị trí hiện tại đúng hơn.
2. **Spikes đơn được loại tốt nhưng coverage chuyển động giảm.** Tất cả
   điểm được gắn fault spikes ở các lượt này không được xuất. Coverage điểm
   vẫn khoảng 98–99%, nhưng thời gian metrics đại diện chỉ khoảng 91–92%;
   full-distance bị thiếu khoảng 8–11%. Không so phần quãng đường này như
   tổng của toàn cửa sổ. RMSE thô trên cùng điểm giữ cho thấy một phần lớn
   mức giảm RMSE toàn bộ đến từ bỏ spikes, không chỉ từ thay tọa độ.
3. **Lỗi kéo dài chưa được xử lý đúng.** Với relocation, mỗi lượt có 330
   điểm lỗi (22 × 15 frame), nhưng **264/330, tức 80%**, vẫn được giữ sau
   khi bộ lọc xác nhận lại chuỗi. Sai số vị trí còn khoảng 1,18 m, trong khi
   bias covered-distance gần 0: phép tịnh tiến sai có thể vẫn cho quãng
   đường/tốc độ có vẻ tốt. Không dùng smoothing thay cho kiểm chứng camera,
   điểm chân hoặc định danh.
4. **Lag có ý nghĩa.** Phần lớn diagnostic chọn 120 ms ở 25 FPS. Lưới chỉ
   40 ms/bước; đây không phải phép đo độ trễ tuyệt đối và không được lấy số
   này áp thẳng cho video 60 FPS. Trung vị 3 frame có độ dài thời gian khác
   khi FPS đổi, dù EMA dùng dt thực.
5. **Chưa nghiệm thu bước 4 hoặc bật bộ lọc đại trà.** Giữ --smooth-pitch
   tùy chọn, không áp lên Metrica sạch để tuyên bố nâng chất lượng. Bộ hiện
   tại phù hợp hơn với mục đích loại điểm nhảy đơn và giảm nhiễu khi đã có
   kiểm tra coverage; chưa bảo đảm vị trí hoặc tổng chuyển động đúng.

Việc tiếp theo có căn cứ là xử lý đánh đổi độ trễ/sai số vị trí và chính
sách xác nhận lại sau vị trí sai kéo dài, sau đó đánh giá trên cửa sổ/trận
chưa dùng để chỉnh phương pháp. Không vặn ngưỡng rồi gọi lại các lượt ở đây
là tập kiểm định độc lập. Tốc độ đỉnh, ID switch thật, occlusion/camera thực
và chất lượng phân đội nằm ngoài bằng chứng của benchmark này.

## Artifact và kiểm tra số liệu

- `data/processed/metrica_benchmark/results.json`: dữ liệu đầy đủ 26 lượt,
  thông số bộ lọc, hash/nguồn và audit từng quỹ đạo.
- `summary.json`: tóm tắt từng lượt; `benchmark_comparison.png`: biểu đồ
  trước/sau, median và range theo seed, có ghi nguồn Metrica Sports.
- `.tmp/summarize_metrica.py`: helper audit/biểu đồ cục bộ, chưa đóng gói.
  Đã kiểm tra 26 khóa lượt không trùng, 22 trajectory mỗi lượt, coverage
  không vượt mẫu số, RMSE tái tính từ SSE và tổng quãng đường khớp từng
  track. Kết quả CLI JSON không chứa NaN/Infinity.

CLI và test được commit, nên có thể tái tạo JSON từ manifest bằng lệnh
đã nêu; helper vẽ biểu đồ chỉ là tiện ích cục bộ. CSV/cache/ảnh không commit.
Khi dùng công khai cần ghi nhận nguồn Metrica Sports như README yêu cầu.
Không sửa PitchSmoother, PitchMetrics hoặc pipeline video trong lượt này.

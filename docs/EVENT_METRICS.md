# Chỉ số sự kiện và thẻ phương pháp — 02/11/2026

Theo yêu cầu tích hợp phần phù hợp từ football-docs, trang **Phân tích trận**
hiển thị bốn chỉ số từ StatsBomb cùng công thức, cách đọc, giới hạn và nguồn.
Không cần cài thêm gói hoặc MCP. Schema `AnalysisResult`, `MetricItem`,
`EventRow`, `TrackingRow` và hệ sân trong DATA_CONTRACT giữ nguyên.

## Phạm vi và cách tính

| Khóa biến thể | Công thức trên hệ sân 105×68 m | Cách đọc |
| --- | --- | --- |
| `ppda.statsbomb-hudl` | Chuyền thành công của đối thủ ở x<63 / hành động phòng ngự đội được chọn ở x>=42 | Chuyền/hành động; thấp hơn gợi ý pressing cao hơn, chưa chứng minh hiệu quả |
| `field_tilt.stats-perform-2016` | Chuyền đội ở x>=70 / chuyền hai đội ở phần ba sân tấn công riêng | Tỷ lệ0–1, giao diện hiển thị%; phép xấp xỉ Opta bằng StatsBomb |
| `pass_completion.statsbomb-hudl` | Chuyền thành công / toàn bộ lần chuyền của đội | Tỷ lệ0–1, giao diện hiển thị% |
| `xg.statsbomb-hudl` | Tổng shot_statsbomb_xg của đội | Bàn kỳ vọng; không phải xG XGBoost của dự án |

Tất cả tính trên hiệp1–4, gồm hiệp phụ, bỏ hiệp5 (luân lưu). Không giới hạn
trước lần thay người đầu tiên như sơ đồ chuyền bóng. Tỷ lệ và PPDA được làm
tròn4chữ số thập phân như nguồn tham chiếu; UI hiển thị2chữ số.

PPDA đếm Duel loại Tackle, Interception, Pass loại Interception,
Dribbled Past và Foul Committed; không thêm Pressure/Ball Recovery. Mỗi đội
StatsBomb đều hướng x tăng: vùng của đối thủ phải dùng x<63, không dùng
cùng điều kiện x>=42. Không áp dụng cách này cho tracking video.

Field tilt đếm cả chuyền thành công/thất bại; bỏ `pass_cross=true`,
`pass_type=Throw-in`, `pass_body_part=Keeper Arm`. Cách đếm là phép xấp xỉ
được nêu rõ, không gán là giá trị Opta chính thức hoặc tỷ lệ giữ bóng theo
thời gian. Nguồn phương pháp không chốt xử lý chuyền thất bại.

Pass completion bao gồm tạt bóng, bóng chết và ném biên; ô trống của cột
`pass_outcome` StatsBomb là hoàn thành. Out/Pass Offside/Unknown/Incomplete/
Injury Clearance đều là lần chuyền không thành công. Thiếu cả cột khác với
ô trống; không mặc định toàn bộ chuyền thành công khi thiếu cột.

## Tổ chức và API

`backend/common/metric_catalog.json` là nguồn định nghĩa dùng chung cho
backend và frontend qua API. Mỗi card có key, version, formula, required_columns,
interpretation, caveats, source_url, reference_url, loại mapping và trạng thái
computed/documented; Pydantic kiểm cấu trúc, từ chối khóa trùng.

- `GET /api/matches/metric-definitions`: sáu card, gồm bốn chỉ số tính mới,
  một card tài liệu hóa xG của dự án và một card bề ngang cụm video hiện có.
- `GET /api/matches/{match_id}/event-metrics?team=Brazil`: trả `AnalysisResult`
  với source=statsbomb, bốn `MetricItem` có scope=team và subject=Brazil.
- Đội không thuộc dữ liệu hoặc mã trận cache không khớp trả422; trận không
  tồn tại trả404; lỗi truy cập StatsBomb trả502.
- Giá trị không tính được là chuỗi giải thích trong trường `value` hiện có,
  không thêm null/status vào schema. UI hiện “Chưa đủ dữ liệu” và nguyên nhân.
- Thiếu cột chỉ ảnh hưởng chỉ số cần cột đó. Thiếu đội/hiệp/type hoặc trộn
  nhiều trận khiến các chỉ số chưa có giá trị. Thiếu vị trí không được âm
  thầm bỏ khỏi phép đếm theo vùng. Thiếu một xG cú sút không xuất tổng phần.
- Không có cú sút và cột xG hợp lệ cho tổng0; mẫu số0 của tỷ lệ/PPDA là thiếu
  giá trị. Mỗi xG cú sút phải nằm trong[0,1].

Loader chuyển thêm các trường tên `pass_type`, `pass_body_part`, `duel_type`
về chuỗi trước khi ghi CSV nếu đầu vào chứa dict id/name; không tạo cột
đang vắng mặt. Giao diện chờ request pass-network hoàn tất trước request
metrics để tránh hai lượt đầu tiên cùng tải/ghi cache của một trận mới.
Không đổi dữ liệu demo, upload video hoặc mô hình đã có.

## Nguồn tham khảo và đối chiếu độc lập với mã tính

Áp dụng ý tưởng metric cards/variant/provenance và fixture từ
[football-docs](https://github.com/withqwerty/football-docs/tree/b1fb1c175226b9726ac31524bf232d54cf960745/metrics).
Mã tính được viết cho DataFrame/hệ mét của dự án; không import hay chạy code
repo ngoài trong runtime. Nguồn phương pháp gốc được lưu trong từng card.
Trang Hudl hiện không trích được công thức bằng công cụ đọc web trong phiên
này, nên công thức PPDA đối chiếu theo card/mã tham chiếu đã ghim, không
tuyên bố đã xác minh lại nội dung Hudl trực tiếp. Bài
[Stats Perform](https://www.statsperform.com/insights/how-we-measure-pressure/)
đọc được và hỗ trợ định nghĩa field tilt cùng giới hạn giải thích pressing.

Fixture `docs/fixtures/event_metrics_reference_v1.json` khóa:

- football-docs commit `b1fb1c175226b9726ac31524bf232d54cf960745`;
- StatsBomb Open Data commit `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`;
- SHA256 của trận3869685: `a0b0036d50c10a4c8879d1ee9f24a7502ec2cfb264a61951c8d500dfc897ec35`;
- giá trị kỳ vọng từ card đã xuất bản, không sinh giá trị kỳ vọng bằng hàm
  của dự án. Không đưa JSON sự kiện gốc vào Git.

| Đội | PPDA | Field tilt | Pass completion | Tổng xG StatsBomb |
| --- | --- | --- | --- | --- |
| Argentina | 7,4222 | 61,86% | 80,81% | 2,7583 |
| France | 9,0909 | 38,14% | 76,14% | 2,2726 |

Chạy offline từ gốc repo, dùng nguồn đã có trong data/raw:

```powershell
.\.venv\Scripts\python.exe -m backend.tactics.verify_event_metrics
```

Verifier kiểm hash trước khi tính, chuyển JSON qua loader sang hệ mét,
ghi/đọc CSV trong bộ nhớ rồi so cả trước/sau với số kỳ vọng, tolerance1e-4.
Nguồn thiếu khiến CLI thất bại rõ ràng; không tự tải hay dùng nguồn khác.
Test reference được skip nếu máy khác chưa có source cục bộ; các test
synthetic/API vẫn chạy. Một trận chuẩn chỉ xác minh phép tính/adapter,
không chứng nhận hiệu quả huấn luyện hoặc độ chính xác video.

## Lệnh kiểm tra

Đặt temp trong repo để các test CLI tuân thủ kiểm đường dẫn của dự án:

```powershell
New-Item -ItemType Directory -Force .tmp/event-metrics-tests | Out-Null
$env:TEMP = (Resolve-Path .tmp/event-metrics-tests).Path
$env:TMP = $env:TEMP
.\.venv\Scripts\python.exe -m pytest -v --basetemp=.tmp/event-metrics-pytest-check
```

Frontend: cd frontend rồi chạy `npm test`, `npm run build`, `npm run lint`.
Đã đạt466test Python (1network deselected),15test Node, build và lint;
44test liên quan được chạy lại sau rà cuối. Còn cảnh báo có sẵn về
Starlette/SHAP, FastRefresh và kích thước bundle. Lượt đầu dùng temp mặc
định ngoài repo gây18test CLI lỗi; lệnh đặt temp trong repo ở trên đã đạt.
HTTP thật qua proxy Vite cho hai đội Brazil/Belgium ở8650, danh mục6card
và route /match đều trả200; snapshot có hash tại
`docs/fixtures/event_metrics_smoke_v1.json`. Snapshot này là kiểm API/
đường phục vụ trang trên cache cục bộ, không là ground truth độc lập cho8650.

Kiểm thủ công khi trình duyệt cho phép: mở `/match`, chọn trận/đội, mở từng
“Cách tính và nguồn”, đổi đội/trận, kiểm loading/lỗi và màn hình nhỏ. Chưa
tuyên bố visual QA đạt: Computer Use bị dừng do không xác định chắc URL.

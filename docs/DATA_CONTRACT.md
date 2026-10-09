# Hợp đồng dữ liệu

## Hệ tọa độ sân chuẩn

- Kích thước sân: `PITCH_LENGTH_M = 105` mét, `PITCH_WIDTH_M = 68` mét.
- Gốc tọa độ ở góc trái dưới sân.
- Trục `x` chạy dọc sân, từ `0` đến `105`; trục `y` chạy ngang sân, từ `0` đến `68`.
- Dữ liệu backend sử dụng hệ tọa độ sân chuẩn này cho các trường vị trí.

## Schema

Các schema được định nghĩa bằng Pydantic v2 tại `backend/common/schemas.py`.

### `TrackingRow`

Một bản ghi theo dõi cầu thủ/vật thể:

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `frame` | `int` | Chỉ số khung hình |
| `time_s` | `float` | Thời gian tính bằng giây |
| `track_id` | `int` | Định danh đối tượng được theo dõi |
| `team` | `"A" \| "B" \| "referee" \| "unknown"` | Đội hoặc loại đối tượng |
| `x_m` | `float` | Tọa độ dọc sân, mét |
| `y_m` | `float` | Tọa độ ngang sân, mét |

### `EventRow`

Một sự kiện trận đấu:

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `match_id` | `int` | Định danh trận đấu |
| `minute` | `int` | Phút của sự kiện |
| `second` | `int` | Giây của sự kiện |
| `team` | `str` | Tên/định danh đội |
| `player` | `str \| None` | Cầu thủ liên quan, nếu có |
| `event_type` | `str` | Loại sự kiện |
| `x_m`, `y_m` | `float \| None` | Vị trí bắt đầu theo hệ sân chuẩn |
| `end_x_m`, `end_y_m` | `float \| None` | Vị trí kết thúc theo hệ sân chuẩn |

### `MetricItem`

Một chỉ số phân tích:

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `key` | `str` | Khóa ổn định của chỉ số |
| `label` | `str` | Nhãn hiển thị |
| `value` | `float \| str` | Giá trị chỉ số |
| `unit` | `str \| None` | Đơn vị, nếu có |
| `scope` | `"team" \| "player" \| "match"` | Phạm vi chỉ số |
| `subject` | `str \| None` | Đội/cầu thủ tương ứng, nếu có |

### `AnalysisResult`

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `source` | `"video" \| "statsbomb"` | Nguồn dữ liệu phân tích |
| `metrics` | `list[MetricItem]` | Danh sách chỉ số |

## Chuyển đổi tọa độ StatsBomb

StatsBomb sử dụng hệ tọa độ `120 × 80`, gốc trái trên, trục `y` hướng xuống.
Hàm `statsbomb_to_pitch(x, y)` chuyển sang hệ sân chuẩn:

```text
x_m = x * 105 / 120
y_m = (80 - y) * 68 / 80
```

Kết quả trả về theo thứ tự `(x_m, y_m)`. Ví dụ:

- `(0, 0)` → `(0, 68)`
- `(120, 80)` → `(105, 0)`
- `(60, 40)` → `(52.5, 34)`

## Hướng tấn công

Dữ liệu sự kiện StatsBomb đã được chuẩn hóa sao cho mọi đội tấn công về phía
x tăng (từ trái sang phải). Dữ liệu tracking trích xuất từ video không có đặc
tính này; cần lật trục nếu muốn so sánh hướng tấn công giữa hai nguồn.

# Đối chiếu điểm chân và ID với bộ nhãn agent

Ngày: 23/10/2026. Người dùng đã xem bộ nhãn và đồng ý tiếp tục. Nguồn nhãn
vẫn là agent; xác nhận này không biến nhãn thành phép đo độc lập thực địa.
Lượt này chỉ đánh giá đầu ra đã khóa, không thay detector/tracker/phân đội,
homography/guard/bộ lọc, dependency hoặc schema/API.

## Nguồn và protocol

- Nhãn `vid1_11f23eea_agent_review.json`: quan sát ảnh không overlay dự đoán,
  pixel ước lượng bằng mắt; mã người cục bộ qua che khuất còn có thể sai.
- Chỉ tám ảnh return: 1105/1145/1185/1225/1255/1295/1325/1345. Tổng 166
  quan sát người, giữ 154 visible, loại 12 occluded/uncertain khỏi ghép chính.
  Không đánh giá tọa độ mét ở early/middle vốn chưa được guard chấp nhận.
- Khóa clean video SHA256
  `86f6f04ce05ac464269dfa4d831bef0c12c3654acdd2fa3c1b6379f864597b2e`.
  Dự đoán đóng băng trong `vid1_11f23eea_prediction_samples.json`, kèm hash
  input artifact và bộ lọc v3 từ commit f8b3976. Không chạy lại YOLO.
- Snapshot lấy từ NMS 0,5 + ByteTrack đã lưu, team_roles_final và replay
  pitch_smoothing_v3_check. Kiểm tra đủ 5.215 khóa frame/ID bbox với raw
  production, 4.735 khóa lọc nằm trong raw. Chiếu bottom-center bbox bằng
  ma trận đúng frame khớp raw trong tối đa 1,37e-6 m. Đây là khớp số học
  giữa hai artifact, **không phải sai số vị trí thực địa**.
- Raw dùng giữa cạnh dưới bbox trong pixel. Điểm v3 vốn ở tọa độ sân được
  chiếu ngược về pixel bằng chính ma trận frame đó. Thước đo ở đây so với
  điểm chân agent trên ảnh; không chứng nhận homography đúng theo mét.
- Manifest `video_review_evaluation.json` khóa dữ liệu nhãn và snapshot
  bằng SHA256 JSON chuẩn hóa (không phụ thuộc LF/CRLF). Ngưỡng chính 12 px,
  kiểm tra độ nhạy 8/12/20 px, chốt trước khi xem kết quả.

## Ghép và cách đọc số

Ghép một-một theo khoảng cách Euclid trong ảnh, không dùng nhãn đội hoặc
ID để chọn cặp. Tối đa số cặp hợp lệ trong gate, sau đó tối thiểu tổng
khoảng cách; không dùng greedy có thể bỏ mất người còn ghép được.

Cặp bị xem là mơ hồ nếu một label gần nhiều prediction, prediction gần
nhiều label visible, hoặc gần label đã loại do che khuất/không chắc. Các
cặp này không dùng đếm thay đổi ID hay đối chiếu vai trò. Prediction không
ghép visible nhưng gần label bị loại được ghi riêng, không tự gọi là FP.

Chỉ đếm thay đổi ID biểu kiến khi cùng mã nhãn ghép không mơ hồ ở hai ảnh
lấy mẫu liên tiếp, cùng đoạn, cách nhau <=90 frame. Không nối qua mẫu bị
mất/mơ hồ. Đây là chỉ báo rà soát thưa, **không phải MOT ID switches**, MOTA
hay IDF1. Nhãn tentative có thể sai; ảnh thưa không thấy hết diễn biến.

## Kết quả ngưỡng chính 12 px

| Mục | Raw | Lọc v3 |
|---|---:|---:|
| Quan sát nhãn visible / bị loại | 154 / 12 | 154 / 12 |
| Quan sát dự đoán | 153 | 140 |
| Ghép với visible | 146 | 135 |
| Cặp ghép không mơ hồ | 143 | 134 |
| Nhãn visible chưa ghép | 8 | 19 |
| Prediction chưa ghép, gần nhãn đã loại | 5 | 4 |
| Prediction chưa ghép khác | 2 | 1 |
| RMSE pixel, chỉ trên cặp ghép của từng bản | 2,997 | 2,808 |
| Khoảng mẫu có thể so ID | 116 | 99 |
| Thay đổi ID biểu kiến trên khoảng đủ điều kiện | 2 | 1 |

Không đọc 146/154 hoặc 135/154 là detector recall/độ chính xác video. Các
tập đã qua guard, on-pitch và gate ghép; nhãn agent chưa đủ chuẩn độc lập.
Số chưa ghép là trường hợp cần rà, chưa tự phân loại detection miss, FP,
nhãn sai, vị trí lệch hay warm-up. Không dùng RMSE matched-only để bỏ qua
điểm nằm ngoài gate hoặc không xuất được.

Đối chiếu công bằng hơn trên **132 cặp cùng frame, nhãn, track ID và không
mơ hồ ở cả hai bản**: RMSE raw 2,781 px, lọc 2,786 px; mean 2,410 → 2,449
px. Không có bằng chứng cải thiện rõ vị trí pixel trên mẫu này. RMSE lọc
nhìn thấp hơn ở bảng matched-only đi kèm tập điểm khác/ít hơn; không coi
đó là chứng minh lọc chính xác hơn. Sai khác rất nhỏ so với nhãn ước lượng
bằng mắt, chưa có phép đo độ lặp của người gán nhãn để kiểm định ý nghĩa.

Vai trò trên cặp không mơ hồ: raw có 63 A→A, 64 B→B, 3 referee→referee,
13 unknown; v3 có 58 A→A, 62 B→B, 3 referee→referee, 11 unknown. Không thấy
cặp known A/B/ref bất đồng trong tập chọn này, nhưng chưa phải chứng nhận
phân đội toàn clip; không bỏ unknown rồi tuyên bố 100% chính xác.

## Hai trường hợp cần rà soát

| Nhãn agent | Hai frame | Raw track ID | Đọc kết quả |
|---|---|---|---|
| B05 | 1145 → 1185 | 9 → 15 | Cả raw/v3 cùng đổi ID; ảnh gợi ý hai người che/lẫn bbox trước khi tách |
| A02 | 1295 → 1325 | 11 → 29 | Raw đếm được; v3 vẫn có ID29 nhưng ghép ở 1325 bị coi là mơ hồ |

Ảnh crop `identity_candidates.jpg` cho thấy sự chen sát/che khuất, phù hợp
với giả thuyết phân mảnh track; chưa kết luận thay đổi danh tính chuẩn.
Đặc biệt v3 đếm 1 thay vì 2 **không chứng minh sửa ID**: A02 vẫn thay ID,
chỉ bị loại khỏi phép đếm không mơ hồ. Bộ lọc tọa độ không sửa ByteTrack.

## Độ nhạy gate

| Gate (px) | Raw ghép | V3 ghép | Khoảng so ID raw/v3 | Đổi ID biểu kiến raw/v3 |
|---|---:|---:|---|---|
| 8 | 145 | 135 | 117 / 101 | 2 / 2 |
| 12 | 146 | 135 | 116 / 99 | 2 / 1 |
| 20 | 146 | 136 | 101 / 88 | 0 / 0 |

Gate lớn làm nhiều cặp trở thành mơ hồ nên số khoảng có thể so ID giảm.
Không được chọn 20 px vì “không còn lỗi ID”. Tất cả ba gate được giữ trong
JSON, không điều chỉnh nhãn hay pipeline để cải thiện kết quả này.

## Quyết định cho dự án

- Video dùng được để minh họa detection/tracking/phân đội, lọc người ngoài
  sân và xuất tọa độ có guard trong cửa sổ ngắn. Ghi rõ ID cục bộ, mất điểm
  và trường hợp che khuất; chưa định danh cầu thủ hoặc thống kê cả trận.
- Bước 4 đã có chức năng và kiểm thử tổng hợp; **chưa nghiệm thu độ chính
  xác vị trí/quãng đường/tốc độ thực địa**. Không đưa số mét/km/h của clip
  vào báo cáo như số liệu thực đã được kiểm chứng.
- Kết thúc đợt rà soát này với giới hạn đã ghi, không tiếp tục chỉnh ngưỡng
  chỉ để đẹp số trên cùng clip. Công việc tiếp theo là bước 5 trên dữ liệu
  tham chiếu Metrica theo phương án dự phòng trong ROADMAP; giữ nhánh video
  cho minh họa/kiểm chứng bổ sung. Metrica ẩn danh không tự liên kết danh tính
  với StatsBomb; mọi so sánh đội hình phải ghi rõ giới hạn nguồn.

## Tái tạo và kiểm tra

```powershell
.\.venv\Scripts\python.exe -m backend.cv.evaluate_video_review --protocol docs/fixtures/video_review_evaluation.json --output data/processed/clip_11f23eea/agent_review_evaluation/results.json
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_video_evaluation_full
```

Output phải là file mới. Snapshot/nhãn/protocol đã commit nên có thể tái
tạo JSON đánh giá mà không cần tải video hoặc chạy GPU. Đây là replay đầu
ra lịch sử đã khóa, không tự đánh giá pipeline mới sau khi sửa mã. Muốn
đánh giá bản pipeline khác phải tạo snapshot/protocol mới, giữ bản cũ.

167 test qua, 1 network deselected, cảnh báo Starlette có sẵn. Test ghép
ngược lựa chọn greedy, so tối ưu với vét cạn trên tập điểm nhỏ, nhãn bị che,
ghép không dùng team, không nối ID qua mẫu mất/mơ hồ/gap, fingerprint/nguồn/
pixel/ID trùng và không ghi đè. JSON hữu hạn, tổng các frame khớp summary.

Artifacts cục bộ: `data/processed/clip_11f23eea/agent_review_evaluation/`
gồm results.json và identity_candidates.jpg. Ảnh crop tạo bởi helper QA
cục bộ `.tmp/render_review_cases.py`, không là ảnh trả từ backend API.
Không đổi dữ liệu lớn, packet nhãn, tham số tracking hoặc hợp đồng chung.

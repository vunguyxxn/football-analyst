# Bộ nhãn do agent tự thực hiện

Ngày: 23/10/2026. Người dùng giao agent tự làm toàn bộ phần đánh dấu vì
không thao tác được. Đã xem 20 ảnh gốc và đánh dấu từng ảnh; **đây là nhãn
nháp bằng quan sát của agent, không phải nhãn chuẩn độc lập do người kiểm tra**.

## Mở kết quả đã điền

`D:\projects\football-analyst\data\processed\clip_11f23eea\human_review_v1\agent_review_v1\review.html`

Trang đã có điểm và mã cục bộ, 20/20 ảnh được agent xem. Người dùng không
cần nhập lại. Bấm Ảnh sau để xem; marker đỏ là bị che hoặc không chắc.
Ảnh tĩnh đánh dấu sẵn nằm trong `annotated_frames/`. Banner trên trang và
ảnh ghi rõ nguồn nhãn agent. Không nối mã người giữa ba đoạn không liên tục.

## Dữ liệu và độ chắc chắn

- 411 quan sát người: 195 A (trắng), 196 B (sẫm/đen), 20 trọng tài (xanh nhạt).
- 375 điểm chân nhìn tương đối rõ; 19 bị che, 17 không chắc. Tất cả pixel
  vẫn là ước lượng bằng mắt, không có sai số đo đã kiểm chứng. Danh tính qua
  che khuất/cắt biên có thể nhầm kể cả khi chân đang nhìn thấy.
- 46 quan sát mốc sân: giao đường giữa/biên gần, biên xa và góc xa bên trái
  khi nhìn thấy ở đoạn middle. Không đoán tâm sân hoặc chân người ngoài ảnh.
- Chỉ đánh dấu người trên sân; không đánh dấu HLV/staff đứng ngoài vạch.
  Người đã ra khỏi ảnh hoặc chỉ còn mảnh thân không xác định được chân
  được bỏ ở frame đó, có ghi chú; không bịa thêm vị trí.
- Tọa độ cầu thủ là pixel, pitch_x_m/pitch_y_m null. Mét của landmark dựa
  trên giả định 105 × 68 m, không phải kích thước sân thực đã đo.

Nhãn lưu trong fixture `docs/fixtures/vid1_11f23eea_agent_review.json`, khóa
clean source SHA256 86f6f04ce05ac464269dfa4d831bef0c12c3654acdd2fa3c1b6379f864597b2e.
Không sao chép tọa độ dự đoán hoặc detector làm nhãn tham chiếu. Vì agent
đã tham gia phát triển hệ thống, không gọi đây là kiểm chứng độc lập.

JSON xuất có reviewer agent, author_type=agent, independent_ground_truth=false,
human_reviewed=false ở từng ảnh. reviewed=true chỉ nghĩa agent đã xem ảnh.
Trang giữ nhãn agent khi nạp/xuất lại và dùng vùng lưu nháp riêng cho bản này.
Không sửa nhãn/dữ liệu người dùng thành đã được con người nghiệm thu.

## Đối chiếu sơ bộ số lượng

Chỉ đối chiếu tám ảnh return nơi pipeline đang cho phép xuất tọa độ:

| Frame bản cắt | Nhãn người do agent | Tọa độ raw | Tọa độ v3 |
|---|---:|---:|---:|
| 1105 | 21 | 18 | 17 |
| 1145 | 21 | 18 | 16 |
| 1185 | 21 | 20 | 19 |
| 1225 | 21 | 19 | 18 |
| 1255 | 20 | 20 | 19 |
| 1295 | 20 | 19 | 16 |
| 1325 | 21 | 19 | 18 |
| 1345 | 21 | 20 | 17 |
| Tổng quan sát | 166 | 153 | 140 |

Đây là số quan sát lặp qua frame, không phải số cầu thủ phân biệt. Raw là
tọa độ đã qua chiếu/guard/chỉ trong sân, không phải toàn bộ detection gốc.
Số lượng ít hơn nhãn nháp gợi ý cần rà phần không xuất điểm, nhưng chưa
ghép từng người với prediction nên **không suy precision, recall, ID switches
hoặc tỷ lệ đúng từ bảng này**. Không tính RMSE mét/tốc độ thực từ nhãn pixel
nháp hoặc MOTA/IDF1 từ bộ ảnh thưa không có bbox đầy đủ.

Kết luận vẫn là bước 4 chưa nghiệm thu độ chính xác thực địa. Bộ nháp có
thể dùng rà soát chức năng, minh họa và chọn tình huống lỗi. Phương án dùng
Metrica cho phân tích chiến thuật vẫn giữ trong ROADMAP, không cần coi
nhãn agent hoặc sai số CSV là ground truth video.

## Tái tạo và kiểm tra

Sau khi có packet ảnh gốc theo `VIDEO_HUMAN_REVIEW.md`:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.export_agent_review --packet data/processed/clip_11f23eea/human_review_v1 --output data/processed/clip_11f23eea/human_review_v1/agent_review_v1
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_agent_review_full
```

Output là thư mục con mới, từ chối ghi đè review cũ. JSON/CSV, trang đã điền,
20 ảnh đánh dấu và summary.json nằm trong output. sample_count_comparison.json
là audit số lượng cục bộ bổ sung, chưa tích hợp vào exporter.

158 test qua, 1 network deselected, cảnh báo Starlette có sẵn. Thêm kiểm
tra xuất nhãn đúng nguồn/đúng frame, tọa độ hợp lệ, không ghi đè, giữ packet
ban đầu, nhãn agent không biến thành independent_ground_truth=true qua
import/export UI. Đã xem ảnh đánh dấu đại diện ba đoạn, kiểm tra đủ 457
điểm và đường dẫn ảnh/video. Trình duyệt công cụ vẫn chặn file://; chỉ kiểm
tra logic UI cục bộ, không tuyên bố đã kiểm tra trực tiếp trình duyệt.
Không thay detector/tracker/guard/bộ lọc, dependency hoặc schema/API.

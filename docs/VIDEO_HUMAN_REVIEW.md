# Bộ gán nhãn kiểm tra video thật

Ngày: 23/10/2026. Đã chuẩn bị dữ liệu, **chưa có nhãn người kiểm tra và
chưa có kết quả nghiệm thu độ chính xác video**. Bước 4 vẫn đang kiểm chứng.

Cập nhật: người dùng đã yêu cầu agent tự làm phần đánh dấu. Bản điền sẵn
ở `human_review_v1/agent_review_v1/review.html`; xem `VIDEO_AGENT_REVIEW.md`.
Đó là nhãn nháp do agent tạo, không phải nhãn độc lập của người kiểm tra.
Hướng dẫn nhập tay bên dưới giữ cho trường hợp cần rà soát sau này.

## Mở và làm ngay

Mở file sau bằng Chrome hoặc Edge (có thể mở thư mục bằng File Explorer,
nhấp đúp hoặc kéo file vào trình duyệt):

`D:\projects\football-analyst\data\processed\clip_11f23eea\human_review_v1\review.html`

Trang chạy cục bộ, dùng ảnh cùng thư mục; không cần khởi động backend,
frontend, cài phần mềm hoặc tải ảnh lên dịch vụ nào. Không tách review.html
khỏi thư mục frames. Có thể phóng to trang; tọa độ bấm được đổi về pixel
gốc 1280 × 720.

1. Nhập tên hoặc mã người gán nhãn. **Làm 8 ảnh đoạn `return` trước**;
   trang đã xếp đoạn này ở đầu. Hai đoạn còn lại dùng kiểm tra bổ sung.
2. Đặt mã cho từng người, ví dụ A01/A02, B01/B02, R01. Ở ảnh đầu mỗi đoạn
   có thể đặt từ trái sang phải, sau đó **giữ mã cho cùng người dù đổi chỗ**.
   Mã được hiểu trong từng đoạn; không nối danh tính qua khoảng không thấy
   giữa early/middle/return, không dùng ID dự đoán làm nhãn chuẩn.
3. Chọn đội: A áo trắng, B áo sẫm/đen, referee áo xanh nhạt, unknown nếu
   không chắc. Chỉ đánh dấu người trong sân thi đấu, không đánh dấu HLV,
   dự bị, khán giả hoặc staff ngoài vạch trắng. Trường hợp sát biên không
   rõ thì ghi “không chắc”, thêm ghi chú, không ép thành nhãn chắc chắn.
4. Bấm điểm chân tiếp xúc mặt sân rồi **Thêm điểm**. Không lấy giữa bbox
   hoặc đầu cầu thủ. Nếu chân bị che, đang nhảy hoặc ảnh nhòe, chọn trạng
   thái tương ứng và ghi chú; điểm ước lượng không dùng như điểm thấy rõ
   để tính sai số vị trí. Có thể xem video ngữ cảnh trong thư mục clips
   bằng trình phát video trên máy để kiểm tra danh tính.
5. Chọn loại **Mốc sân**, chọn đúng mốc trong danh sách và bấm vào giao
   điểm/tâm nhìn thấy. Chỉ đánh dấu mốc nhìn rõ; bỏ mốc ngoài ảnh, không
   suy vị trí bằng chính homography của mô hình. Nếu không xác định được
   hướng tọa độ, chưa đánh dấu các góc sân. Gốc (0,0) là góc trái dưới của
   hệ dự án; biên gần y=0, biên xa y=68 trong clip này, đường giữa x=52,5.
6. Kiểm tra hết người trong sân và mốc nhìn thấy rồi đánh dấu ô hoàn tất
   của **từng ảnh**. Khi sửa/xóa/thêm điểm, ảnh trở về chưa kiểm tra.
7. Bấm **Xuất JSON để bàn giao**; xuất thêm CSV nếu muốn xem dạng bảng.
   Đặt file tải được vào thư mục `human_review_v1` với tên
   `annotations_review.json`. JSON là bản bàn giao chính. Có thể xuất
   bản làm dở và nạp lại bằng nút **Nạp bản đã lưu**.

Tự lưu trong trình duyệt chỉ là bản nháp, có thể mất khi đổi trình duyệt
hoặc xóa dữ liệu trình duyệt; luôn xuất JSON. CSV không lưu được trạng thái
của những ảnh không có điểm. Không sửa manifest.json để nhập nhãn.

## Mẫu được chọn

20 ảnh PNG nguyên kích thước, không vẽ khung/ID dự đoán. Không tự điền nhãn
chuẩn từ thuật toán hoặc nhãn agent cũ. Kèm ba clip nguyên cảnh MP4 ở
60 FPS (mp4v; dùng trình phát trên máy nếu trình duyệt không phát codec):

| Đoạn | Frame ảnh bản cắt, đánh số từ 0 | Clip ngữ cảnh | Vai trò |
|---|---|---|---|
| return | 1105, 1145, 1185, 1225, 1255, 1295, 1325, 1345 | [1075,1376), 301 frame / 5,02 s | Ưu tiên; ảnh trong cửa sổ tọa độ tạm hợp lệ |
| early | 140, 170, 200, 230, 260, 290 | [110,321), 211 frame / 3,52 s | Lia máy; chỉ kiểm tra tracking/hình học bổ sung |
| middle | 585, 615, 645, 705, 735, 765 | [555,796), 241 frame / 4,02 s | Lia máy; chỉ kiểm tra tracking/hình học bổ sung |

Không coi early/middle đã có tọa độ mét hợp lệ. Phần ngữ cảnh return có
một ít frame ngoài cửa sổ guard để người xem hiểu diễn biến, không cấp
phép xuất thêm chỉ số ở những frame đó. Các ảnh lấy mẫu không trùng frame
đã dùng trong fixture recalibration/checkpoint hoặc nhãn ID mẫu cũ;
vẫn là cùng clip, không phải kiểm chứng tổng quát sang trận khác.

Nguồn gốc `data/raw/vid1.mp4` khóa SHA256
`11f23eead918e838cb39fdb1ef98179dc93f86574fdb6d38bb6cd8ced3e01ed1`.
Bản cắt `vid1_11f23eea_clean.mp4` khóa SHA256
`86f6f04ce05ac464269dfa4d831bef0c12c3654acdd2fa3c1b6379f864597b2e`.
Frame gốc = frame bản cắt + 600; giây gốc = 10 + frame/60. Không nhầm với
các video cũ từng có cùng tên vid1.mp4. Manifest lưu hash từng ảnh/clip.

## File trong bộ bàn giao

- `review.html`: công cụ bấm điểm, lưu/nạp JSON và xuất CSV, không dùng mạng.
- `frames/`: 20 ảnh PNG nguồn, không có overlay dự đoán.
- `clips/`: ba clip ngữ cảnh gốc để theo dõi người qua các ảnh.
- `manifest.json`: danh sách ảnh, số frame/timestamp gốc và bản cắt, hash,
  thông tin nguồn, trạng thái ban đầu pending_human_annotation; nhãn trống.
- `review_frames.csv`: bảng 20 ảnh và phạm vi đánh giá.
- `annotations_template.csv`: header trống nếu muốn ghi bảng thủ công;
  ưu tiên công cụ bấm điểm để tránh nhầm tọa độ.
- `validation.json`: kết quả kiểm tra file, chưa phải kết quả độ chính xác.

Các trường nhãn nội bộ: clip, clean_frame, kind (player/landmark), entity_id,
team, visibility (visible/occluded/uncertain), image_x_px/image_y_px, note.
Pixel có gốc góc trái trên, x sang phải/y xuống. Cầu thủ chưa có tọa độ mét
chuẩn nên pitch_x_m/pitch_y_m để null; mốc có tọa độ quy ước trên sân giả
định 105 × 68 m. Đây là định dạng QA nội bộ, không đổi DATA_CONTRACT.md.

## Có thể kết luận gì sau khi gán nhãn

Trước hết rà soát độ nhất quán danh tính, người bị bỏ sót, người ngoài sân
và sai lệch điểm chân trong ảnh. Để báo sai số theo mét phải kiểm chứng
hình học bằng mốc độc lập. Không chiếu cả nhãn và dự đoán qua cùng một
homography chưa kiểm chứng rồi gọi đó là ground truth thực địa.

Các mốc nhìn thấy có thể ít hoặc thẳng hàng; không mặc định đủ để khởi tạo
một homography mới. Kích thước sân 105 × 68 m vẫn là giả định đã chốt.
Không suy tốc độ chuẩn chỉ từ vài điểm chân gán nhãn thưa và noisy. Bộ này
không phải MOT ground truth đầy đủ mọi frame/bbox; chưa tính MOTA/IDF1 hoặc
tổng distance/tốc độ cả trận. Nhãn mơ hồ phải tách khỏi nhãn chắc chắn.

Sau khi có JSON do người kiểm tra tạo, mới đối chiếu dự đoán đã khóa và
quyết định chỉ số nào đủ tin cậy. Không dùng nhãn này chỉnh mô hình rồi
báo nó như tập đánh giá độc lập chưa từng xem.

## Tái tạo và kiểm tra kỹ thuật

```powershell
.\.venv\Scripts\python.exe -m backend.cv.prepare_video_review --plan docs/fixtures/video_review_plan.json --output data/processed/clip_11f23eea/human_review_v1
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_video_review_full
```

Lệnh chỉ nhận đường dẫn trong repo, khóa nguồn bằng hash, kiểm tra metadata
và offset. Thư mục output phải chưa tồn tại; chạy lại chọn tên khác để
không ghi đè nhãn người. Video giải mã tuần tự, giữ một frame đầy đủ trong
RAM và ghi clip theo từng frame, không nạp cả video. Không chạy lại detector
hoặc sửa mã tracking/nhãn đội/guard/bộ lọc.

154 test qua, 1 network deselected, cảnh báo Starlette có sẵn. Test thêm:
ảnh PNG khớp chính xác pixel source, số frame clip/cadence, nhãn trống,
hash/đổi nguồn/offset/path và không ghi đè. Test JavaScript cục bộ với DOM
mô phỏng kiểm tra đổi tọa độ khi ảnh co giãn, thêm/chống trùng, mốc sân,
review state, xuất CSV/JSON, nạp sai bộ ảnh/pixel và lưu nháp. Không tải
file qua trình duyệt hoặc tạo nhãn thật trong kiểm thử.

Đã kiểm tra trực tiếp ảnh đại diện ba đoạn, giải mã lại đủ 211/241/301 frame
clip, hash/kích thước toàn bộ 20 ảnh. Trình duyệt kiểm thử của agent chặn
protocol file://, nên **chưa kiểm tra trực tiếp bố cục/thao tác trong trình
duyệt thực**; không đi vòng qua hạn chế này. Test logic cục bộ đã qua.
Ảnh/video/nhãn thật nằm data/processed và không commit; generator, template,
plan và test được commit để tái tạo.

# Phân tích video mới từ giao diện

Ngày 27/10/2026. Luồng mới tại `/video`: chọn video → **Phân tích video**
→ gửi tới FastAPI cục bộ → YOLO + ByteTrack → phát video với khung/ID.
Không cần chạy lệnh xử lý cho từng clip. Backend và frontend vẫn phải
được khởi động theo `AGENTS.md`.

## Cách dùng và phạm vi

1. Chọn MP4 H.264 hoặc video mà trình duyệt phát được.
2. Bấm **Phân tích video**. Giữ trang mở trong lúc gửi file.
3. Chờ trạng thái **Đã phân tích xong** rồi phát hoặc tua video.
4. Chọn video khác để phân tích lại. Đổi video xóa kết quả đang xem,
   tránh vẽ khung của clip cũ lên clip mới.

Giới hạn đầu vào: 500 MB, 10 phút, tối đa 4K/120 FPS. Nhịp frame phải
đều để đồng bộ; dừng và báo lỗi nếu timestamp lệch nhịp, video giải mã
thiếu frame hoặc thay đổi kích thước. File không phát được trong trình
duyệt cần xuất lại H.264 trước khi phân tích.

Một tác vụ tại một thời điểm, có tiến độ và nút hủy. GPU CUDA được ưu
tiên, CPU dự phòng chậm hơn. GPU dùng trọng số gốc `data/raw/yolo11n.pt`,
imgsz 1280/conf 0,1; CPU dùng imgsz 640/conf 0,1. Không tải trọng số hay
cài thư viện mới. Vẫn giữ trọng số gốc theo quyết định so sánh bước 5b.

K-means hai cụm trên tối đa 300 đặc trưng thân áo từ tối đa 12 frame.
Cụm tối hơn mang nhãn A, cụm sáng hơn B; màu không rõ là unknown, có
voting theo ID. Đây là nhóm màu ước lượng, không xác nhận tên đội hoặc
phân biệt trọng tài/thủ môn; không dùng nhãn clip cũ để gán clip mới.

Khung được vẽ bằng SVG trên video gốc; API chỉ trả JSON. ID không phải
số áo hay số cầu thủ duy nhất; có thể đổi khi che khuất/chuyển cảnh.
Overlay thuộc trang web, không được nhúng vào file MP4; trình phát toàn
màn hình/Picture-in-Picture riêng của trình duyệt có thể không gồm SVG.

Chưa tự hiệu chỉnh sân: chưa bảo đảm lọc người ngoài biên, chưa tính
tọa độ mét, tốc độ, quãng đường hoặc heatmap từ clip mới. Sân mini cần
TrackingRow đã hiệu chỉnh riêng; không giả tọa độ từ pixel. Hồ sơ
StatsBomb/Metrica và báo cáo xG mẫu không phải kết quả suy ra từ clip
vừa tải. Nhận diện sự kiện từ video vẫn ngoài phạm vi.

## API cục bộ mới

Không đổi `TrackingRow`, `AnalysisResult` hoặc `docs/DATA_CONTRACT.md`.
API tác vụ này là giao thức riêng cho upload và **khung ảnh pixel**:

| Yêu cầu | Kết quả |
|---|---|
| `POST /api/video-jobs?extension=mp4` | Body binary của file, không multipart; HTTP 202 với `id`, `status`, `progress`, `stage` |
| `GET /api/video-jobs` | Danh sách tác vụ đang chạy để khôi phục theo dõi/hủy khi quay lại trang |
| `GET /api/video-jobs/{id}` | queued/running/completed/failed/cancelled; khi hoàn tất có `result` |
| `POST /api/video-jobs/{id}/cancel` | Yêu cầu hủy; chờ worker dừng giữa các frame |
| `GET /api/video-jobs/{id}/chunks/{index}` | JSON kết quả đoạn, chỉ đọc khi tác vụ completed |

`result` gồm fps, frames, width/height, duration_s, chunk_frames, chunks,
device, image_size/confidence, track_ids, observations, group_observations,
color_groups_available và limitations. Count ID không phải count người.

Mỗi đoạn có `frames[]`; mỗi frame có `frame` (0-based), `time_s`,
`boxes[]`. Mỗi box có `id`, `group` (A/B/unknown), `xyxy` theo pixel của
ảnh nguồn, gốc trái trên. Các trường này không được đưa vào schema tọa
độ sân. Frontend chọn frame theo nhịp FPS đã kiểm, không nội suy và
không giữ khung từ đoạn khác khi tải/seek.

Worker đọc từng frame, ghi JSON đoạn khoảng 10 giây. Frontend giữ một
đoạn kết quả; việc tua tải đoạn tương ứng và thử lại nếu mất kết nối.
Không giữ toàn bộ frame ảnh/video trong RAM, không tạo MP4 MP4V để phát
trên web. Video gốc dùng object URL của file người dùng đã chọn.

Dữ liệu lưu tại `data/processed/video_jobs/{uuid}/`, được Git ignore.
Tên file đầu vào không được dùng làm đường dẫn. File lỗi khi nhận upload
được dọn; video/kết quả tác vụ đã nhận được giữ cục bộ để kiểm tra,
chưa có chức năng xóa/lưu trữ tự động. Máy chủ khởi động lại sẽ đánh dấu
tác vụ còn dang dở là failed; không báo giả hoàn tất.

Khi quay lại trang có thể theo dõi/hủy tác vụ còn chạy, nhưng file video
đã chọn và kết quả xem không được giữ qua reload/đổi trang. Sau khi tác
vụ cũ kết thúc, chọn video và phân tích lại để mở phiên xem mới. Chưa có
thư viện quản lý kết quả cũ trên giao diện.

## Kiểm chứng

- Test API: upload, giới hạn dung lượng/định dạng, video hỏng, busy,
  cancel, failure, restart, danh sách active và biên chỉ số đoạn.
- Test màu: không gán khi đặc trưng thiếu/mơ hồ hoặc xa cụm.
- Bộ kiểm thử dự án: 286 test Python qua, 1 network deselected;
  12 test frontend qua. Build/lint exit 0, chỉ cảnh báo bundle/Fast
  Refresh đã có từ trước.
- Nghiệm thu trình duyệt bằng `data/raw/Video Project 12.mp4`, thực sự
  gửi binary từ nút trên trang, xử lý GPU và đọc JSON để vẽ khung.
  Số liệu chi tiết phiên nghiệm thu được ghi tại `PROGRESS.md`.

Đây là nghiệm thu tích hợp, không phải đánh giá accuracy detection,
tracking, phân đội hoặc độ chính xác vật lý của tọa độ.

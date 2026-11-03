# Nguồn train mới và clip kiểm chứng giữ riêng v8

Đã bổ sung 3 clip thật, mỗi clip 30 giây, 1280×720, 25 fps/750 frame.
Đây là footage đại học với camera ảo cắt, lia và zoom từ panorama;
không phải hoạt cảnh CG, cũng không phải camera truyền hình gốc.
Nguồn mới giúp kiểm tra miền hình ảnh khác nhưng chưa thay thế bộ
kiểm chứng broadcast hoặc việc mở rộng đủ đa dạng cho train.

## Nguồn, giấy phép và tách match

Nguồn tải công khai:
[SoccerTrack v2 follow-cam event clips](https://huggingface.co/datasets/algo-dev99/soccertrack-v2-followcam-events/tree/5ca71d867ee073335abb24b771e0604ff22d1b88),
revision `5ca71d867ee073335abb24b771e0604ff22d1b88`, công bố CC BY 4.0.
Ghi công tác giả bộ clip algo-dev99 và nguồn SoccerTrack v2 của Scott,
Uchida, Kuroda, Kim, Fujii. Nguồn gốc công bố giấy phép dataset tại
[LICENSE-DATA](https://github.com/AtomScott/SoccerTrack-v2/blob/a752d294df2a0e816e827b70f284980698f5a50e/LICENSE-DATA).
README giấy phép và inventory khóa revision được lưu cục bộ.

Đã khảo sát SoccerTrack gốc nhưng file yêu cầu quyền truy cập; không
tải dữ liệu gated. Các clip nhận ở đây là bản dẫn xuất được phân phối
công khai tại repository trên. Không dùng video demo đã vẽ tracking
hoặc nhãn machine-made đi kèm làm ground truth. Không chạy code nguồn
bên ngoài hay thêm thư viện.

Split được khóa **trước suy luận role v6/v7**:

| Match ID | Clip | Phạm vi dùng |
|---|---|---|
| 117093 | st117093_h1_c000.mp4 | Ứng viên train |
| 118575 | st118575_h1_c000.mp4 | Ứng viên train |
| 128057 | st128057_h1_c000.mp4 | Giữ riêng để kiểm chứng |

Chọn c000 hiệp1 theo quy tắc, không chọn dựa điểm model. Toàn match
128057, gồm clip/hiệp khác, bị loại khỏi train dự án. Tên match theo
nguồn, chưa xác minh riêng danh tính/ngày từng trận. Không tuyên bố
chưa từng xuất hiện trong mọi tập pretrain bên ngoài; chỉ kiểm soát
việc dùng trong dự án. Dữ liệu v6/v7 cũ không đổi.

## Nhãn đã rà và phạm vi ảnh

Rút mốc 5/15/25 giây mỗi clip. Đề xuất bbox bằng YOLO11n COCO chỉ
lớp person, agent xem toàn cảnh, crop và overlay, gán lại vai trò và
loại đề xuất trùng/nhân viên/bóng/bóng đổ. Không dùng role detector
v6/v7 để gán nhãn heldout. Chưa có người kiểm độc lập.

Nhận 6 vùng ảnh:

| Phần | Số vùng | Player | Keeper | Referee |
|---|---:|---:|---:|---:|
| Train candidate | 4 | 30 | 2 | 2 |
| Heldout review | 2 | 16 | 1 | 2 |

Hai vùng train là toàn frame, hai vùng còn lại có ROI lớn để bỏ dải
mép chưa rõ:117093-f625 y205–720;118575-f125 y50–720. Giữ chiều ngang
1280, không phóng crop thành người lớn. Các đối tượng giao mép ROI
được cắt bbox theo vùng đã rà. Không gọi cả6vùng là full-frame gốc;
pixel ngoài ROI chưa gán nhãn, không được dùng làm nền âm tính.
Các ảnh mẫu giữ người nhỏ, người cắt mép và người chồng nhau khi
đủ rõ; nhân viên/dự bị ngoài cuộc chơi không thành lớp player.

Quarantine3mốc:117093-f375,118575-f625,128057-f125 vì còn đề xuất
trùng/chồng hoặc người xa chưa xác nhận; không xuất nhãn cả frame.
53nhãn là lượt quan sát, không53người hoặc6trận độc lập.

Exporter kiểm SHA256 video theo LFS nguồn, decode frame và hash PNG
khớp packet trước khi crop. Sàng lọc ảnh mới với465ảnh/đơn vị pixel
khác nhau trong corpus v6 bằng dHash+thumbnail, không có near-image
hit theo phép kiểm. Đây không phải chứng minh danh tính trận độc lập.
Đã xem cả6overlay xuất cuối cùng. Source clip giữ nguyên, không ghi
đè weights, ảnh/nhãn hoặc bộ kiểm cũ.

## Kiểm chứng mới, sau khi khóa nhãn

Đã đóng băng manifest trước khi chạy v6/v7, hai kích thước640/1280,
conf0,25/NMS0,7/matching0,5, không lọc khung trùng role.

| Model | Size | Player đúng /16 | Keeper đúng /1 | Referee đúng /2 |
|---|---|---:|---:|---:|
| v6 |640|15|0|0|
| v6 |1280|14|0|0|
| v7 fixed |640|15|0|0|
| v7 fixed |1280|14|0|0|
| v7 multi |640|15|1|0|
| v7 multi |1280|12|0|0|

Đây chỉ là2keyframe của1match mới, không phải độ chính xác cả750frame,
tracking/IDF1 hay đánh giá độc lập bởi người gán nhãn khác. Bbox có
COCO hỗ trợ nên vẫn có thiên lệch đề xuất. Không dùng kết quả này để
chọn model/size hoặc sửa ngưỡng; không đưa match đã kiểm chứng vào
train sau khi xem điểm. Giữ các ca ref/keeper thất bại làm căn cứ
đánh giá mở rộng; chưa đủ số mẫu để ước lượng khả năng tổng quát hóa.

## Artifact và nghiệm thu

Clip cục bộ dưới `data/raw/role_sources_v8/`:

- `st117093_h1_c000.mp4`: SHA256
  `6b09f6160cc65768da35cf74dda0241ca6baccc1e4771b8304b80921d169da95`.
- `st118575_h1_c000.mp4`: SHA256
  `9cb3e68d0cbb16cad2195da5c0a021ea8b51f3b646e7634f5eb0b5eb7da158fe`.
- `st128057_h1_c000.mp4`: SHA256
  `0e05b39e41c6c8e13c1e320ac6f2c51c41e0759730a9fe59b62c7f643d508738`.

Packet và split khóa trongdocs/fixtures/role_source_split_v8.json,
role_sources_review_v8.json; manifest/snapshot role_source_release_v8,
role_sources_diagnostic_v8.json. Video, ảnh và overlay không commit.
Export train/heldout tách thư mục dưới
`data/processed/role_source_release_v8`, chưa ghép vào lịch train.
Manifest release ghi trạng thái trước suy luận; snapshot diagnostic
ghi kết quả sau suy luận, không sửa lại manifest đã khóa.

```powershell
.\.venv\Scripts\python.exe -m backend.cv.release_role_sources
.\.venv\Scripts\python.exe -m backend.cv.evaluate_role_sources
.\.venv\Scripts\python.exe -m pytest tests/test_role_source_release.py tests/test_role_counterexamples.py -q --basetemp .tmp/pytest_role_sources_v8
```

20test đích đạt. Lệnh từ chối ghi đè thư mục release/diagnostic đã có.
Toàn bộ558test Python đạt,1networkdeselected,4warningcũ.
Guard tách toànmatch chặn đổi clip/hiệp để chuyển heldout vào train.
Không đổi API/DATA_CONTRACT,model runtime,frontend/dependency; chưa
train thêm hoặc nhập nguồn chưa rà vào dataset.

## Bước tiếp theo

Mở rộng nhãn train từ hai match ứng viên, ưu tiên thêm keyframe nhìn
rõ keeper và ref áo tối; đồng thời gán thêm mốc trên match128057 để
bộ kiểm có đủ mẫu/che khuất/kích thước. Giữ split match hiện tại,
không tăng epoch trước khi nguồn mới đủ nhãn. Cần thêm broadcast thật
từ match khác để kiểm chứng camera lia thật ngoài miền camera ảo này.

# Kiểm tra thêm ba đoạn camera lia — 22/10/2026

## Kết luận

Giữ sân mặc định **105 × 68 m** theo quyết định người dùng. Bù camera chạy
được trên ba đoạn, cơ chế ngừng tọa độ hoạt động khi hết chuỗi hoặc khi
chèn ảnh lỗi. Tuy nhiên sai số mốc chưa ổn định: có điểm sai **3,28 m** dù
trạng thái vẫn là `tracked`. Chưa đủ điều kiện chạy toàn clip để báo cáo
tốc độ/quãng đường chính xác; chưa chuyển bước 5.

Không chỉnh thuật toán, ngưỡng hoặc các mốc hiệu chỉnh sau khi xem kết quả.
Các kết quả/bộ hiệu chỉnh trước vẫn được giữ nguyên.

## Thiết lập và nguồn

- Nguồn: bản cắt `vid1_11f23eea_clean.mp4`, SHA256
  `86f6f04ce05ac464269dfa4d831bef0c12c3654acdd2fa3c1b6379f864597b2e`,
  1800 frame, 1280 × 720/60 FPS; bản cắt bắt đầu ở giây 10 video gốc.
- Ba mốc hiệu chỉnh tay tại frame 0, 450, 1050. Mỗi mốc có 4 cặp chính và
  2 mốc phụ vòng tròn giữa sân, fit theo cơ chế bước 4 đã có. Mốc được
  agent chọn qua quan sát ảnh; chưa có rà soát nhãn độc lập.
- Khóa cấu hình trước khi xem/gán nhãn các frame đánh giá 75, 225, 525,
  710, 1125, 1275. Không dùng điểm ở frame đánh giá để fit. Đoạn giữa có
  phần thời gian chồng với khảo sát cũ; đây là các đoạn cùng clip, không
  phải ba trận hoặc ba video độc lập.
- Chạy lại YOLO11n thật trên CUDA, image size 1280, confidence 0,1, chỉ
  person; dùng mọi bbox person để loại vùng người trước CameraMotion.
  Mỗi frame được đọc riêng, không nạp toàn bộ video vào RAM.
- Chỉ đánh giá camera và phép chiếu mốc. Không chạy ByteTrack/phân đội/
  thống kê cầu thủ trong lượt này. Số detection chiếu được là lượt quan sát,
  không phải số cầu thủ hoặc track ID. Không công bố throughput GPU mới.
- Các đoạn có lia hai hướng và thay đổi độ phóng biểu kiến. Chưa có đánh
  giá zoom mạnh hoặc cắt cảnh tự nhiên trong ba đoạn này. Không suy rộng
  thành đã xử lý mọi chuyển động camera truyền hình.

Fixture: `docs/fixtures/vid1_11f23eea_homography_segments.json`, có hash,
mốc hiệu chỉnh, phạm vi và nhãn kiểm tra. Hệ tọa độ/TrackingRow/API giữ nguyên.

## Phạm vi và khả năng duy trì phép chiếu

`end_frame` trong fixture không bao gồm; bảng dưới ghi đầu/cuối có bao gồm.

| Đoạn | Frame bản cắt | Giây video gốc | Kết quả camera | Video đọc lại |
|---|---|---|---|---:|
| Đầu, đổi hướng lia | 0–302 | 10,00–15,03 | 1 mốc tay + 300 tracked + 2 lost do hết chuỗi | 303 |
| Lia trái | 450–750 | 17,50–22,50 | 1 mốc tay + 300 tracked | 301 |
| Lia trở lại | 1050–1350 | 27,50–32,50 | 1 mốc tay + 300 tracked | 301 |

Tổng đọc lại **905 frame** diagnostic. Ở đoạn đầu, frame 301 trả
`reanchor_interval_exceeded`, frame 302 yêu cầu mốc tay mới; cả hai có
ma trận null và **không có detection nào được xuất tọa độ**, dù detector
vẫn phát hiện người. Đến frame 450, mốc tay mới phục hồi phép chiếu.
Không có thất bại tự nhiên do ngưỡng chất lượng trong 900 bước trước đó.

## Sai số vị trí trên frame kiểm tra

Mỗi đoạn có 8 điểm theo thời gian: hai giao đường giữa sân với vòng tròn
và hai biên tại hai frame kiểm tra. Đây là cùng loại mốc đã dùng hiệu chỉnh,
được quan sát ở frame khác; không gọi là điểm hình học độc lập hoàn toàn.
Sai số là khoảng cách Euclid theo hệ sân 105 × 68 m dựa trên nhãn ảnh bằng
mắt, không phải ground truth đo đạc.

| Đoạn | Số điểm | Sai số trung bình | Lớn nhất |
|---|---:|---:|---:|
| Đầu, đổi hướng lia | 8 | 0,64 m | 2,91 m |
| Lia trái | 8 | 1,36 m | 3,28 m |
| Lia trở lại | 8 | 0,50 m | 1,79 m |

Ba kiểm tra hình học bổ sung ở đoạn lia trái: góc sân xa tại frame 525/710
và giao cung vùng cấm phía gần tại frame 525, không dùng fit đoạn đó.
Sai số trung bình **0,91 m**, lớn nhất **1,07 m**. Hai đoạn còn lại không có
thêm nhãn hình học đủ rõ ngoài các mốc theo thời gian; không bịa điểm khuất.

Lỗi mốc biên xa chi phối một số mẫu lớn. Hệ thống có thể báo `tracked` với
vòng tròn nhìn gần khớp mà tọa độ biên vẫn lệch nhiều. Các ngưỡng RANSAC hiện
tại chỉ kiểm tra tính nhất quán chuyển động giữa hai frame; không phát hiện
được mọi lỗi hiệu chỉnh ban đầu hoặc trôi tọa độ tuyệt đối. Việc đạt 300
bước tracked không phải nghiệm thu độ chính xác theo mét.

## Kiểm tra ngừng tọa độ khi mất hiệu chỉnh

Ngoài hết chuỗi trên video thật, thực hiện phép thử có chủ đích:

1. Khởi tạo bằng ảnh thật frame 450 và mốc hiệu chỉnh của đoạn.
2. Chèn một ảnh đen trong bộ nhớ vào lượt cập nhật 451 (không sửa video gốc).
3. Kết quả `lost / insufficient_ground_features`, phép chiếu trả None.
4. Trả lại ảnh sân, không cung cấp mốc mới: vẫn `lost / manual_anchor_required`.
5. Cấp mốc tay frame 1050: `manual_anchor`, phép chiếu trở lại hoạt động.

Đây là stress test ảnh lỗi được tạo có chủ đích, **không phải** phát hiện
cắt cảnh tự nhiên đã được đo precision/recall. Nó kiểm chứng khóa trạng
thái mất dấu và không phát tọa độ bằng ma trận cũ.

## Artifact và tái chạy

Kết quả cục bộ:

```text
data/processed/clip_11f23eea/homography_multi_check/
  calibration_frozen.json
  camera_quality.jsonl       # status, ma trận và bbox từng frame
  summary.json
  evaluation.json            # sai số từng mốc + stress test
  early_pan.mp4
  left_pan.mp4
  return_pan.mp4
  check_{75,225,525,710,1125,1275}.jpg
```

Media và dữ liệu sinh ra không commit. Helper khảo sát hiện tại ở
`.tmp/check_multiple_segments.py` và `.tmp/evaluate_multiple_segments.py`,
không phải CLI được đóng gói cho fresh checkout. Bộ fixture và tham số
ở trên cho phép chạy chế độ sản phẩm hiện có với đầu ra mới:

```powershell
$env:YOLO_CONFIG_DIR = "$PWD\data\processed"
$env:MPLCONFIGDIR = "$PWD\.tmp\matplotlib"
.\.venv\Scripts\python.exe -m backend.cv.track_video data/processed/clip_11f23eea/vid1_11f23eea_clean.mp4 data/processed/clip_11f23eea/multi_pitch_full.mp4 --weights data/raw/yolo11n.pt --device 0 --image-size 1280 --calibration docs/fixtures/vid1_11f23eea_homography_segments.json --pitch-output data/processed/clip_11f23eea/multi_pitch_full --compensate-camera
```

Lệnh này sẽ đọc toàn clip, chỉ chiếu ba phạm vi của fixture; không tự hiệu
chỉnh các khoảng trống. Lượt khảo sát chỉ chạy 905 frame ở ba đoạn; chưa
chạy CLI toàn clip hoặc tính chỉ số cầu thủ. Không đổi ngưỡng để tránh lost
hay làm đẹp tỷ lệ xuất tọa độ.

Kiểm tra bổ sung: fixture khớp hash/kích thước/phạm vi, stress assertions,
giải mã đủ ba video và toàn bộ 73 test qua (1 network test deselected,
cảnh báo Starlette TestClient cũ).

## Việc tiếp theo

Cần kiểm tra sai số mốc sân theo thời gian và cơ chế hiệu chỉnh lại để
phát hiện/giảm lỗi tuyệt đối mà optical flow vẫn cho qua. Nếu chỉnh tiếp,
coi các nhãn hiện tại là dữ liệu phát triển và giữ bộ kiểm tra mới. Sau khi
chất lượng tọa độ ổn định mới đánh giá vị trí chân/ID và chuyển sang chỉ số
cầu thủ. Giữ sân mặc định 105 × 68 m, không yêu cầu tìm sân khác hoặc camera
cố định để tiếp tục công việc.

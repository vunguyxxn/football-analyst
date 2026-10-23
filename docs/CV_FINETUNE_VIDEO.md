# Đối chiếu YOLO11n trước/sau fine-tune trên video

Ngày 23/10/2026. Tiếp nối bước 5b, chạy lại hai bộ trọng số trên cùng video
clean 30 giây, 1.800 frame, 1280×720/60 FPS. Đây là chẩn đoán ngoại tuyến
trên clip phát triển đã dùng trước đây, không phải tập test video độc lập.

## Cấu hình và phạm vi

- Nguồn: `data/processed/clip_11f23eea/vid1_11f23eea_clean.mp4`, SHA256
  `86f6f04ce05ac464269dfa4d831bef0c12c3654acdd2fa3c1b6379f864597b2e`.
- Baseline: `data/raw/yolo11n.pt`. Ứng viên: `best.pt` của lượt fine-tune
  15 epoch; nguồn/giấy phép/phương pháp ở `CV_FINETUNE_YOLO.md`.
- Cả hai chạy CUDA, ảnh suy luận 1280, confidence 0,1, chunk 10 giây,
  lọc person, NMS trùng người 0,5, ByteTrack mặc định, cùng mẫu phân đội,
  bộ ổn định vai trò, hiệu chỉnh đoạn return và landmark guard.
- Bật `on_pitch_only`: người ngoài sân không được đưa vào tracker/phân đội.
  Khi hiệu chỉnh chưa hợp lệ thì không đóng khung. Đoạn return hiệu chỉnh
  ở frame 1050–1350; trước kiểm tra đầu tiên 1080 chưa xuất người.
- Không bật bộ lọc tọa độ: đối chiếu điểm chân giữa đáy bbox sau ByteTrack.
  Không so sai số mét, tốc độ hoặc thay thuật toán tracking.

Protocol `docs/fixtures/yolo_person_video_protocol_v1.json` khóa hash video,
hai trọng số, nhãn, hiệu chỉnh, checkpoint, mẫu áo và mã pipeline liên quan
trước khi chạy. Hai fixture hiệu chỉnh/checkpoint là bản sao nguyên byte
của return_calibration/return_checks đã dùng ở bước trước. Mỗi mô hình
được nạp mới, tracker mới và chạy tuần tự toàn clip để giữ lịch sử warm-up.

Runner gọi nguyên hàm `track_video`, bọc ByteTrack bằng lớp chỉ ghi lại đầu
ra và trả đúng đối tượng gốc. Có test xác nhận không sửa input/output,
tham số khởi tạo hoặc bỏ frame rỗng. Không sửa mã pipeline sản phẩm.
Camera motion loại vùng người dựa vào bbox của từng detector: hai lượt
có thể có ma trận/guard khác nhau dù cấu hình giống nhau. Vì vậy đây là
so sánh hai lượt pipeline, không cô lập riêng tác động detector.

## Phép đối chiếu

Dùng lại tám ảnh 1105/1145/1185/1225/1255/1295/1325/1345, nhãn nháp agent
và cách ghép từ `VIDEO_REVIEW_EVALUATION.md`. Có 154 quan sát visible,
12 occluded/uncertain loại khỏi ghép chính. Ghép một-một tối đa số cặp,
sau đó tối thiểu tổng khoảng cách pixel; không dùng ID/đội để chọn cặp.
Gate chính 12 px, kiểm tra độ nhạy 8/20 px, khoảng ảnh tối đa 90 frame.

Số đổi ID biểu kiến chỉ dùng nhãn ghép không mơ hồ ở hai ảnh mẫu liên tiếp.
So sánh bổ sung trên cùng khoảng nhãn đủ điều kiện ở cả hai mô hình;
không so giá trị số ID giữa các mô hình. Sai lệch pixel cũng có bản so
trên cùng frame/nhãn không mơ hồ, không yêu cầu ID số của hai mô hình bằng
nhau. Các trường hợp không ghép được vẫn thống kê riêng.

Nhãn được ước lượng bằng mắt, mã người qua che khuất còn tentative. Không
đọc tỷ lệ ghép là detector recall, số đổi ID thưa là MOT ID switches,
hoặc số ID ít hơn là tracking tốt hơn. Chưa có MOTA/IDF1/ground truth
video độc lập. Trọng số mặc định chưa thay đổi.

## Kết quả và quyết định

Cả hai lượt đủ 1.800 frame. Guard cùng trạng thái: 1.499 uncalibrated,
30 awaiting_landmark_check, 271 tracked. Cùng 270 frame có người sau
warm-up; tám frame đánh giá đều tracked. Tổng quan sát frame/người tăng
5.215 → 7.106, không đồng nghĩa có nhiều người thật hơn. Baseline tái hiện
các tổng và chẩn đoán cũ ở `VIDEO_REVIEW_EVALUATION.md`.

Gate chính 12 px:

| Mục | Baseline | Fine-tuned |
| --- | ---: | ---: |
| Quan sát nhãn visible / loại | 154 / 12 | 154 / 12 |
| Quan sát dự đoán tại tám ảnh | 153 | 217 |
| Ghép với nhãn visible | 146 | 150 |
| Nhãn visible chưa ghép | 8 | 4 |
| Ghép không mơ hồ | 143 | 130 |
| Dự đoán chưa ghép, gần nhãn bị loại | 5 | 12 |
| Dự đoán chưa ghép khác, cần rà | 2 | 55 |
| Khoảng mẫu có thể so ID riêng mỗi bản | 116 | 95 |
| Đổi ID biểu kiến trên các khoảng riêng | 2 | 6 |

Không gọi toàn bộ 55 dự đoán chưa ghép là false positive: có thể do nhãn
thiếu, lệch điểm chân, khung bộ phận hoặc khung trùng. Montage cho thấy
khung chồng cùng cầu thủ gần máy: fine-tuned có unknown ID40/42 ở frame
1105, unknown ID69/42 ở 1185 và A ID154/187 ở 1345. NMS IoU 0,5 hiện tại
chưa loại hết khung có kích thước khác nhau. Không chỉnh threshold sau khi
xem kết quả trong lượt này.

Trên **87 khoảng cùng nhãn đủ điều kiện ở cả hai bản**, baseline có một
đổi ID biểu kiến, fine-tuned có sáu. Trường hợp A02 của baseline bị loại
khỏi tập chung do bản fine-tuned ghép mơ hồ; số một không thay số hai
trên tập riêng. Trên 124 cặp cùng frame/nhãn không mơ hồ, RMSE pixel
2,820 → 2,738; chênh lệch nhỏ so với độ không chắc của nhãn ước lượng.

Độ nhạy cho thấy kết luận không chỉ phụ thuộc gate chính:

| Gate | Ghép baseline / fine-tuned | Khoảng ID chung | Đổi ID trên khoảng chung baseline / fine-tuned |
| --- | --- | ---: | --- |
| 8 px | 145 / 149 | 95 | 2 / 7 |
| 12 px | 146 / 150 | 87 | 1 / 6 |
| 20 px | 146 / 151 | 71 | 0 / 3 |

Tăng gate làm nhiều cặp mơ hồ và giảm số khoảng ID đủ điều kiện; không
diễn giải số đổi ID nhỏ hơn giữa các gate là thuật toán cải thiện.

**Giữ YOLO11n gốc làm mặc định.** Mô hình fine-tuned cải thiện mAP trên
bộ ảnh test ở bước 5b nhưng chưa đủ căn cứ áp dụng vào pipeline video
1280/conf 0,1 hiện tại. Muốn triển khai cần một lượt hiệu chỉnh riêng
trên dữ liệu phát triển rồi khóa cấu hình để đánh giá video khác có nhãn;
không chọn ngưỡng bằng chính tám ảnh này và coi đó là test độc lập.
Không thay pipeline, trọng số gốc, bộ lọc sân hoặc tuyên bố chất lượng
chiến thuật. Hoàn tất so sánh; phần tiếp theo theo ROADMAP là bước 6 xG.

## Lệnh và artifact

```powershell
.\.venv\Scripts\python.exe -m backend.cv.compare_person_video --output data/processed/yolo_person_video_comparison_repro
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_person_video_full_v1
```

Output phải mới; cần giữ các input cục bộ với đúng hash protocol. Hai
lượt `baseline/`, `finetuned/` có `tracked.mp4`, `tracker.jsonl` từng frame,
`pitch/` chứa tracking/camera/metrics, và `result.json`. Kết quả chung ở
`comparison.json`, montage ba thời điểm ở `comparison.jpg`. Video im lặng,
giữ nguyên 60 FPS; ảnh và video không đưa vào Git. Lượt đã chạy nằm ở
`data/processed/yolo_person_video_comparison_v1/`. Snapshot các tổng và
chẩn đoán chung ở `docs/fixtures/yolo_person_video_result_v1.json`, khóa
hash báo cáo cục bộ. Toàn bộ test: **264 passed, 1 network deselected**;
cảnh báo Starlette cũ. Ba test mới cho recorder, thống kê frame rỗng và
đối chiếu khoảng ID chung.

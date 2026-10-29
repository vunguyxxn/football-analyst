# Phân tích bóng đá trực tiếp từ video — mở rộng 27/10/2026

Cập nhật29/10: đã đối chiếu chuỗi theo lịch mẫu và đo bỏ sót sự kiện,
không chỉ đếm frame có bóng. Kết quả20/24 điểm,1/4 chuyền trên mẫu agent;
thử crop quanh chân không cải thiện. Đã tìm một pha sút ở nguồn15(1)
để rà tiếp, chưa có mô hình sút. Xem BALL_SEQUENCE_VALIDATION.md.

Người dùng xác nhận nghiên cứu tự nhận diện chuyền bóng và cú sút chỉ từ
video, bao gồm theo dõi bóng và kiểm chứng riêng. Đây là thay đổi so với
phạm vi cũ, đã ghi ở `ROADMAP.md`. Chưa thể gọi luồng phát hiện người,
đếm ID hoặc thống kê frame là hoàn tất yêu cầu này.

## Sản phẩm cần đạt và dữ liệu bắt buộc

| Kết quả cho HLV | Điều kiện trước khi đưa số liệu |
|---|---|
| Heatmap theo đội/cầu thủ | Vị trí sân 105×68 đã hiệu chỉnh, nhãn đội/ID đủ tin cậy, ghi rõ đoạn có dữ liệu |
| Quãng đường, tốc độ | Quỹ đạo mét liên tục, bù camera, không nối qua mất dấu/chuyển cảnh, loại bước bất hợp lý |
| Chuyền bóng | Theo dõi bóng, liên kết người chạm bóng, xác định người gửi/nhận và kết quả, kiểm chứng trên sự kiện gán nhãn |
| Cú sút/xG | Phân biệt sút với chuyền/cross/clearance, hướng cầu môn và vị trí sân, đặc trưng phù hợp mô hình xG |
| Gợi ý chiến thuật | Chỉ số bóng đá đủ chất lượng và tình huống nguồn để truy ngược; không suy gợi ý từ số ID/frame |

Tọa độ người từ homography có thể dùng cho phân bố vị trí. Tọa độ bóng
bay không được chiếu phẳng rồi coi là điểm chạm đất. Không coi người
gần bóng nhất trong ảnh luôn là người kiểm soát bóng. Vùng chưa quan
sát, che khuất và tình huống khó phải có trạng thái chưa xác định.

Hiệu chỉnh sân tay + bù camera vẫn theo bước 4 đã chốt. Việc nghiên cứu
sự kiện không tự cho phép bỏ kiểm tra chất lượng tọa độ hoặc thay schema.
Tự khởi tạo homography chưa được đưa vào phạm vi bổ sung này.

## Lượt đầu: detector bóng riêng

Đã thêm:

- `backend/cv/ball_probe.py`: kiểm tra model cục bộ trên ảnh lấy đều theo
  thời gian. Có full frame và sáu crop chồng, hợp dự đoán bằng IoU NMS.
  Lưu ảnh gốc tách khỏi dự đoán để có thể gán nhãn lại.
- `backend/cv/finetune_ball.py`: lấy lại class ball=0 từ dữ liệu gốc
  đã xác minh ở bước 5b. Không dùng trọng số person đã bỏ class ball.
- `backend/cv/evaluate_ball_probe.py`: chẩn đoán định vị trên mẫu điểm
  có nhãn agent, bỏ ảnh không chắc; không gọi đó là đánh giá độc lập.

Clip phát triển `data/raw/Video Project 12.mp4`, SHA256
`cd6138c73e54f8bc0507bfd7492554a3f3fce5c015f14015173f948b50dc1711`.
Probe gốc lấy 47 ảnh cách một giây: 45 ảnh có ứng viên ở conf0,05,
nhưng có nhận nhầm túi/đồ ngoài sân và bỏ sót bóng. **45/47 không phải
recall hoặc bằng chứng theo dõi được bóng.** Mẫu điểm agent còn nhầm
lẫn vật thể nhỏ với giày và cần rà lại; không dùng tỷ lệ ghép điểm này
để nghiệm thu mô hình. Mẫu quá nhỏ, chỉ là chẩn đoán phát triển.

Nhãn agent ở `docs/fixtures/ball_clip_agent_review_v1.json`: bản nháp
8 ảnh, sửa lại một điểm thành chưa chắc trong quá trình rà, còn 3 ảnh
có điểm/5 ảnh chưa chắc. Tâm bóng ước lượng từ ảnh gốc, dung sai 12 px;
không phải box ground truth, nhãn chuyên gia hay test giữ riêng. Clip
này không dùng huấn luyện.

## Protocol fine-tune khóa trước khi chạy

Tái dùng ảnh/nhóm đã chia ở `yolo_person_dataset_v1/manifest.json`,
kiểm lại SHA256 ảnh và nhãn gốc trước khi giữ class ball. Dữ liệu cùng
nguồn/giấy phép/ghi công ở `CV_FINETUNE_YOLO.md`: CC BY 4.0, nguồn
[martinjolif/football-player-detection](https://huggingface.co/datasets/martinjolif/football-player-detection),
revision `e8b8cea002692efd74c945fcdad63e729adc5671`.

| Tập | Ảnh | Nhãn bóng |
|---|---:|---:|
| Train | 199 | 174 |
| Validation | 100 | 93 |
| Test giữ riêng | 73 | 60 |

YOLO11n COCO gốc → một class ball; 8 epoch, imgsz1280, batch2,
AdamW/lr0=0,001, seed20261027, AMP tắt, workers0; mosaic0,5 và đóng
hai epoch cuối. Protocol: `docs/fixtures/yolo_ball_protocol_v1.json`.
Best checkpoint chọn bằng validation, test chỉ đánh giá sau huấn luyện.
Baseline COCO chỉ giữ class32 trước NMS rồi đổi thành class0 để chấm
đúng nhãn bóng; tránh gộp lớp người/đồ vật vào ball qua single_cls.

Phân nhóm filename/ảnh gần trùng vẫn chưa chứng minh độc lập theo trận.
Nhãn nguồn chưa được chuyên gia rà lại toàn bộ. Không thay model trên
web chỉ vì mAP tăng. Đầu ra thí nghiệm ở `data/processed/ball_finetune_v1`;
kết quả và quyết định phiên được ghi tại `PROGRESS.md`.

Kết quả lượt 8 epoch trên test 73 ảnh/60 bóng:

| Chỉ số | COCO gốc | Fine-tuned |
|---|---:|---:|
| mAP50 | 0,3512 | 0,5579 |
| mAP50–95 | 0,1791 | 0,2009 |
| Precision do validator báo | 0,5083 | 0,7430 |
| Recall do validator báo | 0,3333 | 0,5301 |

Precision/recall này ở điểm chọn của validator, không phải ngưỡng conf
0,1 của clip. AP là metric detector trên bộ ảnh nhãn nguồn, không phải
accuracy sự kiện. Probe sau fine-tune trên 47 ảnh clip còn nhiều ứng
viên sai và bỏ sót; tỷ lệ có ứng viên 47/47 không chứng minh đúng bóng.
**Chưa đưa trọng số vào web, chưa có đếm chuyền/sút hoặc heatmap mới.**

Lệnh tái lập (đầu ra phải mới):

```powershell
.\.venv\Scripts\python.exe -m backend.cv.ball_probe 'data/raw/Video Project 12.mp4' data/processed/ball_probe_new
.\.venv\Scripts\python.exe -m backend.cv.finetune_ball data/processed/ball_training_new
.\.venv\Scripts\python.exe -m backend.cv.evaluate_ball_probe data/processed/ball_probe_new/probe.json docs/fixtures/ball_clip_agent_review_v1.json
```

## Tiếp tục sau detector

1. Rà video với detector ứng viên; gán nhãn bóng trên các đoạn liên tục,
   giữ riêng đoạn kiểm tra, đo vị trí và đoạn mất dấu. Không nội suy
   xuyên che khuất dài/chuyển cảnh hoặc ghép nhầm nhiều bóng.
2. Liên kết bóng–cầu thủ có trạng thái chưa xác định và kiểm tra tiếp xúc;
   đối chiếu nhãn người chạm bóng và đoạn bóng di chuyển tự do.
3. Gán nhãn chuyền/sút và đánh giá precision/recall/F1 theo dung sai thời
   gian đã khóa. Cú sút không được quyết định chỉ bằng tốc độ bóng hoặc
   hướng bóng trong ảnh. Ứng viên chưa xác nhận không đưa vào tổng chính.
4. Nối kết quả đủ chất lượng vào báo cáo bóng đá; chuyển thông tin frame,
   lỗi detector và ID sang phần chẩn đoán. Heatmap/quãng đường chỉ xuất
   cho đoạn hiệu chỉnh đạt yêu cầu; không lấy số liệu Metrica thay cho clip.

Đây là công việc nghiên cứu đang tiếp diễn, chưa phải mô hình nhận diện
chuyền/sút đã nghiệm thu hoặc chức năng heatmap tự động của video mới.

## Nghiên cứu tiếp trên Video Project 15 (27/10/2026)

Nguồn SHA256 `f51735a042b493eba3cced891209fe1b6beb20ca80e20c340c7ede51900495d0`,
job `e0eb4128f58d45ea85c4ef0000ca92df`. Không dùng tọa độ clip12 cho clip15.

`ball_sequence` chạy detector bóng riêng, giữ chuỗi có hỗ trợ liên tục,
lọc vùng sân thô và đường biên gần, bỏ vị trí bóng khi không quan sát
được. Khoảng mất ngắn chỉ dùng nối trạng thái có giới hạn; không tạo
vị trí nội suy. Tiếp xúc gần chân còn có trạng thái mơ hồ; chỉ tạo ứng
viên khi người nhận đã tồn tại, cùng nhóm màu, có bóng tự do giữa hai
người và tỷ lệ thiếu quan sát thấp. Đổi ID không đủ để kết luận chuyền.

Artifact `data/processed/ball_sequence_video15_v3/`: 999 frame có bóng
được chuỗi chấp nhận, 432 frame có ứng viên gần chân trên 1.571 frame.
Đây là số hỗ trợ thuật toán, không phải recall/accuracy. Hai ứng viên:
8–9,533333s ID93→51 nhóm A; 45,6–46,4s ID308→268 nhóm A. Agent đã
rà contact sheet review/pass-1.jpg và pass-2.jpg; đây là rà theo ứng
viên, không phải kiểm định độc lập. Chưa có mô hình cú sút đã kiểm chứng.

`circle_calibration` kiểm tra hình học conic/đường giữa sân bằng dữ liệu
tổng hợp. Thử vòng tròn clip15 bị loại do sai lệch điều khiển 9,2 px;
không nới ngưỡng để nhận. Bản công bố tạm dùng mốc sân chọn tay trong
`docs/fixtures/clip_f51735_manual_pitch_v1.json`, frame900–1199. Kiểm
tra pixel giữ lại do cùng agent ước lượng đạt 5,52 và 2,56 px; không
quy đổi thành độ chính xác mét hay xem là ground truth độc lập.

`project_uploaded_job` kiểm tra hash/kích thước nguồn, theo chuyển động
camera trong cửa sổ giới hạn, dừng khi chất lượng không đạt; tái sử dụng
PitchSmoother/PitchMetrics. Tọa độ theo DATA_CONTRACT, sân giả định 105×68,
gốc trái dưới. 5.956 vị trí hợp lệ trên 297 frame, 1.183 vị trí ngoài sân
bị loại; chỉ công bố đoạn 30–40s. Không cộng qua khoảng mất dấu, không
ép tốc độ quá cao về ngưỡng. Heatmap cộng thời gian người được quan sát,
không đo kiểm soát bóng. ID/nhóm áo chưa xác nhận danh tính/đội thực.

Lệnh từ gốc repo (output nghiên cứu tách khỏi production):

```powershell
$jobFolder = 'data/processed/video_jobs/e0eb4128f58d45ea85c4ef0000ca92df'
.\.venv\Scripts\python.exe -m backend.cv.ball_sequence $jobFolder data/processed/ball_sequence_video15_new
.\.venv\Scripts\python.exe -m backend.cv.project_uploaded_job $jobFolder docs/fixtures/clip_f51735_manual_pitch_v1.json data/processed/pitch_video15_new
```

Artifact đã rà được đặt riêng dưới job/ball_research và job/pitch_estimate
để API đọc. Không tự chạy các nghiên cứu này khi upload video mới; phải
hiệu chỉnh/kiểm tra nguồn trước khi công bố. Web ghi rõ ước lượng và
ứng viên, thu gọn báo cáo frame/ID vào phần chẩn đoán. Còn thiếu đánh
giá độc lập và nhận diện sút/gợi ý chiến thuật có căn cứ.

Kích thước vạch sân tham chiếu [IFAB Law 1](https://www.theifab.com/laws/latest/the-field-of-play/):
khung thành rộng 7,32 m, vùng cầu môn mở 5,5 m mỗi bên nên rộng 18,32 m;
đã sửa hình sân frontend tương ứng. Kích thước sân nguồn vẫn là giả định.

## Mở rộng đoạn sân và chặn trôi mốc (29/10/2026)

Fixture `clip_f51735_manual_pitch_v2.json` bổ sung mốc frame1200 bằng
giao đường giữa sân/biên và hai góc trước vùng cấm địa. Mốc frame900
giữ nguyên. `clip_f51735_landmark_checks_v2.json` chứa sáu cặp giao
cung tròn/vạch cấm địa trên frame901,1050,1199,1201,1350,1499. Tái sử
dụng LandmarkGuard; các điểm này chỉ kiểm tra, không sửa matrix.
Ngưỡng cố định1m theo hệ sân giả định, tối đa150 frame giữa kiểm tra.
Chưa có checkpoint đạt thì chưa xuất vị trí; quá hạn/trôi vượt ngưỡng
chặn tới lần neo tiếp theo. Không kiểm tra ngược toàn bộ khoảng trước
checkpoint; vẫn cần đánh giá dày hơn/độc lập để xác nhận các khoảng đó.

Nhãn thô tại frame1200 ban đầu lệch ở kiểm tra pixel (12,95/10,69px);
đã xem crop vạch sân và sửa nhãn trước lần chạy chuỗi v2. Sai lệch sau
sửa là3,93/3,29px. Đây là quá trình chọn mốc/kiểm tra nội bộ có quan sát
kết quả, không được báo cáo như đánh giá blinded hoặc accuracy độc lập.
Ngưỡng10px/1m không được nới. Không dùng nhãn để fit lại matrix.

```powershell
.\.venv\Scripts\python.exe -m backend.cv.project_uploaded_job data/processed/video_jobs/e0eb4128f58d45ea85c4ef0000ca92df docs/fixtures/clip_f51735_manual_pitch_v2.json data/processed/pitch_video15_guarded_new --landmark-checks docs/fixtures/clip_f51735_landmark_checks_v2.json
```

Kết quả lưu `data/processed/pitch_video15_guarded_v2/`: 11.703 vị trí/
592 frame; hai khoảng camera có kiểm tra30,0333–40s và40,0333–50s;
sai lệch nội bộ lớn nhất0,733m ở sáu checkpoint. Các ID tách theo mốc,
không cộng thành vận động cầu thủ toàn clip. Artifact công bố của job
đã thay bằng bản này, giữ bản cũ riêng. Đây vẫn là hiệu chỉnh tay cho
một nguồn cụ thể; chưa tự tạo hiệu chỉnh cho video tải lên mới.

## Nguồn nền detector và tác vụ tham khảo

- [Ultralytics predict](https://docs.ultralytics.com/modes/predict/):
  lọc class, confidence và kích thước inference; triển khai dùng bản
  Ultralytics cài sẵn 8.3.221, không tự cập nhật theo tài liệu mới.
- [SoccerNet Game State Reconstruction](https://www.soccer-net.org/tasks/game-state-reconstruction):
  bài toán tái dựng người trên sân từ broadcast; tham khảo việc tách
  hiệu chỉnh sân, tracking và định danh thay vì đồng nhất chúng.
- [SoccerNet Tasks](https://www.soccer-net.org/tasks): phân biệt nhiệm
  vụ tracking/calibration với action spotting. Chưa tải bộ dữ liệu hoặc
  model SoccerNet vào dự án trong phiên này.

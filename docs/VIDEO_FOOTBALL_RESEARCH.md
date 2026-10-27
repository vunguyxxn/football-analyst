# Phân tích bóng đá trực tiếp từ video — mở rộng 27/10/2026

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

## Nguồn kỹ thuật tham khảo

- [Ultralytics predict](https://docs.ultralytics.com/modes/predict/):
  lọc class, confidence và kích thước inference; triển khai dùng bản
  Ultralytics cài sẵn 8.3.221, không tự cập nhật theo tài liệu mới.
- [SoccerNet Game State Reconstruction](https://www.soccer-net.org/tasks/game-state-reconstruction):
  bài toán tái dựng người trên sân từ broadcast; tham khảo việc tách
  hiệu chỉnh sân, tracking và định danh thay vì đồng nhất chúng.
- [SoccerNet Tasks](https://www.soccer-net.org/tasks): phân biệt nhiệm
  vụ tracking/calibration với action spotting. Chưa tải bộ dữ liệu hoặc
  model SoccerNet vào dự án trong phiên này.

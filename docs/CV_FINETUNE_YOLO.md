# Bước 5b — fine-tune YOLO11 nano trên ảnh bóng đá

Ngày 23/10/2026: đã hoàn tất một lượt fine-tune và so sánh trước/sau trên
tập test giữ riêng. Mô hình mới là ứng viên ngoại tuyến; pipeline video vẫn
dùng trọng số cũ. Không đổi API hoặc hợp đồng dữ liệu.

## Dữ liệu và nguồn

372 ảnh 1920×1080 từ [martinjolif/football-player-detection trên Hugging Face](https://huggingface.co/datasets/martinjolif/football-player-detection),
khóa revision `e8b8cea002692efd74c945fcdad63e729adc5671`.
Nguồn khai báo giấy phép [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Ghi công: Football project / Roboflow football-players-detection-3zvbc-yyhdl v1;
bản sao Hugging Face bởi martinjolif. [Trang bộ dữ liệu gốc](https://universe.roboflow.com/football-project-pifbc/football-players-detection-3zvbc-yyhdl/dataset/1).

Thay đổi nhãn: bỏ class ball; gộp goalkeeper, player, referee thành
`person` (class 0) để tương thích bộ tracking hiện tại. Đây không phải mô
hình phân đội hoặc loại trọng tài. Có 8.579 box người; hai box vượt mép ảnh
được cắt về biên. Nhãn nguồn được kiểm tra bằng montage ba ảnh, chưa gán
nhãn lại độc lập toàn bộ. Nguồn có người ngoài sân không được gán nhãn,
vì vậy không suy rộng kết quả thành khả năng phát hiện mọi người trong ảnh.

Kiểm SHA256 cho file LFS và Git blob SHA1 cho file thường theo inventory
đã khóa. Chỉ tải ảnh, nhãn văn bản và metadata; không dùng cache pickle từ
nguồn. Inventory ở `docs/fixtures/football_detection_inventory.json`.

## Chia tập và quy trình đã khóa

Không dùng cách chia ngẫu nhiên từng frame có sẵn của nguồn. Nhóm theo
tiền tố tên ảnh trước dấu gạch dưới đầu tiên; hợp nhóm ảnh trùng pixel
hoặc gần trùng (dHash ≤ 4 và MAE thumbnail xám 64×36 ≤ 3) trước khi chia.
15 nhóm, seed 20261023; tỷ lệ mục tiêu 60/20/20 tính theo số nhóm.
Hai cặp gần trùng nằm cùng nhóm; không có ảnh trùng pixel cần loại.

| Tập | Nhóm | Ảnh | Box người |
| --- | ---: | ---: | ---: |
| Train | 9 | 199 | 4.568 |
| Validation | 3 | 100 | 2.358 |
| Test giữ riêng | 3 | 73 | 1.653 |

Không giao nhóm hoặc hash pixel giữa ba tập. Tuy nhiên, tiền tố tên file
chỉ là quy ước suy đoán; chưa xác minh được danh tính trận đấu, và bộ dò
gần trùng không bảo đảm phát hiện mọi frame liên quan. Không gọi đây là
đánh giá độc lập theo trận đấu.

Protocol ở `docs/fixtures/yolo_person_finetune_protocol.json`, khóa trước
khi huấn luyện: YOLO11n pretrained COCO, 15 epoch, batch 4, ảnh 640,
AdamW, lr0 0,001, seed 20261023, workers 0, AMP tắt. Mosaic 0,5,
đóng ở hai epoch cuối; warmup một epoch, deterministic bật. Đầu ra đổi
từ 80 class sang một class; Ultralytics chuyển 448/499 mục trọng số.
Không cài thêm thư viện. Môi trường: Python 3.11.3, Ultralytics 8.3.221,
PyTorch 2.8.0+cu128, CUDA 12.8, RTX 3050 Laptop 6 GB. Thời gian toàn lượt
khoảng 333 giây; kết quả có thể khác đôi chút trên môi trường khác.

Checkpoint `best.pt` được chọn bằng fitness trên validation. Chỉ đánh giá
test sau huấn luyện, không chọn epoch hoặc điều chỉnh cấu hình theo test.
Hai mô hình dùng cùng ảnh/nhãn test, kích thước ảnh 640, FP32, conf 0,001,
NMS IoU 0,7, tối đa 300 box. Conf này dùng để tính đường precision–recall
và AP, không phải ngưỡng hiển thị video.

Ultralytics 8.3.221 bỏ qua `args.classes` trong postprocess của validator.
Runner dùng validator riêng lọc class `person=0` **trước NMS** cho cả hai
mô hình, tránh biến class COCO khác thành người qua `single_cls`, hoặc
để box class khác triệt tiêu box người. Có test hồi quy cho trường hợp này.
Baseline test được nạp mới từ trọng số gốc; hash trọng số gốc không đổi.

## Kết quả test

| Chỉ số | YOLO11n COCO gốc | Sau fine-tune | Chênh lệch điểm phần trăm |
| --- | ---: | ---: | ---: |
| mAP50 | 71,04% | 91,67% | +20,62 |
| mAP50–95 | 39,62% | 56,40% | +16,78 |
| Precision | 74,25% | 92,44% | +18,19 |
| Recall | 74,23% | 85,78% | +11,55 |

Precision/recall do validator tổng hợp tại điểm F1 được chọn trên đường
precision–recall của mỗi mô hình, không phải so tại một ngưỡng conf vận
hành cố định. mAP là chỉ số so sánh chính. Chỉ có một lượt với một seed;
chưa có khoảng tin cậy hoặc đánh giá trên bộ nhãn độc lập của `vid1.mp4`.
Không suy ra chất lượng giữ ID, phân đội, homography hoặc nhận diện sơ đồ
từ mAP phát hiện người. Bước 5 vẫn chưa nghiệm thu chất lượng chiến thuật.

## Chạy lại và kiểm chứng

Chạy tại gốc repo, dùng thư mục output mới để tránh ghi đè:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.prepare_person_dataset --download --output data/processed/yolo_person_dataset_repro
.\.venv\Scripts\python.exe -m backend.cv.finetune_person --dataset data/processed/yolo_person_dataset_repro --output data/processed/yolo_person_finetune_repro
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_finetune_full_v1
```

Trọng số đầu vào cần có ở `data/raw/yolo11n.pt`; SHA256 của lượt này là
`0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`.
Runner từ chối dataset bị sửa, giao nhóm/pixel giữa các tập, protocol
khác manifest, thiếu CUDA hoặc output đã tồn tại. Các thư viện đã cài sẵn
trong môi trường dự án; runner tắt tự cài thư viện và tích hợp logger ngoài.

Artifact cục bộ:

- `data/processed/yolo_person_dataset_v1/manifest.json`: ánh xạ từng ảnh,
  nhóm, tập, hash và thống kê nhãn; `label_review.jpg`: montage rà nhãn.
- `data/processed/yolo_person_finetune_v1/comparison.json`: kết quả gốc.
- Cùng thư mục: `configuration.json`, `progress.json`, `run.log`,
  `training/args.yaml`, `training/results.csv` và `training/weights/best.pt`.
- SHA256 best.pt: `025dc92ed4f7bdde70e2f2442a1ee16fd3aa4ed4a4e32d8f7278f138747e747a`.
- `docs/fixtures/yolo_person_finetune_result_v1.json`: bản chụp kết quả,
  nhóm, cấu hình và hash để xem sau khi xóa dữ liệu cục bộ.

Ảnh, cache và trọng số không đưa vào Git. Có chín test cho đổi nhãn,
nhãn lỗi, gộp nhóm trùng/gần trùng, hash nguồn, tạo dataset, từ chối ghi đè,
phát hiện sửa nhãn và lọc person trước NMS. Bước tiếp theo khi áp dụng
trọng số là so sánh trên video giữ nguyên cấu hình tracking và bộ lọc sân.

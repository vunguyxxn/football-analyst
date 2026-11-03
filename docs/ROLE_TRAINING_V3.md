# Ghép dữ liệu và huấn luyện small v3

Ngày 03/11/2026: đã ghép 58 ROI mới, huấn luyện đủ 20 epoch và đánh giá.
Lỗi cầu thủ bị gọi trọng tài trên validation giảm so với v2, nhưng vẫn
cao hơn v1. V3 chưa đạt gate chọn model; chưa đưa vào ứng dụng.

## Kết quả cùng ngưỡng 0,25

Ghép dự đoán với nhãn theo vị trí, IoU tối thiểu 0,5, không ghép theo
vai trò. Cùng ảnh và nhãn validation/test đã dùng ở các lần trước.

| Chỉ số | Small v1 | Small v2 | Small v3 |
|---|---:|---:|---:|
| Val: player bị gọi referee / 2557 | 757 | 940 | 801 |
| Val: referee nhận đúng / 292 | 35 | 39 | 43 |
| Val: FP referee theo nhãn | 907 | 1058 | 934 |
| Test: player bị gọi referee | 0 | 0 | 0 |
| Test: referee nhận đúng / 76 | 10 | 13 | 11 |
| Test: FP referee theo nhãn | 0 | 9 | 6 |

V3 giảm 139/940 = 14,8% lỗi player→referee so với v2; so với v1 còn tăng
44/757 = 5,8%. Referee recall val tăng lên 14,73%, precision chỉ 4,40%.
Vì vậy chưa thể xem lỗi phân vai trò đã được giải quyết. Test là bộ hồi
quy đã xem, không phải kiểm định độc lập. Chưa kiểm độc lập nhãn, chưa
xác minh tuyệt đối danh tính trận; không dùng test để chọn/tinh chỉnh.

Gate validation khóa trước train: tăng referee AP50 ít nhất 5 điểm phần
trăm so với v1, tổng mAP giảm không quá 3 điểm, player AP50 không giảm
quá 3 điểm, keeper AP50 không giảm quá 5 điểm. V3 không đạt phần tăng
referee AP50; các guard còn lại đạt. Khóa lựa chọn baseline trước test
ở `data/processed/role_training_v3/comparison/selection-before-test.json`.

## Dataset và huấn luyện

Giữ train v2 341 ảnh/lượt crop và thêm mỗi ROI mới đúng một lần: train
399, val128, test35. Hash bytes ảnh/nhãn hai tập kiểm không đổi. Chỉ dùng
ROI đã rà, không đưa toàn ảnh nguồn chưa gán nhãn đầy đủ vào train.
Các lượt crop/lặp không được đếm là người/trận độc lập.

Khởi tạo từ best small v1 giống v2, AdamW mới, 20 epoch, imgsz640,
batch4, AMP off, lr0,0003, seed20261102, mosaic0,5 và tắt 3 epoch cuối.
Không khởi tạo từ v2 để tránh cộng thêm lịch cập nhật khi so sánh.
Đây là một seed; checkpoint được chọn bằng validation fitness, không
khẳng định mức giảm là hiệu quả nhân quả riêng của dữ liệu mới.

Phiên đầu bị ngắt sau epoch18; đã resume từ last.pt với optimizer lưu
và chạy tiếp epoch19–20. Log nằm ở `small/run.log`, `small/resume.log`.
Thời lượng ghi lại chỉ xấp xỉ thời gian xử lý, không gồm thời gian chờ.

Weights cục bộ:
`data/processed/role_training_v3/small/training/weights/best.pt`, SHA256
`49c506916dde438311ef39a0a77330bbce1c1b60c0d9311f307f6a7dc26b53b2`.
Protocol và snapshot kết quả trong `docs/fixtures/role_training_protocol_v3.json`
và `role_training_result_v3.json`; key `balanced` trong evaluator dùng
chung là candidate v3, key `baseline` là v1.

## Lệnh tái lập trên thư mục mới

```powershell
.\.venv\Scripts\python.exe -m backend.cv.merge_role_v3
.\.venv\Scripts\python.exe -m backend.cv.finetune_roles train --dataset data/processed/role_dataset_v3 --protocol docs/fixtures/role_training_protocol_v3.json --output data/processed/role_training_v3/small --model small
.\.venv\Scripts\python.exe -m backend.cv.compare_role_models --dataset data/processed/role_dataset_v3 --protocol docs/fixtures/role_training_protocol_v3.json --run data/processed/role_training_v3/small --output data/processed/role_training_v3/comparison
```

Các lệnh từ chối ghi đè thí nghiệm đã có. Dataset, weights, ảnh crop
giữ cục bộ. Không đổi hợp đồng dữ liệu hoặc model runtime.

# Kiểm nguồn nền, ghép dataset và huấn luyện small sạch v6

Ngày03/11/2026: đã hoàn tất kiểm nguồn, ghép dữ liệu, huấn luyện20epoch
và so sánh cùng bộ kiểm. Giảm nhầm player→referee trên validation,
nhưng chưa đạt gate đã khóa; chưa đổi model ứng dụng hoặc hiệu chỉnh sân.

## Kiểm nguồn nền

Đọc manifestv2, xác minh bytes ảnh/nhãn; xem toàn bộ212ảnh toàn cảnh
qua6contact sheets, thấy ngữ cảnh camera trận thật. Các prefix ngoại
thuộc nguồn martinjolif pinned ở protocolv1/v2; ảnh local có hash
nguồn/frame. Không thấy nhóm Villarreal nghi mô phỏng trong basev2.
Giữ loại5ảnh có nhãn quarantine của v2; không nhận lại bằng cách chỉ
xóa bbox chưa rõ.129lượt ROI giữ nguyên gói đã ràv2, nguồn ảnh/video
và các lần lặp đã ghi trong manifest; không phải129người mới.

Phạm vi kiểm lần này là nguồn/hash/ngữ cảnh media; không gán nhãn lại
từng người trong212ảnh và không xác minh độc lập mọi danh tính trận.
Từ “sạch” không bảo đảm ground truth hoàn hảo. Tài liệu/hash nguồn và
giấy phép kế thừa protocolv1/v2; source auditv6 khóa manifest nền.

## Dataset và protocol

Giữ341lượt trainv2 (212full+129ROI), thêm7ảnh toàn cảnh đã ràv5 ×4lượt
=28. Train369,val128,test35.7ảnh vẫn chỉ là7ảnh riêng biệt, không gọi
28lượt là28nguồn. Không nhập ROIv3 có media chưa xác minh. Không đổi
bytes ảnh/nhãn val/test. Dữ liệu mới từng được rà/screen với tập kiểm,
nhưng chưa chứng minh tách trận tuyệt đối hoặc có đánh giá độc lập.

Khởi tạo `data/raw/role_detector_v1/yolo11s.pt` COCO gốc, SHA256
`85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5`.
Không kế thừa weightsv1/v2/v3 cho train; v1 chỉ dùng làm baseline so
sánh.20epoch,640/batch4,AMPoff,AdamWlr0,0003,seed20261102,mosaic0,5,
tắt3epoch cuối; RTX3050 6GB,877,98giây. Thay điểm khởi tạo và dữ liệu
cùng lúc nên không quy cải thiện riêng cho7ảnh mới. Chỉ thử một seed.

## Kết quả

Ngưỡng0,25,ghép theo vị trí IoU0,5, cùng nhãn/bộ kiểm:

| Validation | Baselinev1 | Smallv6 |
|---|---:|---:|
| Player bị gọi referee /2557 |757|409|
| Player nhận đúng |1604|1971|
| Referee nhận đúng /292 |35|63|
| FP referee theo nhãn |907|511|
| Referee precision |3,72%|10,98%|
| Referee recall |11,99%|21,58%|
| Keeper nhận đúng /92 |33|50|
| mAP50–95 |37,15%|41,78%|
| Referee AP50 |6,45%|10,46%|

Lỗi player→referee giảm45,97% so v1 và48,94% so v3(801). Tuy nhiên
referee AP50 chỉ tăng4,00điểm phần trăm, chưa đạt gate+5điểm. Ba guard
tổng/player/keeper đạt. Khóa quyết định baseline ở selection-before-test
trước khi mở test hồi quy; không nới gate sau khi thấy kết quả.

Test đã biết: mAP50–95 khoảng43,3%, referee TP15/76,FP8,recall19,74%,
precision65,22%; v1 TP10,FP0. Keeper TP6/12 so3/12. Player→referee
0→3,playerTP673→670/695. Có tiến bộ và đánh đổi, chưa đủ duyệt runtime.
Không gọi test này blind hoặc dùng nó để tinh chỉnh.

## Artifact và nghiệm thu

Weights local `data/processed/role_clean_training_v6/small/training/weights/best.pt`,
SHA256 `6d99be77ca79b3e3c924e7568a061bf151909da62f9e9b4708595cef46510c8f`.
Protocol/sourceaudit/result trongdocs/fixtures với hậu tốv6. Key
`balanced` của evaluator là candidatev6, không phải v2. Dataset/weights
giữ cục bộ.542test Python đạt,1network deselected,4warning cũ; đã xác
minh lại manifest,weights và protected split sau train/compare.

```powershell
.\.venv\Scripts\python.exe -m backend.cv.prepare_clean_roles
.\.venv\Scripts\python.exe -m backend.cv.finetune_roles train --dataset data/processed/role_clean_dataset_v6 --protocol docs/fixtures/role_clean_training_protocol_v6.json --output data/processed/role_clean_training_v6/small --model small
.\.venv\Scripts\python.exe -m backend.cv.compare_role_models --dataset data/processed/role_clean_dataset_v6 --protocol docs/fixtures/role_clean_training_protocol_v6.json --run data/processed/role_clean_training_v6/small --output data/processed/role_clean_training_v6/comparison
```

Lệnh từ chối ghi đè thí nghiệm/dataset đã có. Không đổi API,
DATA_CONTRACT,frontend hoặc dependency.

## Bước tiếp theo

Rà các lỗi còn lại củav6, đặc biệt409player→referee và keeper/referee
bỏ sót, trước khi chọn thay đổi dữ liệu hoặc độ phân giải. Cần đánh
giá thêm clip thật chưa dùng gán nhãn/train để quyết định model có đủ
tốt cho báo cáo chiến thuật. Chưa nên bỏ gate hoặc chuyển sang sửa
hiệu chỉnh sân với giả định rằng phân vai trò đã được giải quyết.

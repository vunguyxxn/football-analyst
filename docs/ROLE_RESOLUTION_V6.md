# Cùng weights v6: 640 so với1280

Ngày03/11/2026: đã chạy cùng weightsv6 trên128ảnhval và35ảnhtest,
không train hoặc đổi runtime. Tăng độ phân giải giảm nhầm player→ref
nhưng làm nhận diện keeper kém đi rõ rệt, nên chưa đổi toàn bộ sang1280.

## Thiết lập cố định

Weights SHA256 `6d99be77ca79b3e3c924e7568a061bf151909da62f9e9b4708595cef46510c8f`.
Confidence0,25,NMSIoU0,7,max_det300,ghép vị trí IoU0,5;batch1,FP32,
GPU RTX3050 6GB. Cùng thứ tự ảnh/nhãn trong manifest khóa; xen kẽ size
chạy trước theo frame chẵn/lẻ. Warmup3lần mỗi size trước đo. Không
thay threshold theo kết quả và không dùng test để chọn cấu hình.
Đã tái lập đúng confusion và dự đoán không ghép ở640 với snapshotv6.

## Lỗi trên validation

| Chỉ số |640|1280|
|---|---:|---:|
| Player→referee |409|155|
| Player đúng /2557 |1971|2336|
| FP player |386|472|
| Referee đúng /292 |63|91|
| FP referee |511|354|
| Referee precision |10,98%|20,45%|
| Referee recall |21,58%|31,16%|
| Keeper đúng /92 |50|22|
| FP keeper |28|38|
| Keeper precision |64,10%|36,67%|
| Keeper recall |54,35%|23,91%|

Player→referee giảm62,10%; keeper mất28truepositive. Số player nhận
đúng tăng nhưng FPplayer cũng tăng; không nhìn riêng recall hoặc một
loại lỗi để kết luận detector đạt chuẩn. Đây là fixed-confidence,
không phải phép đo mAP/AP của gate chọn weights; không thay gate cũ.

Test hồi quy đã biết:player→ref3→2,playerTP670→683/695,FP98→92;
refTP15→23/76,FP8→15;keeperTP6→2/12,FP6→4. Xu hướng keeper suy giảm
cũng xuất hiện trên test, không chỉ validation. Chưa có đánh giá độc
lập hoặc người kiểm nhãn riêng cho lần này.

## Tốc độ và bộ nhớ

| Phép đo trên128ảnhval |640|1280|
|---|---:|---:|
| Predict trung bình ms/ảnh |62,16|93,54|
| Median ms/ảnh |60,73|95,76|
| P95 ms/ảnh |84,97|117,59|
| Nghịch đảo thời gian predict: ảnh/giây |16,09|10,69|
| CUDA allocated tensor peak MiB |94,02|165,17|

1280tốn khoảng1,50lần thời gian predict trung bình ở phép đo này.
Test:50,77→84,51ms/ảnh (~19,70→11,83ảnh/s). Đồng bộCUDA trước/sau
predict, đo wall time gồm preprocess/forward/NMS; không gồm đọc file,
đọc nhãn,ghép nhãn hoặc trích bbox raCPU. Một pass xen kẽ kích thước,
chưa có kiểm định độ biến động, nên không coi đây là benchmark video
đầu cuối hoặc mức tăng tốc chắc chắn trên mọi máy.

Peak là tensor do PyTorch cấp phát, **không phải tổngVRAM** của process
hoặc GPU: không gồm CUDA reserved cache,driver,process khác. Các số
này không thay cho peakVRAM khi chạy cả tracking/calibration/web.

## Tái lập

```powershell
.\.venv\Scripts\python.exe -m backend.cv.compare_role_resolution
.\.venv\Scripts\python.exe -m pytest tests/test_role_balance.py tests/test_full_frame_roles.py -q --basetemp .tmp/pytest_role_resolution_v6
```

23test liên quan matching/FP/FN/ROI đạt. Script kiểm hash/mapping,
đối chiếu640với snapshot và kiểm dataset/weights lại sau chạy. Kết quả
local `data/processed/role_resolution_v6/result.json`; snapshot
`docs/fixtures/role_resolution_result_v6.json`. Lệnh từ chối ghi đè.
Không đổi DATA_CONTRACT,frontend,dependency hoặc model ứng dụng.

## Bước tiếp theo

Ưu tiên rà các keeper dẫn tới chênh lệch truepositive ròng28 ở1280:
cần ghép từng đối tượng để phân biệt thay đổi định vị/IoU,nhầm role
hoặc confidence thấp; chênh TP ròng28không tự chứng minh chỉ có28
đối tượng thay đổi. Đồng thời kiểm thêm FPplayer tăng. Sau đó mới
chọn giải pháp dữ liệu/multi-scale hoặc inference; chưa huấn luyện
thêm chỉ để bù một triệu chứng chưa rõ và chưa thay runtime sang1280.

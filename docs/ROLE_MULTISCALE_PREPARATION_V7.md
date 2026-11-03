# Phân bố dữ liệu và chuẩn bị train multi-scale v7

Ngày03/11/2026: đã thống kê datasetv6, chuẩn bị hai nhánh fixed/multi
và kiểm tra một bước tối đa1344trênGPU. Chưa chạy hai lịch train đầy
đủ, chưa có weights hoặc kết quả cải thiệnv7. Không đổi runtime.

## Phân bố bbox hiện có ởimgsz640, trước augmentation

| Train theo lượt xuất hiện |<24px|24–48px|≥48px|Tổng|
|---|---:|---:|---:|---:|
| Player |3920|711|50|4681|
| Goalkeeper |201|10|0|211|
| Referee |423|110|87|620|

369lượt ảnh chỉ có302đơn vị pixel+label khác nhau:212full nền,
83ROIkhác nhau và7full mới. Số bbox trong đơn vị không lặp:
player4369,keeper193,ref556. Đó không phải số người/trận độc lập,
vì các frame vàcrop có thể cùng đối tượng. Sau loại lặp,keeper189/193
vẫn dưới24px. Val92/92keeper vàtest12/12keeper dưới24px.

Như vậy train không thiếu tuyệt đối keepernhỏ, nhưng mất cân bằng
vai trò rõ:keeper khoảng3,8%bbox theo lượt. Không kết luận nguyên
nhân duy nhất là người nhỏ; lỗi đổi role khi1280 cần học biểu diễn
ổn định theo kích thước và kiểm tra tổng quát hóa màu áo/ngữ cảnh.

Metadata màuROIref đã rà:blue33unique/33exposure,yellow10/30,
red3/18,black1/6. Chỉ tính đối tượng chính trong ROI có metadata;
full-frame nền chưa có bảng màu đầy đủ, nên không nói train chỉ có
1trọng tài đen. Trong7full mới đã xem, k84/obj7vànew11/obj10áotối;
6keeper cóblue,white,yellow,orange,pink-red. Các thông tin màu này
chỉ là inventory một phần doagent rà, chưa kiểm độc lập. Không thu
nguồn mới hoặc tự tạo nhãn màu từHSV trong bước chuẩn bị này.

Không tăng lặp ROIblack1lên nữa: tăngexposure không tạo thêm đa dạng.
Giữ nguyên samplingv6 để phép thử có thể tách ảnh hưởngmulti-scale.
Nếu hai nhánh đều kém, ưu tiên thêm keeper/refáotối nguồntrain mới,
không lấyval/test để bù màu/kích thước.

## Hai nhánh đã khóa

- Cùng bestv6 sạch làm điểm khởi tạo,AdamWmới,20epoch,lr0,0001,
  batch1,FP32/AMPoff,seed20261102,mosaic0,5,tắt3epochcuối.
- Fixed:imgsz896,multi_scale=false.
- Multi:imgsz896,multi_scale=true. CodeUltralytics8.3.221 đang cài
  dùngbool và chọn0,5–1,5lần kích thước gốc, làm trònstride32:
  khoảng448–1344. Không dùngimgsz1280multi-scale vì sẽ lên tới1920.
- Dataset369/128/35giống nhau từnghashảnh/nhãn, chỉmanifesthash
  protocolvàđườngdataset khác. Protocol chỉ khácarmIDvàmulti_scale.
- Checkpoint từng nhánh chọn bằngfitnessvalidation nội bộ896.
  Đánh giá độc lập sau train đặt640bằngevaluation_image_size,giữ
  ngưỡngconf0,25/NMS0,7/matching0,5/gatecũ so với v1. Cần đo thêm
  1280cả3vai trò theo cách đã làm ởv6, không tự chọn size từ test.

Việc tăngepoch/chuyểnbatch/đổiimgsz so với v6 cũng tác động kết quả;
chỉ so fixed896vớimulti896 mới nhắm riêng hiệu ứng bậtmulti-scale,
vẫn chỉmộtseed/chưa kiểm độc lập. Không coi gateđạt là tự động deploy.

## Kiểm bộ nhớ

Probe thực hiện1bước loss/backward/AdamW trên bản sao model, ảnh train
resizevuông1344,batch1,FP32. Tensorpeak2473,94MiB,reserved4178MiB,
loss hữu hạn,inputweights giữ nguyên,không lưu weights saustep.
Đây là smoke,không phải kết quả train hoặc peak toànrun. Chưa gồm
mosaicloader/validation,driver/process khác; phải theo dõiOOMkhi chạy
thật, không tự tăngbatch. Khi thiếubộnhớ cần ghi thất bại và khóa
protocol mới trước thử lại, không âm thầm đổi thông số giữa nhánh.

## Artifact và lệnh tiếp theo

Thống kê: `docs/fixtures/role_distribution_v6.json`.
Plan+hai protocol: `role_scale_plan_v7.json`,
`role_scale_fixed_protocol_v7.json`,`role_scale_multi_protocol_v7.json`.
Probe: `role_scale_memory_probe_v7.json`.
Hai dataset đã xuất: `data/processed/role_scale_v7/fixed_dataset` và
`multi_dataset`. Không ghi đèv6,giữval/test.555testPythonđạt,
1networkdeselected,4warningcũ;7testmới kiểmflagbool,envelope vàsizebin.

```powershell
.\.venv\Scripts\python.exe -m backend.cv.role_distribution
.\.venv\Scripts\python.exe -m backend.cv.prepare_role_scale
.\.venv\Scripts\python.exe -m backend.cv.probe_role_scale_memory
```

Lệnhprepare từ chối datasetoutput có sẵn; không cần chạy lại khi đã
cóhai datasetv7. Lệnhtrain cho bước tiếp theo, chạy tuần tự:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.finetune_roles train --dataset data/processed/role_scale_v7/fixed_dataset --protocol docs/fixtures/role_scale_fixed_protocol_v7.json --output data/processed/role_scale_v7/fixed_run --model small
.\.venv\Scripts\python.exe -m backend.cv.finetune_roles train --dataset data/processed/role_scale_v7/multi_dataset --protocol docs/fixtures/role_scale_multi_protocol_v7.json --output data/processed/role_scale_v7/multi_run --model small
```

Sau train: khóa kết quảval trước khi test,so cả3lớp/FP/FN/khungtrùng
ở640và1280. Chưatrainlịch đầyđủ trong phiên này. KhôngđổiAPI,
DATA_CONTRACT,dependency hoặcfrontend.

# Thử lọc khung trùng vai trò ngoại tuyến

Ngày03/11/2026: đã thử một chính sách cố định, giữ nguyên weightsv6,
input1280,conf0,25,NMSphânlớpIoU0,7,max_det300 và phép ghép nhãn
role-blindIoU0,5. Không train hoặc thay runtime.

## Chính sách thử

SauNMSgốc, xét khung theo confidence giảm dần, tie theo thứ tự đầu vào.
Nếu khung khác vai trò cóIoU>0,7 với một khung đã giữ, loại khung điểm
thấp hơn. Không ưu tiên thủ môn hoặc dùng vị trí/nhãn thật để chọn.
Giữ nguyên khung cùng lớp; khung bị loại không loại tiếp khung khác.
Các khung còn lại trở về thứ tự ban đầu trước phép chấm đã khóa.
Ngưỡng0,7 dùng lại mứcNMSgốc, chốt trước chạy; không sweep hoặc điều
chỉnh theo test. Không khẳng định mọi cặp overlap cao đều cùng người.

## Validation128ảnh

| Lớp | TP trước→sau | FP trước→sau | FN trước→sau |
|---|---:|---:|---:|
| Player |2336→2356|472→340|221→201|
| Goalkeeper |22→26|38→19|70→66|
| Referee |91→81|354→195|201→211|

Precisionplayer83,19→87,39%;keeper36,67→57,78%;ref20,45→29,35%.
Recallkeeper23,91→28,26% nhưngref31,16→27,74%. Player→ref155→138.
Keeper có8lượt được nhận đúng mới,4lượt mấtTP,18lượt giữ đúng;
cải thiện ròng4không có nghĩa mọi lỗi khungtrùng đã sửa.

Loại296khung:ref→player168,player→ref102,keeper→player13,
player→keeper10,ref→keeper1,keeper→ref2. Mũi tên là vai trò khung bị
loại→khung được giữ, không phải nhãn groundtruth hoặc số sửa đúng.
Confidence khác lớp chưa được xác minh là so sánh/cân chuẩn tốt.

## Test hồi quy35ảnh đã biết

| Lớp | TP trước→sau | FP trước→sau | FN trước→sau |
|---|---:|---:|---:|
| Player |683→683|92→84|12→12|
| Goalkeeper |2→2|4→3|10→10|
| Referee |23→21|15→7|53→55|

Player→ref vẫn2. Loại19khung, không tăngTPkeeper, lại giảmTPref2.
Đây là bộ hồi quy đã xem, không đánh giá độc lập hoặc dùng làm lý do
chọn/tinh chỉnh chính sách. Không lấy tổng giảmFP để bỏ qua giảmrecall.

## Kết luận và giới hạn

Chính sách đạt mục tiêu giảm FPnhưng không cải thiện đồng đều3vai trò.
Đặc biệt không giải quyết được phần lớn keeper bị gọiplayer mà không
có khungkeeper phù hợp; chỉ lọc được xung đột đã có nhiều khung.
Việc áp dụng toàn cục có thể loại người thật đứng chồng nhau. Lần này
chưa rà trực quan mọi suppression-event, nên không gọi tất cả khung
bị loại làduplicate thật. Chưa duyệt đưa vào ứng dụng, không sửa phép
chấm hoặc hạ threshold để bù kết quả.

## Artifact và lệnh kiểm tra

```powershell
.\.venv\Scripts\python.exe -m backend.cv.offline_role_dedup
.\.venv\Scripts\python.exe -m pytest tests/test_offline_role_dedup.py tests/test_role_balance.py -q --basetemp .tmp/pytest_offline_role_dedup
```

22test đích đạt: thứ tự/tie,người lân cận,cùnglớp,không loại dây chuyền,
không đổimutationinput,ngưỡng hợp lệ và matching/FP/FN/gate hiện có.
Toàn bộ548test Python đạt,1networkdeselected,4warningcũ.
Chạy thực tế đối chiếu chính xác1280baseline với snapshotresolution,
kiểmhashdataset/weights vàmapping trước/sau. Kết quảlocal
`data/processed/offline_role_dedup_v6/result.json`,chi tiết khung bị
loại trong `suppression-events.json`;snapshot
`docs/fixtures/offline_role_dedup_v6.json`. Lệnh từ chối ghi đè output.
Không đổi API/DATA_CONTRACT/dependency/frontend hoặc weights.

## Bước tiếp theo

Giữ runtime hiện tại và ngừng thử nới lọcconfidence để giải quyết mọi
vai trò. Chuẩn bị thửtrainmulti-scale với mẫu keeper nhỏ,nhiều màu áo
và refereeáotối từnguồntrain mới; trước train phải kiểm phân bố lớp/
kích thước,khóa sampling vàgate,giữsplit cũ. Có thể dùng lại log khung
trùng làm tập rà phát triển nhưng không chuyểnval/test sangtrain.
Chưa coi kết quả này đủ để chốt vai trò cho báo cáo chiến thuật.

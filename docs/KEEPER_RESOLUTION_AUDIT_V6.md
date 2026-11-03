# Vì sao thủ môn nhận đúng giảm ở1280?

Ngày03/11/2026: đã ghép từng nhãn keeper trênval92lượt vàtest12lượt,
cùngweights/conf0,25/NMS0,7/matchingIoU0,5 của phép thử resolution.
Tái lập đúng keeperTPval50→22,test6→2. Không train hoặc đổi nhãn,
runtime hay quy tắc matching.

## Đối chiếu từng nhãn

| Chuyển trạng thái640→1280 |Validation|Test hồi quy|
|---|---:|---:|
| Đúng cảhai |17|2|
| Đúng640 nhưng sai1280 |33|4|
| Sai640 nhưng đúng1280 |5|0|
| Sai cảhai |37|6|

Do đó TPgiảm ròng28 ởval là33mất−5được, không phải chỉ28đối tượng
thay đổi. Đây là lượt quan sát, có thể lặp cùng thủ môn qua nhiềuframe.

Toàn37lượt mất nhận đúng vẫn ghép được với dự đoán **player**, không
phải không có khung. IoUkhung player với nhãn:val0,736–0,948,
test0,813–0,935; đều vượt gate0,5 khá rõ. Medianconfidenceplayer1280
val0,771,test0,875. Không có trường hợp nào trong37lượt này chỉ vì
khung dự đoán được chọn bị lệch đến mức không đủIoU.

## Tách dự đoán sai vai trò và khung trùng lớp

Chỉ cho các lượt mất TP, chạy thêmprobe1280conf0,001; đây là dữ liệu
chẩn đoán sauNMS, không đổi ngưỡng đánh giá chính và không phải vector
điểm lớp thô của mạng.

| Tình huống |Val33lượt mất|Test4lượt mất|
|---|---:|---:|
| Không có keeperprobe ghép đủIoU; player được chọn |23|3|
| Keeperprobe đủIoU nhưngconfidence<0,25 |1|1|
| Keeper ở ngưỡng0,25 đã đủIoU, nhưng player thắng ghép vị trí |9|0|

Nhóm23không chứng minh xác suấtkeeper bằng0: probe chỉ quan sát output
sau lọc lớp/NMS/max_det. Tuy nhiên bằng chứng trực tiếp là output được
ghép đổi vai trò thànhplayer, không phải chỉ thiếuconfidence hoặc mất
định vị. Hạ ngưỡngconfidence đơn thuần chưa có căn cứ khắc phục23lượt.

Nhóm9có cảhai khung role khác nhau. NMSphân lớp hiện tại có thể giữ
hai khung, evaluator role-blind ghép một-một theoIoU trước khi xét vai
trò. IoUplayer cao hơnkeeper từ0,0032đến0,2279; ở5/9lượt scorekeeper
còn cao hơnplayer nhưng matching không chọn theo score. Đây là lỗi
dự đoán trùng vai trò tương tác với quy tắc ghép đã khóa; không được
đổi matching theo nhãnkeeper để làm đẹp số. Việc có thêm keeperbox
cũng có thể góp FP vì không được ghép; chưa quy mọiFPkeeper về9ca này.

## Rà trực quan

Đã xem toàn37contextcrop bị mấtTP, gồm33val và4test. BboxGT xanh lá,
640xanh lam,1280đỏ. Có keeper nhiều màu áo, đứng gần khung thành hoặc
trong vùng sân quan sát được; đa số mờ/nhỏ. Valcao11–22px khiquy640,
test17,7–21,7px. Rà này chưa thấy bằng chứng đủ để tự sửa nhãn, chưa
có người kiểm độc lập; crop không thay thế xác minh toàn cảnh/trận.

33val phân bố prefix4b770a17,5384388,798b456,cd987c2;4testđềuthuộc
08fd33. Không lấy ảnh bộ kiểm để bổ sung train. Đổi kích thước input
là một thay đổi quan sát được; chưa chứng minh cơ chế bên trong mạng
hoặc một nguyên nhân nhân quả duy nhất cho nhầmkeeper→player.

## Nghiệm thu và artifact

```powershell
.\.venv\Scripts\python.exe -m backend.cv.audit_keeper_resolution
.\.venv\Scripts\python.exe -m pytest tests/test_role_balance.py tests/test_full_frame_roles.py -q --basetemp .tmp/pytest_keeper_resolution_audit_v6
```

Script kiểmhash/mapping,dataset giữ nguyên,kiểmTPtừngsize/split khớp
snapshot. Outputđãkiểm `data/processed/keeper_resolution_audit_v6_checked`,
2sheetvàresult; snapshot `docs/fixtures/keeper_resolution_audit_v6.json`
chứa104nhãn,phânnhóm,khung/conf/IoU vàprobe. Lầnprobe bổ sung giữ
nguyên dự đoán chính từng nhãn so với lần rà ban đầu; đã đối chiếu
trực tiếp trước khi ghi trạng thái rà37mẫu.23test liên quan đạt.
Không thay API,DATA_CONTRACT,dependency/frontend hoặc weights.

## Bước tiếp theo

Thử xử lý các khung dự đoán trùng vai trò ở bước inference ngoại tuyến,
giữ nguyênmatching và báo cả3lớp/FP/FN, không đặt luật dựa vào nhãn thật.
Việc này chỉ nhắm nhóm cạnh tranh khung, không kỳ vọng tự sửa23ca
thiếu outputkeeper. Sau đó mới quyết định thửtrainmulti-scale với mẫu
keeper nhỏ và nhiều màu áo từnguồntrain mới. Chưa hạconf hoặc chọn1280
đại trà; chưa train thêm trước khi kiểm chứng thay đổi inference.

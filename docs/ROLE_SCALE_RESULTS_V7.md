# Kết quả chạy fixed và multi-scale v7

Ngày03/11/2026: đã chạy tuần tự đủ20epoch mỗi nhánh, đo cả3vai trò
ở640và1280 trênval128/test35. Không đổi model ứng dụng.

## Thiết lập và giới hạn

Hai nhánh cùngweightsv6,dataset369/128/35,sampling,batch1FP32,AdamW
lr0,0001,seed20261102,mosaic0,5/tắt3epochcuối. Fixedimgsz896;
multibậtmulti_scale448–1344. Bestcheckpoint chọn bởi valfitness896,
không lựacheckpoint theo test hoặc theo640/1280 riêng.

Fixed chạy liên tục20epoch. Multi bị gián đoạn sauepoch9,đãresume
optimizer/lastcheckpoint từepoch10đến20. Không bảo đảm replayRNG
bitwise so với chạy liên tục; đây là thí nghiệm thực tế mộtseed,
chưa phải bằng chứng nhân quả thuần túy của multi-scale.

Đánh giá cùngconf0,25,NMS0,7,max_det300,role-blindmatchingIoU0,5,
không dùng bộ lọc khungtrùng ngoại tuyến. Cảhaihoànthànhval640/1280
và khóa `validation-before-test.json` trước khi đọc test hồi quy đã
biết. Baselinev1AP640được tính lại cùngbatch1 để áp gatecũ công bằng.
Không đổiảnh/nhãn/weights đầu vào; kiểmhash trước/sau vàhai dataset
giốngnhau từngrecord. Không đánh giá độc lập hoặc nhận dạng danh tính.

## Validation: TP / FP / FN

| Size |Lớp|Fixed896|Multi-scale|
|---|---|---:|---:|
|640|Player|1924 /372 /633|1866 /339 /691|
|640|Keeper|37 /15 /55|41 /9 /51|
|640|Referee|37 /528 /255|24 /519 /268|
|1280|Player|2405 /367 /152|2247 /401 /310|
|1280|Keeper|50 /34 /42|53 /67 /39|
|1280|Referee|47 /168 /245|89 /402 /203|

Player→referee: fixed640449,multi640444;fixed128087,multi1280220.
Ở1280,multi tăngTPkeeper3sofixed nhưngFPkeeper tăng33;precision
keeper59,52%fixed so44,17%multi. Multi tăngTPref42 nhưngFPref tăng234;
precisionref21,94%fixed và18,13%multi. Không xemTPđơn lẻ để duyệt.

So với v6ở1280 (keeper22/38,ref91/354,player2336/472 theoTP/FP):
fixed cải thiệnkeepernhưng mất nhiềurefTP;multi cải thiệnkeepernhưng
FPkeepercao hơn,refTP89so91vàFPref402so354. V6không tự trở thành
model runtime được duyệt chỉ vì các nhánh mới chưa đạt.

## Test hồi quy: TP / FP / FN

| Size |Lớp|Fixed896|Multi-scale|
|---|---|---:|---:|
|640|Player|677 /102 /18|663 /84 /32|
|640|Keeper|5 /4 /7|6 /9 /6|
|640|Referee|5 /0 /71|4 /3 /72|
|1280|Player|687 /107 /8|685 /81 /10|
|1280|Keeper|4 /3 /8|5 /9 /7|
|1280|Referee|8 /3 /68|18 /5 /58|

Player→referee:testfixed6400,multi6402;1280cảhai0. Test không dùng
để chọn size,checkpoint hoặc điều chỉnhngưỡng sau khi xem kết quả.

## Gate và quyết định

ValmAP50–95ở640:fixed40,74%,multi37,84%. RefereeAP50:fixed8,44%,
multi7,82%. Cảhai chưa đạt tăng5điểm phần trăm refereeAP50 so với
baselinev1 nhưgateđãkhóa; multi còn không đạtkeeperAPguard. Fixed
đạt ba guard còn lại. Không promote hoặc nới gate.

Việc train đa kích thước có thể giúp keeperở1280 trong lần thử này,
nhưng chưa nâng chất lượng đồng đều3lớp, đặc biệtrefereeở640 còn yếu.
Không kết luận multi-scale luôn tốt/xấu từ mộtseed và lầnresume.

## Thời gian, artifact và kiểm tra

Fixed1227,23giây (~20,45phút),tensorpeak2148,15MiB.
Multi1451,15giây ước tính thời gian xử lý (~24,19phút),tensorpeak
2720,46MiB ở phầnresume; không phải tổngVRAM hoặc benchmark tốc độ
được kiểm soát. Thời gianmulti không gồm khoảng gián đoạn, có thể
bỏ phần epoch bị ngắt trước checkpoint; không dùng làm tỷ lệ tốc độ
chắc chắn.555testPythonđạt,1networkdeselected,4warningcũ.

Weightslocal:

- Fixed:`data/processed/role_scale_v7/fixed_run/training/weights/best.pt`,
  SHA256 `78c519e27a2f8deadec3b20229d94d053b7215f04e4cc79c557b8e6af7a7c827`.
- Multi:`data/processed/role_scale_v7/multi_run/training/weights/best.pt`,
  SHA256 `530b1c28fc199e46669c20f3f79218772ee651b0e04216cdaae8975b9203f4a4`.

Snapshot `docs/fixtures/role_scale_result_v7.json`; fullresult/log và
validationfreeze trong `data/processed/role_scale_v7/comparison`.
Planv7 vẫn là snapshot chuẩn bị, không là trạng thái job trực tiếp.
Lệnh so sánh lại trênoutput mới (module mặc định từ chối ghi đè):

```powershell
.\.venv\Scripts\python.exe -m backend.cv.compare_role_scale_runs
```

Không đổi API,DATA_CONTRACT,dependency/frontend hoặc runtime.

## Bước tiếp theo

Ưu tiên bộ dữ liệu và nhãn vai trò: rà màu/ngữ cảnh củarefereeáotối
trongfull-frame train, thêm nguồntrainthật khác trận cókeeper/referee
nhỏ và gán đầy đủ. Chưa nên tiếp tục tăngepoch hoặc biến đổi độ phân
giải trên cùngnguồnítđa dạng. Cần kiểmclipthật chưa dùngtrain để chốt
mức tin cậy, không chuyểnval/test sangtrain. Với demo hiện tại vẫn
phải ghi nhóm màu/IDước lượng, không khẳng định mọi nhóm là vai trò
đã xác minh; ưu tiên hiệu chỉnh sân chỉ khi giữ được các giới hạn đó.

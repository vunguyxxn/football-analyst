# Audit goalkeeper FP và referee FN v14 so v11 trên val1280

Ngày 05/11/2026. Audit ngoại tuyến đã hoàn tất; không train, không sửa GT, không đổi model ứng dụng. Một seed và nhãn do agent rà, chưa nghiệm thu độc lập.

## Phạm vi và xác minh

Đọc AGENTS/PROGRESS/DATA_CONTRACT và báo cáo training v14. Kiểm lại protocol/plan/manifest/sampling ledger, mọi ảnh/nhãn snapshot và dữ liệu nguồn, weights v11/v14, fixture/local result đánh giá và validation-before-test hash. Val cùng128ảnh/hash như v11. Chỉ inference các ảnh val; không known test hoặc match128057. API/schema/frontend và dữ liệu đã phát hành giữ nguyên.

Dùng lại128 prediction v11 từ role_error_audit_v11/predictions.json. Xác thực cache ảnh/nhãn và geometry GT, weights, toàn bộ49 keeper FP và292 referee GT khớp artifact audit v11 có hash đã công bố. Cache v11 chưa có hash riêng trong fixture cũ; audit mới ghi SHA cache, đồng thời kiểm bằng chứng từng case và replay mọi số đếm. Artifact training v14 chỉ chứa số liệu tổng, không đủ box/score; vì vậy chạy đúng128 prediction v14 tại1280 một lần và lưu lại. Bổ sung raw head trên114ảnh val có referee FN, dùng lại raw v11 đã lưu cho149nhãn; không inference v11 mới.

Phép chấm giữ conf0.25,NMSIoU0.7,matchingIoU0.5,max_det300,FP32; không cross-role dedup. Matching GT–prediction một-một, không ưu tiên lớp, theo IoU giảm dần và tie-break chỉ số gốc. Giữ nguyên thứ tự prediction. Replay khớp chính xác TP/FP/FN,P/R,confusion và unmatched của cả3lớp với fixture training v14.

## Replay cả ba lớp

| Role | Model | TP | FP | FN | Precision | Recall |
|---|---|---:|---:|---:|---:|---:|
| player | v11 | 2459 | 437 | 98 | 84.91% | 96.17% |
| player | v14 | 2392 | 365 | 165 | 86.76% | 93.55% |
| goalkeeper | v11 | 50 | 49 | 42 | 50.51% | 54.35% |
| goalkeeper | v14 | 68 | 110 | 24 | 38.20% | 73.91% |
| referee | v11 | 143 | 230 | 149 | 38.34% | 48.97% |
| referee | v14 | 115 | 186 | 177 | 38.21% | 39.38% |

## Toàn bộ keeper FP:89 mới,21 còn lại,28 đã hết

Ghép hai tập **FP** riêng trong cùng ảnh bằng greedy IoU>=0.5,một-một, IoU giảm dần và tie-break index. Mỗi FP v14 ghép được một FP v11 gọi còn lại; không ghép gọi mới; FP v11 không được ghép gọi đã hết. Đây là liên hệ không gian của các lỗi theo GT cố định, không phải định danh người/vật hay theo dõi đối tượng. Một người có thể có nhiều box. Một FP cũ đã hết có thể trở thành TP hoặc không còn keeper box; không đồng nghĩa người đó biến mất.

49FP v11 =21còn lại+28đã hết;110FP v14 =21còn lại+89mới. Tăng ròng61=89−28, không phải61lỗi mới. Giữ cả49case cũ trong bảng audit, không chỉ110case hiện tại.

110FP hiện tại theo cơ chế scoring:63ghép sai lớp (58GTplayer/5GTreferee),29unmatched dù có GTIoU>=0.5được prediction khác chiếm,18không có GTIoU>=0.5. Có46FP có player prediction khác chồng IoU>=0.5; không coi mọi FP là nhận nhầm một người độc lập.

Phân loại trực quan sau rà toàn bộ crop, context khó và crop native phóng lớn:

| Nội dung khung FP | Tổng | Trong89FP mới |
|---|---:|---:|
| official_person | 5 | 5 |
| outfield_person | 76 | 63 |
| gt_keeper_with_competing_box | 9 | 7 |
| off_field_person | 3 | 0 |
| goal_post | 6 | 5 |
| ball | 2 | 1 |
| keeper_like_gt_player_requires_review | 3 | 2 |
| uncertain_advertising_edge_object | 1 | 1 |
| gt_keeper_localization_below_iou50 | 2 | 2 |
| advertisement | 1 | 1 |
| stadium_lamp | 2 | 2 |

76khung trên cầu thủ sân là nhóm lớn nhất;5trên trọng tài được giữ riêng, không gọi họ là người ngoài sân. 11vật nền gồm6cột gôn,2bóng,2đèn và1quảng cáo;3người ngoài sân. Keeper-23 ở mép chữ quảng cáo còn mơ hồ sau xem4x, giữ nhóm uncertain thay vì khẳng định có người. Có109/110FP cao<24px khi thu cạnh dài640,1ở24–48px (đo bbox prediction trước augmentation).

9case GTkeeper có khung cạnh tranh không phải9thủ môn bị nhận sai loại: box keeper thua matching với box khác quanh GT. Keeper-34/49 nhìn đúng thủ môn nhưng IoU gần nhất với GTkeeper lần lượt0.4732/0.4858, chưa đạt0.5. Không hạ matching hoặc tự gọi là thiếu GT từ hai case này.

## Cờ nhãn:chỉ yêu cầu nghiệm thu, giữ nguyên scoring

| Case | Ảnh/index GT | Cờ |
|---|---|---|
| keeper-14 | 4b770a_1_7…0344c0dc…; GT7 | Người xám giống keeper, GTplayer; sát mép phải |
| keeper-20 / oldkeeper-6 | 4b770a_5_6…cc113a3e…; GT6 | Người xám trong vùng cầu môn giống keeper, GTplayer |
| keeper-57 | 538438_7_5…cfd814ca…; GT0 | Người xám giống keeper, GTplayer; sát mép phải |
| keeper-66 / oldkeeper-29 | 798b45_3_2…d951824d…; không có GTchồng box | Người đỏ giống cầu thủ sân, nghi thiếu nhãn player |
| referee-120 | 538438_3_10…1130754d…; GT6 | Staff/official chưa chắc, cờ cũ tiếp tục giữ |

Đây là7dòng audit trên5case nguồn, không phải7người độc lập. Crop player đỏ66 đã kiểm native4x, mọi GTIoU với prediction bằng0; keeper prediction vẫn là FP theo scoring dù có bổ sung một GTplayer sau nghiệm thu. Không sửa nhãn hoặc tính lại kết quả theo các cờ. Paths đầy đủ, boxes, index, score và ảnh chứng minh nằm trong review fixture/CSV.

## Từng referee GT:67 mất đúng,39 nhận thêm

Trong292GT:76giữ đúng,67v11đúng→v14sai,39v11sai→v14đúng,110vẫn sai. TP143=76+67→115=76+39; FN149→177. Mất ròng28khác với67lượt mất đúng. Đã xem toàn bộ292crop, ưu tiên67lost và39gained, và xem context toàn cảnh của toàn bộ118case biên xa.

Phân nhóm vị trí do agent rà theo đường biên nhìn thấy, không phân loại chỉ bằng y:

| Vị trí | GT | Giữ đúng | Mất đúng | Nhận thêm | Vẫn sai | TPv11→v14 |
|---|---:|---:|---:|---:|---:|---|
| far_touchline | 118 | 20 | 50 | 4 | 44 | 70→24 |
| interior | 125 | 25 | 8 | 33 | 59 | 33→58 |
| near_touchline | 48 | 31 | 9 | 2 | 6 | 40→33 |
| near_touchline_role_uncertain | 1 | 0 | 0 | 0 | 1 | 0→0 |

Biên xa TP70/118→24/118, recall59.32%→20.34% theo phân nhóm trực quan này. Trong50lost biên xa có49GT<24px tại640,1case24.2px; toàn bộ118GT biên xa có117<24px. Chưa phải 118người/trận độc lập và vị trí này chưa được nghiệm thu độc lập.

Rà lại toàn cảnh phát hiện metadata vị trí của audit v11 sai ở referee-159 (GT10,538438_7_1…45f573e5…) và referee-230 (GT7,798b45_7_1…fe31e705…): hai người ở trong sân, không ở biên xa. Audit mới sửa thuộc tính vị trí sang interior; giữ nguyên fixture cũ và toàn bộ GT/scoring. Màu áo:291dark/1orange (referee-125 biên gần); phân màu chỉ là thuộc tính thị giác, không suy ra danh tính trận/official.

| Cao GTtại640 | Giữ đúng | Mất đúng | Nhận thêm | Vẫn sai |
|---|---:|---:|---:|---:|
| under24 | 45 | 58 | 30 | 101 |
| 24to48 | 31 | 9 | 9 | 9 |
| 48plus | 0 | 0 | 0 | 0 |

## Chẩn đoán inference:đã xác minh và giới hạn

Raw là score từng lớp sau sigmoid, trước single-label argmax/NMS; không phải xác suất dự đoán đúng. Chỉ tính trên raw boxes có IoU>=0.5 với GT; không lẫn maxscore trên cả ảnh.

| Cơ chế v14 trên referee FN | Toàn bộ177FN | Trong67lost |
|---|---:|---:|
| correct_role_score_below_threshold | 136 | 57 |
| correct_role_box_present_but_matching_competes | 32 | 9 |
| correct_role_loses_class_argmax | 8 | 1 |
| no_raw_box_at_iou50 | 1 | 0 |

Trong50lost biên xa:48score referee dưới0.25,2có correct-role box nhưng cạnh tranh matching. Trong39gained, chẩn đoán v11 cũ là19score thấp/15matching cạnh tranh/5argmax; vì vậy không coi mọi lượt nhận thêm là score tăng.

Ví dụ referee-0 (GT0,4b770a_1_4…dfb7854e…): v11refscore0.3280→v14ghép keeper score0.5828; max rawref tạiIoU>=0.5 chỉ0.1329. Referee-43 (GT21,4b770a_1_7…0344c0dc…): rawref0.2806 đã qua0.25 nhưng player0.4061 thắng argmax; prediction được ghép là player. Referee-46 không có raw boxIoU>=0.5, nên chỉ xác nhận localization/coverage không đạt tiêu chuẩn, chưa khẳng định do vật che hay NMS.

Không có case177FN rơi vào nhóm “winning correct raw box removed before matching” sau các điều kiện trên. Không cần chạy bổ sung NMS để giải thích một nhóm không xuất hiện. 32matching cạnh tranh có danh sách correct-role survivor/index/score/GT được ghép trong JSON; không gọi chúng là lỗi NMS. Chưa chạy thử chính sách thay thế, chưa kết luận đổi NMS/dedup/ngưỡng sẽ cải thiện.

## Đánh đổi player và keeper đúng

Player2557GT:2337giữ đúng,122mất đúng,55nhận thêm,43vẫn sai; TP2459→2392 mất ròng67. Trong122lost:52GTplayer được ghépkeeper,55ghépref,15missed. 73/122vẫn có player boxIoU>=0.5 trong tập survivor, nên mất TP theo matching không đồng nghĩa người biến mất khỏi detection. Một số GTplayer còn có cờ rolekeeper ở trên.

Keeper92GT:45giữ đúng,5mất đúng,23nhận thêm,19vẫn sai; TP50→68. Confusion GTplayer→keeper7→58,GTref→keeper0→5; unmatched keeper42→47. Ba phần tăng51+5+5 giải thích tăng ròng61FPkeeper. PlayerFP437→365 đồng thời mất TP, không đủ để đề xuất một policy chỉ tối ưu keeper/ref mà bỏ player.

## Artifact, tái hiện và kiểm thử

`data/processed/role_error_audit_v14/`:predictions.json,result.json,summary.json,audit.csv,reviewed-audit.csv,110+49+292crop,ảnh context toàn cảnh,25sheet crop và21sheet context biên xa. Review CSV có đường dẫn ảnh gốc,index GT/pred,box/score,v11/v14,transition,size,nhóm thị giác,cờ nhãn và ảnh chứng minh. Ảnh/weights/video không commit. Không sao chép val vào train.

Audit result SHA256:`3ddd2b70eff072b1ec311a16a98dab642f84df448c0030c4c2b038f8c698de56`.
Prediction cache SHA256:`cb251880d165f837c7182d4243c35507d278709d000df9ae14face0a7839dfde`.
Review fixture SHA256:`c1aa7d78a32b906474d6079202c6809d82f9f28b128ff1373ec794cb505ecedd`.

Fixture:role_error_audit_review_v14.json và role_error_audit_summary_v14.json. `validate_review` bắt buộc đủ mọi case cũ/mới/ref và giữ nguyên mọi evidence gốc, không cho đổi box/score/index/raw/transition/threshold hoặc tự nhận nghiệm thu độc lập.

```powershell
.\.venv\Scripts\python.exe -m backend.cv.audit_role_errors_v14 collect
.\.venv\Scripts\python.exe -m backend.cv.audit_role_errors_v14 summarize
.\.venv\Scripts\python.exe -m pytest -q tests/test_role_errors_v14.py tests/test_role_errors_v11.py --basetemp .tmp/pytest_role_error_v14_target
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_role_error_v14_full
```

Collect đã chạy một lần; từ chối khi đích tồn tại, không dùng để chạy lại inference lúc cache đã đủ. Summarize replay và xác thực cache/hash/evidence hoàn toàn offline, không inference. Ảnh review/board được tạo từ ảnh nguồn; phân loại thủ công lưu trong fixture, không detector tạo nhãn. Lượt summarize thứ hai cho summary byte-identical sẽ được kiểm trước commit.

6test mới;11test đích (v11/v14) đạt. Toàn bộ **625passed,1networkdeselected,4warning cũ** (Starlette/SHAP). Test chặn đổi score/box/transition/index, thiếu coverage49oldFP/110currentFP/292GT, sai threshold/claim, split test/heldout/duplicate và replay sai bất kỳ lớp nào.

## Bước tiếp dựa trên bằng chứng

Ưu tiên nghiệm thu độc lập5case nhãn nghi vấn và bộ thuộc tính vị trí; mọi sửa nhãn nếu được duyệt cần version/gate riêng. Sau đó rà lại độ phủ train theo parent cho player↔keeper và referee tối biên xa, dùng nguồn train ngoài val/test; không lấy những crop lỗi này đưa vào train.

48/50lost biên xa có score đúng dưới0.25 và tăng FPkeeper chủ yếu quanh người: riêng lọc nền hoặc dedup không giải quyết đủ cả hai. Chưa có cơ sở đổi NMS, giảm threshold, tăng repeats/epoch hay thay model ứng dụng. Thiết kế một thay đổi đơn lẻ và khóa thử nghiệm tiếp theo sau nghiệm thu; chưa thực hiện ở phiên này.

Một seed,nhãn agent và các ảnh/crop tương quan. Audit xác nhận cơ chế tại inference/scoring và thay đổi trên GTcố định; không chứng minh dữ liệu mới, ROI âm hoặc một tham số gây ra hồi quy. Gate v14 vẫn chưa đạt; giữ ứng dụng hiện tại.

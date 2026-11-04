# Xử lý khung trùng vai trò ngoại tuyến trên v11

Ngày04/11/2026. Không train thêm, không sửa nhãn/ngưỡng và không thay model ứng dụng.

## Phép thử đã khóa

Dùng nguyên `suppress_cross_role` đã thử với v6: sau NMS phân lớp gốc, xét confidence giảm dần, tie theo thứ tự đầu vào. Khi khác vai trò và IoU>0.7, bỏ khung điểm thấp hơn; không ưu tiên keeper/ref. Giữ khung cùng lớp, không loại dây chuyền, trả survivor về thứ tự gốc trước matching. Không sweep hoặc chỉnh policy theo kết quả.

Weights small v11 SHA256 `d576a3aceb80bc0a9f797da9b4d4bdba36995c2ea4203eed786ac7c63b89be72`; protocol `docs/fixtures/offline_role_dedup_protocol_v11.json`, SHA256 `cd5a0a63653ea6b33b924e1a89bf97ff6881c474e615fafa876e5285221d70af`. 128 val và35 ảnh hồi quy cũ ở640/1280, conf0.25/NMS0.7/matchingIoU0.5/max_det300,FP32. Không inference match128057. Khóa kết quả val trước known test; test đã xem từ trước, không phải kiểm mù.

Đối chiếu trước lọc khớp đầy đủ TP/FP/FN, confusion và unmatched của cả ba lớp với snapshot v11. Pred1280 val còn khớp chính xác từng box/score/thứ tự với audit trước. Đây là phép chấm cố định sau lọc, không tính lại AP hoặc đổi gate.

## Validation:128 ảnh

| Size | Vai trò | TP trước→sau | FP trước→sau | FN trước→sau | Precision trước→sau | Recall trước→sau |
|---|---|---|---|---|---|---|
| 640 | player | 2184→2183 | 446→386 | 373→374 | 83.04%→84.97% | 85.41%→85.37% |
| 640 | goalkeeper | 66→66 | 18→15 | 26→26 | 78.57%→81.48% | 71.74%→71.74% |
| 640 | referee | 46→47 | 310→257 | 246→245 | 12.92%→15.46% | 15.75%→16.10% |
| 1280 | player | 2459→2475 | 437→339 | 98→82 | 84.91%→87.95% | 96.17%→96.79% |
| 1280 | goalkeeper | 50→55 | 49→29 | 42→37 | 50.51%→65.48% | 54.35%→59.78% |
| 1280 | referee | 143→139 | 230→140 | 149→153 | 38.34%→49.82% | 48.97%→47.60% |

| Size | Vai trò | Giữ TP | Mất TP | Nhận đúng thêm | Vẫn sai |
|---|---|---|---|---|---|
| 640 | player | 2156 | 28 | 27 | 346 |
| 640 | goalkeeper | 65 | 1 | 1 | 25 |
| 640 | referee | 42 | 4 | 5 | 241 |
| 1280 | player | 2442 | 17 | 33 | 65 |
| 1280 | goalkeeper | 50 | 0 | 5 | 37 |
| 1280 | referee | 128 | 15 | 11 | 138 |

## Bộ hồi quy cũ:35 ảnh

| Size | Vai trò | TP trước→sau | FP trước→sau | FN trước→sau | Precision trước→sau | Recall trước→sau |
|---|---|---|---|---|---|---|
| 640 | player | 676→677 | 138→137 | 19→18 | 83.05%→83.17% | 97.27%→97.41% |
| 640 | goalkeeper | 6→6 | 4→3 | 6→6 | 60.00%→66.67% | 50.00%→50.00% |
| 640 | referee | 12→11 | 5→3 | 64→65 | 70.59%→78.57% | 15.79%→14.47% |
| 1280 | player | 686→686 | 93→83 | 9→9 | 88.06%→89.21% | 98.71%→98.71% |
| 1280 | goalkeeper | 5→5 | 3→3 | 7→7 | 62.50%→62.50% | 41.67%→41.67% |
| 1280 | referee | 39→39 | 43→33 | 37→37 | 47.56%→54.17% | 51.32%→51.32% |

| Size | Vai trò | Giữ TP | Mất TP | Nhận đúng thêm | Vẫn sai |
|---|---|---|---|---|---|
| 640 | player | 676 | 0 | 1 | 18 |
| 640 | goalkeeper | 6 | 0 | 0 | 6 |
| 640 | referee | 11 | 1 | 0 | 64 |
| 1280 | player | 685 | 1 | 1 | 8 |
| 1280 | goalkeeper | 5 | 0 | 0 | 7 |
| 1280 | referee | 36 | 3 | 3 | 34 |

## Khung bị loại và đối chiếu từng nhãn

| Bộ | Size | Khung bị loại | Player→ref trước→sau |
|---|---|---|---|
| val | 640 | 116 | 245→246 |
| val | 1280 | 191 | 57→42 |
| test | 640 | 4 | 2→1 |
| test | 1280 | 20 | 4→4 |

Tổng70 lượt mấtTP qua hai size/hai split:69 prediction đúng bị lọc,1 prediction đúng vẫn giữ nhưng đổi GT được ghép khi matching chạy lại. Không gọi70lượt là70người. Đã xem cả70 crop ngữ cảnh; không tuyên bố rà toàn bộ suppression event hoặc mọi cặp overlap là cùng người.

Case review41 (val1280) cho thấy khung player đúng vẫn còn, nhưng được ghép sang GT khác sau lọc; packet lưu ID/box hai nhãn. Matching gốc không sửa. Phần lớn crop mất TP còn lại có hai vai trò chồng quanh cùng vùng người: giữ score cao hơn không đảm bảo giữ đúng vai trò; không ép trường hợp chồng người thành duplicate thật.

## 49 FP keeper và50 lỗi ref biên xa đã rà trước

Trong49 FP keeper val1280 ban đầu:15 bị loại,5 trở thành TP nhờ bỏ box cạnh tranh,29 vẫn FP. Không có mất TP keeper trên val1280, nhưng ở640 có1mất/1được bù nên TP tổng giữ nguyên.

29FP còn lại gồm8cầu thủ sân,1GTkeeper có khung cạnh tranh,7người ngoài sân,6đèn,2cột gôn,1cờ góc,3bóng,1vật mờ sau gôn. Lọc khung chồng vai trò không loại được vật thể chỉ có một prediction; không phải cách thay thế kiểm sân hoặc dữ liệu âm khó. Các lớp hình ảnh dựa trên packet agent review trước, chưa kiểm độc lập.

Trong50nhãn ref biên xa còn sai đã rà: **0 được sửa đúng** bởi policy tại1280. Các11ref nhận đúng thêm ởval1280 thuộc các nhãn khác; không lấy cải thiện tổng để nói đã giải quyết nhóm biên xa. Val1280 còn mất15refTP, nhận thêm11, ròng143→139.

## Kết luận

Policy giảmFP nhưng không cải thiện đồng đều ba lớp. Val1280 keeper precision50.51%→65.48%,ref38.34%→49.82%; đổi lại ref recall48.97%→47.60%. Val640 playerTP giảm1,keeper giữ tổngTP nhưng có1case mất,ref tăng1; known test640 refTP12→11. Known test1280 TP tổng mỗi lớp giữ nguyên vẫn có1player và3ref mất được bù bởi số nhận đúng thêm tương ứng.

**Chưa phù hợp áp dụng toàn cục; giữ runtime hiện tại.** Không đổi threshold/gate hoặc ưu tiên vai trò để bù số. Confidence giữa các lớp chưa được kiểm chứng là so sánh/cân chuẩn tốt. Không dùng bộ hồi quy để lựa chọn phiên bản policy.

## Kiểm tra và artifact

```powershell
.venv/Scripts/python.exe -m backend.cv.offline_role_dedup_v11
.venv/Scripts/python.exe -m pytest tests/test_offline_role_dedup.py tests/test_offline_role_dedup_v11.py -q --basetemp .tmp/pytest_dedup_v11
```

Lệnh yêu cầu output chưa tồn tại. 9test đích đạt,596test toàn bộ đạt,1networkdeselected,4warningcũ. Kiểm dataset/weights và codepolicy bằng hash trước/sau. Chỉ thêm runner ngoại tuyến, test và tài liệu; DATA_CONTRACT/API/frontend/model ứng dụng không đổi.

Output local `data/processed/offline_role_dedup_v11`: protocol-before-run, validation-before-test, result, predictions, label-changes và suppression-events. Review có4sheet/70crop các TP mất. Fixtures `offline_role_dedup_v11.json` và `offline_role_dedup_review_v11.json` giữ số liệu, toàn bộ70mất TP, hành động trên49FP và hash bằng chứng.

## Bước tiếp theo

Chuẩn bị nguồn train khác bối cảnh có âm khó (đèn/cột/cờ, người ngoài sân) và nhãn đủ người trong toàn cảnh, kèm keeper đứng xa xanh/sáng và ref tối biên xa. Kiểm nguồn, split và nhãn trước khi chốt sampling; không đưa ảnh val/test đang rà vào train. Chưa train lại hoặc nới lọc theo điểm.

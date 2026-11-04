# Rà lỗi thủ môn và trọng tài v11 tại 1280

Ngày 04/11/2026. Chỉ inference trên 128 ảnh validation, đối chiếu v10/v11.
Giữ confidence0.25, NMS0.7, matching IoU0.5, max_det300, FP32; không đổi
labels, weights, phép chấm hoặc model ứng dụng. Không inference known test
hay match128057. Kiểm hash bảo vệ vẫn thực hiện trên manifest toàn bộ.

## Kết luận

V11 giảm bỏ sót so với v10 nhưng phát sinh nhiều loại lỗi khác nhau:
nhầm cầu thủ thành thủ môn, khung nhiều vai trò quanh cùng người, người
ngoài sân và vật thể nền. Với trọng tài biên xa, điểm lớp thấp vẫn là
nhóm lớn nhất. Không có căn cứ coi toàn bộ lỗi là thiếu keeper xanh nhỏ
hoặc chỉ là NMS, và chưa có thí nghiệm tách nguyên nhân từ dữ liệu train.

## 49 FP thủ môn là những gì?

FP ở đây theo **nhãn và bộ ghép đã khóa**, chưa phải kết luận thủ công rằng
mọi khung đều chỉ nhầm người. Tái hiện đủ TP/FP/FN và confusion cả ba lớp.

- V10 có21 FP; v11 có49 FP. Ghép không gian IoU0.5 giữa hai tập FP:
  **9 còn lại, 40 mới xuất hiện, 12 cũ hết**. Chênh lệch28 là mức tăng ròng,
  không phải tổng số lỗi mới. Đây là liên hệ khung ảnh, không phải ID người.
- 7 khung keeper được ghép vào GT player; 17 khung không được ghép vì GT
  tương ứng đã thuộc một prediction khác; 25 khung không có GT IoU>=0.5.
- Trong17 khung cạnh tranh GT:9 quanh GT keeper,8 quanh GT player. Có8/9
  khung quanh keeper đi kèm box player;1 đi kèm keeper khác. Vì vậy có
  keeper đúng về người/vai trò vẫn bị tính FP do một box khác được ghép trước.

Rà toàn bộ49 crop, thêm ảnh native cho các cấu trúc/người khó phân biệt:

| Đối tượng nhìn thấy | Số khung FP | Trong đó mới xuất hiện |
|---|---:|---:|
| Cầu thủ sân, kể cả chồng người |19|14|
| GT keeper có box cạnh tranh |9|8|
| Người ngoài sân, chưa khẳng định staff/ballboy/vai trò cụ thể |8|6|
| Đèn sân |6|6|
| Cột gôn |2|2|
| Cờ góc |1|1|
| Bóng |3|2|
| Vật thể mờ vùng sau gôn, chưa chắc |1|1|

`keeper-45` giữ unknown vì ảnh mờ; không ép thành lớp nền cụ thể.
Các người ngoài sân trong tập val không tự động trở thành dữ liệu train.
Không lấy các ảnh/box val này làm hard negatives huấn luyện.

Ví dụ có thể xem trong thư mục audit local: `keeper-10` là đèn sân,
`keeper-2/21` cột gôn, `keeper-16` cờ góc, `keeper-30/42` bóng,
`keeper-13` người mặc bib phía ngoài sân. `keeper-7/12/47` có GT keeper
nhưng box player trùng quanh người được ghép trước. Giữ nguyên điểm số cũ.

## 149 FN trọng tài còn lại

Trong292 nhãn ref: **75 giữ nhận đúng, 68 nhận đúng thêm, 26 mất nhận đúng,
123 vẫn sai**. TP101→143; số149 FN gồm26 mất và123 vẫn sai, không phải149
lỗi mới. 99 FN đang ghép thành player,50 không có prediction được ghép.

Rà cả149 crop/context; phân vị trí theo đường biên và bối cảnh, không chỉ
dựa vào tọa độ y. Mọi candidate biên xa được xem thêm khung hình rộng:

- 50 biên xa,90 giữa sân,8 biên gần;1 cạnh khu kỹ thuật chưa chắc vai trò.
- Cả50 biên xa có chiều cao box dưới24px khi thu cạnh dài về640.
  Trong50 này:42 vẫn sai từ v10,8 là mất nhận đúng; không có mẫu số tổng
  ref biên xa để gọi đây là recall của nhóm hoặc số người/trận độc lập.
- Các ref biên xa nhìn như áo tối; có1 ref biên gần áo cam trong tập149.
- `referee-60`, ảnh `538438_3_10...1130754d...`, GT index6: người mặc
  tracksuit ở khu kỹ thuật, chưa đủ căn cứ staff/official từ ảnh tĩnh.
  Chỉ gắn cờ, giữ GT và phép chấm; không loại case này để làm đẹp số liệu.

Chẩn đoán điểm lớp trước argmax/NMS và khung còn sau xử lý:

| Bằng chứng trực tiếp | Toàn bộ149 FN | Trong50 biên xa |
|---|---:|---:|
| Điểm ref cao nhất quanh GT vẫn dưới0.25 |107|44|
| Có box ref IoU>=0.5 nhưng bị cạnh tranh khi ghép |31|3|
| Điểm ref đạt0.25 nhưng thua lớp khác khi argmax |8|0|
| Không có raw box IoU>=0.5 |2|2|
| Raw ref thắng lớp nhưng mất trước matching |1|1|

Các nhóm được phân theo thứ tự ưu tiên chẩn đoán; có khung đúng vai trò
không có nghĩa prediction được ghép cho GT. Raw score không phải xác suất
dự đoán đúng, và bằng chứng giai đoạn inference không chỉ ra quan hệ nhân
quả riêng của năm ảnh mới hoặc một nhãn train đã sửa.

### Một case sát ranh giới localization/NMS

`referee-105`, GT index21 trong ảnh `798b45_3_4...f5ce0ffb...`:
raw ref score0.7992, IoU GT0.5283; một raw ref khác score0.9419 có IoU
với box này0.8953 nên được NMS giữ, nhưng IoU GT chỉ0.4781. Raw ref
score0.4680, IoU GT0.5081 cũng bị box score cao hơn chèn. Replay trực tiếp
predictor preprocess→inference→postprocess khớp predict chuẩn từng box,
class và score. Đây là tương tác vị trí box và ngưỡng matching, chưa phải
lý do đổi NMS hoặc giảm ngưỡng toàn cục. Giữ nguyên cách tính FN.

## Bằng chứng và kiểm tra

- Code: `backend/cv/audit_role_errors_v11.py`;5 test chặn sai cách đếm FP,
  cạnh tranh GT, nhầm tăng ròng thành lỗi mới và sửa/rút gọn review.
- Fixtures: `role_error_audit_review_v11.json` chứa đủ49 FP/149 FN,
  geometry/hash/score/nhãn/bối cảnh và quyết định review;
  `role_error_audit_summary_v11.json` giữ thống kê và replay ba lớp.
- Audit local: `data/processed/role_error_audit_v11` có predictions,
  result,11 contact sheets lỗi, các full-context/native crops và NMS proof.
- Tái hiện chính xác TP/FP/FN, confusion và unmatched predictions của
  v10/v11 trên val1280. Dataset và weights kiểm hash trước/sau audit.
- Review do agent thực hiện, chưa kiểm chứng độc lập. Các phân loại hình
  ảnh này không sửa GT hoặc được coi là nhãn đánh giá mới.
- 593 test toàn bộ đạt,1 network deselected,4 warning cũ;5 test đích đạt.

```powershell
.venv/Scripts/python.exe -m backend.cv.audit_role_errors_v11
.venv/Scripts/python.exe -m pytest tests/test_role_errors_v11.py -q --basetemp .tmp/pytest_audit_v11
```

Lệnh audit yêu cầu thư mục đích chưa tồn tại, không ghi đè bản đã xuất.
Review có thể xác thực bằng `validate_review(audit, review)` sau kiểm
SHA256 result theo packet. Chỉ đọc snapshot JSON khi rà lại, không cần
chạy GPU lặp để đổi cách phân loại thủ công.

## Bước tiếp theo

Thử chính sách xử lý khung trùng vai trò **ngoại tuyến trên v11** trước,
giữ nguyên GT và phép chấm, báo đủ ba lớp ở640/1280. V11 có nhiều case
keeper/ref cạnh tranh với box player nên cần đo trực tiếp, không suy từ
kết quả dedup v6. Không tự đưa policy vào runtime. Sau đó mới chọn nguồn
train khác bối cảnh cho người/đèn/cột/cờ và keeper đứng xa nếu còn lỗi;
không sao chép val/test vào train, chưa tăng epoch hoặc train tiếp.

Lần thử v6 từng giảm ref TP91→81 ở1280 dù FP giảm. Vì thế phép thử v11
phải báo rõ mọi mất TP và người đứng chồng nhau; không mặc định bỏ khung
thấp điểm hơn sẽ giữ đúng vai trò.

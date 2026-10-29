# Kiểm chứng chuỗi bóng và sự kiện — 29/10/2026

Đây là rà phát triển do cùng agent làm, không phải đánh giá độc lập.
Agent đã thấy ứng viên8–9,53s trước đó; không gọi mẫu này là blinded
hoặc held-out. Nhãn dựa trên ảnh gốc không có detector overlay, vẫn
cần người rà độc lập trước nghiệm thu. Không đổi DATA_CONTRACT/thư viện.

## Mẫu và quy tắc

Nguồn Video Project15, job `c140f8aefb4e4678b51fe6f633e1fc56`.
Protocol và nhãn ở `docs/fixtures/ball_video15_validation_protocol_v1.json`
và `ball_video15_agent_review_v1.json`.

- Ảnh gốc toàn clip lấy mỗi0,5s, crop cùng vùng y400–1060 mỗi0,2s
  trong7–10s,19–22s,30–33s,44–47s. Không chọn crop theo vị trí dự đoán.
- Nhãn vị trí:30 mẫu theo lịch cố định ở7–10s và19–22s;24 nhìn rõ,
  6 không chắc do chạm chân/che khuất. Không bỏ mẫu khỏi lịch để tăng điểm.
- Dung sai điểm12px, khóa trước so sánh. Mất dự đoán là miss; điểm sai
  vừa là FP vừa là FN; mẫu không chắc không được tính là đúng.
- Sự kiện chỉ trong7–10s,19–22s,30–34s,49–52s (13s tổng). Đã kéo đoạn
  30–33s thành30–34s trước scoring để không cắt mất lần nhận bóng.
- Bốn chuyển bóng cùng nhóm màu được agent đánh dấu; ghép một-một,
  cùng lớp/nhóm áo và lệch đầu/cuối mỗi mốc tối đa0,5s. Không đếm hai
  dự đoán cho cùng một nhãn; tách hai đường chuyền liền nhau ở7–10s.
- Đoạn44–47s sát biên chưa chắc nhận bóng trong sân, không chấm như
  đường chuyền hoàn tất hoặc mẫu âm. Không kiểm chứng danh tính người
  chuyền/nhận từ mốc thời gian đơn thuần.

## Kết quả và nguyên nhân

| Chẩn đoán nhỏ trên mẫu | Kết quả |
|---|---|
| Vị trí bóng trong12px | 20/24 mẫu nhìn rõ;4 thiếu dự đoán,6 không chắc bỏ qua |
| Sai lệch trung vị/cao nhất khi có dự đoán | 1,94/8,61px |
| Ghép thời gian đường chuyền | 1/4;3 bị bỏ sót,0 ứng viên thừa trong phạm vi rà |
| Recall/F1 chuyền trên mẫu | 0,25/0,40; không đại diện toàn video |
| Nhận diện sút | Chưa triển khai, precision/recall/F1 giữ null |

Ba lần bỏ sót ở khoảng7,1–7,8s,19,5–21,2s và32,3–33,2s đều có mất
chuỗi bóng tại chân/tranh chấp hoặc thiếu hỗ trợ trước/sau chuyền.
Không nối qua mất dấu dài để ép tạo sự kiện. Chuyền32,3s về phía hậu
vệ/sân nhà là mẫu âm cho suy luận "bóng hướng cầu môn trong ảnh = sút".
Khoảng49–52s cầu thủ ngã/trợ lý phất cờ cũng không tự thành cú sút.

Thử crop detector quanh chân gần vị trí bóng vừa quan sát, tối đa2crop/
frame, không lấy vị trí dự đoán xuyên quá0,15s hoặc chuyển cảnh. Chạy
toàn1571 frame:1691 lượt crop, chỉ1 proposal mới; kết quả điểm/chuyền
không cải thiện. Giữ thành thí nghiệm ngoại tuyến, không bật trong
upload/web. Không đổi trọng số hoặc nới ngưỡng để tăng chỉ số mẫu.
Artifact: `data/processed/ball_contact_refinement_video15_v1/`;
baseline/raw review: `data/processed/ball_validation_video15_v1/`.

## Cú sút: nguồn khác, giữ riêng

Rà các file sẵn có tìm được một pha có khả năng cao là cú sút trong
**Video Project15 (1).mp4**, nguồn SHA256
`11a9b033dbeca46af7e3cf1117269b04044ddf8d89b6c594efc16222606dd053`.
Ảnh cách0,1s cho thấy cầu thủ trắng vung chân khoảng30,5–30,7s, bóng
hướng cầu môn trái, thủ môn phản ứng/đổ người sau đó. Nhãn phát triển
lưu `shot_video15_part1_agent_review_v1.json`; kết quả pha bóng để
uncertain. Không cộng vào clip15 mẫu, không suy xG hoặc chiếu bóng bay
thành điểm mặt sân. Một pha này chưa đủ chia train/test cho mô hình sút.
Khảo sát clip15(2) chỉ là rà nguồn, không khẳng định không có cú sút.

## Tái tạo và giao diện

```powershell
.\.venv\Scripts\python.exe -m backend.cv.evaluate_ball_sequence data/processed/video_jobs/c140f8aefb4e4678b51fe6f633e1fc56/ball_research docs/fixtures/ball_video15_validation_protocol_v1.json docs/fixtures/ball_video15_agent_review_v1.json data/processed/ball_validation_video15_new.json
.\.venv\Scripts\python.exe -m backend.cv.ball_sequence data/processed/video_jobs/c140f8aefb4e4678b51fe6f633e1fc56 data/processed/ball_contact_refinement_video15_new --replay data/processed/video_jobs/c140f8aefb4e4678b51fe6f633e1fc56/ball_research --contact-crops
```

Audit lưu hash protocol/nhãn/report/JSONL. API ball-events chỉ đọc audit
`ball_research/validation.json` khi hash nguồn/job/prediction/chuỗi khớp;
không cho audit cũ ghép vào dự đoán mới. Web hiện20/24 và1/4 cùng cảnh
báo mẫu phát triển, có nút tua ba đường chuyền bị bỏ sót. Tổng chuyền/sút
production vẫn null. Đây là báo cáo chất lượng, không nâng nhãn thủ công
thành sự kiện được AI tự nhận diện.
Đã bấm thẻ bỏ sót thứ3 trên trình duyệt, tua31,8s và pause đúng trước
pha chuyền trắng; ảnh `data/processed/live_demo_v1/15-ball-pass-validation.jpg`.

339 test Python qua/1 network deselected;14 test frontend qua;
build/lint qua với cảnh báo cũ. Test mới kiểm tra sai nguồn, mẫu thiếu,
điểm sai/mất/không chắc, absent, duplicate và ghép sự kiện một-một,
tách pass/shot, thiếu triển khai sút, hash audit và crop không nội suy.

Việc tiếp: thêm nhãn bóng/tiếp xúc dày quanh các đoạn mất dấu, dữ liệu
cú sút dương tính và mẫu âm khó từ nhiều pha/trận, tách nhóm train/
validation/test trước huấn luyện, đánh giá độc lập trước bật đếm tự động.

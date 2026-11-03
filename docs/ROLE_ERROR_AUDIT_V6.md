# Rà lỗi small v6

Ngày03/11/2026: chạy lại v1/v6 trên128ảnh validation đã khóa, cùng
imgsz640,conf0,25,NMSIoU0,7,ghép vị trí IoU0,5. Không train, không
đổi ngưỡng/nhãn hoặc model ứng dụng. Tái lập đúng757vs409lỗi player
bị gọi referee và229FNreferee/42FNkeeper của snapshot huấn luyện.

## Đối chiếu từng đối tượng

| Nhóm | Số lượt | Cao dưới24px ở640 |
|---|---:|---:|
| Player→referee tồn tại ở cảv1/v6 |357|327|
| Player→referee mới ởv6 |52|45|
| Hết gọi referee ởv6 |400|259|
| Referee bị gọi sai hoặc không ghép được |229|196|
| Keeper bị gọi sai hoặc không ghép được |42|42|

357+52=409lỗi hiện tại;357+400=757lỗi cũ. V6 chuyển389/400trường hợp
hết nhầm thành player đúng,4thànhkeeper,7bỏsót. Vì vậy chỉ389trường
hợp là sửa đúng vai trò, không gộp cả400vào số sửa đúng.

372/409=91,0%player bị gọi referee cao dưới24px;37còn lại24–48px.
Các lỗi này nằm ở4prefix val:4b770a123,538438173,798b4589,cd987c24.
Đây là lượt quan sát trên frame có thể lặp người, không409người/trận
khác nhau. Chưa suy màu áo của toàn409lượt chỉ từ mẫu xem.

229FNreferee gồm130bị gọi player và99không có ghép dự đoán hợp lệ.
42FNkeeper gồm32bị gọi player và10không ghép được. “Không ghép được”
có thể là bỏ sót,định vị không đủIoU hoặc thấp ngưỡng, không xác định
nguyên nhân chỉ bằng số đếm. Toàn42keeper lỗi dưới24px.

FPreferee tổng511theo nhãn đã khóa:409lần ghép nhầm player và102dự
đoán referee không ghép nhãn nào. Chưa rà trực quan102dự đoán thừa,
không tự kết luận tất cả là nền thật hay nhãn bỏ sót. Không thay FP/FN
gốc theo quan sát chưa được kiểm chứng.

## Rà100mẫu ảnh

Lấy20mẫu cách đều theo tênảnh/ID ở mỗi5nhóm, không phải lấy ngẫu nhiên
để ước lượng tỷ lệ tổng thể. Xem5contact sheets và ảnh toàn cảnh của
mẫu61.60mẫu player đều cho thấy cầu thủ áo vàng, thường mờ/nhỏ hoặc
có người lân cận; mẫu ref chủ yếu áo đen, có trợ lý cầm cờ; mẫu keeper
có nhiều màu áo và thường gần khung thành. Đây là quan sát của agent,
chưa có người rà độc lập.

Mẫu61: nhãn referee ởảnh
`4b770a_1_7_png.rf.0344c0dc64e2361671483c067c0bc549.png`,label_id21,
có trọng tài đen chồng lên cầu thủ đỏ. V6 ghép thànhplayer,confidence
0,742. Đưa vào hàng đợi rà bbox/đối tượng vì attribution chưa rõ;
không kết luận nhãn sai hoặc đổi protected label. Các mẫu khác cũng
không chứng minh toàn bộ nhãn validation sạch.

Người nhỏ là dấu hiệu chung mạnh, chưa chứng minh causal nguyên nhân
hoặc model chỉ dựa vào màu. Vai trò referee/keeper bị gọi player cho
thấy giảm nhầm áo vàng chưa đồng nghĩa giải quyết đủ3vai trò. Ngưỡng
confidence đơn lẻ không giải quyết được định danh vai trò khi che nhau.

## Artifact và nghiệm thu

```powershell
.\.venv\Scripts\python.exe -m backend.cv.audit_role_errors_v6
.\.venv\Scripts\python.exe -m pytest tests/test_role_balance.py tests/test_full_frame_roles.py -q --basetemp .tmp/pytest_role_error_audit_v6
```

Script khóa hash dataset/weights/mapping, kiểm tổng nhầm player và
FNtừngvai trò khớp snapshot; từ chối ghi đè thư mục kết quả. Full audit,
100crop và5sheet local `data/processed/role_error_audit_v6_review`.
Snapshot `docs/fixtures/role_error_audit_v6.json` chứa100mẫu,đếm lỗi,
size bins và reviewqueue.23test matching/ROI/gate liên quan đạt.

## Bước tiếp theo

Ưu tiên phép thử cùng weightsv6 ởimgsz1280 trên đúng tập kiểm để xem
người nhỏ có được nhận tốt hơn, giữconf/matching như cũ, báo cả FP/FN
và tốc độ/VRAM. Đây là đánh giá độ phân giải, chưa cần train lại hoặc
triển khai. Đồng thời rà riêng102referee không ghép nhãn và trường
hợp chồng người; mọi sửa nhãn cần phiên bản mới, giữ baseline đánh
giá cũ để đối chiếu. Chưa chuyển sang hiệu chỉnh sân với giả định
phân vai trò đã đạt chuẩn.

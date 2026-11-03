# Bổ sung train toàn cảnh, giữ người nhỏ

Ngày03/11/2026: đã rà và xuất gói đầu tiên gồm3ảnh nguyên khung,
60bbox:52player,4goalkeeper,4referee. 41người cao dưới24px khi quy640,
18người24–48px,1người từ48px. Không bỏ bbox nhỏ hoặc phóng crop thay
ảnh toàn cảnh; bytes JPEG nguồn được giữ nguyên. Chưa train v4.

## Phạm vi nhãn

Đã xem toàn cảnh và các crop đánh số của gFCS,k13,k84. Gán vai trò
tất cả đối tượng thi đấu và trọng tài nhìn thấy, gồm thủ môn, người nằm,
người che nhau và trọng tài biên. Khán giả/nhân viên/người dự bị ngoài
cuộc chơi không phải lớp player. Đây là chính sách nhãn ngữ nghĩa,
không thay quy tắc lọc người ngoài đường biên của ứng dụng.

| Frame | Player | Thủ môn | Trọng tài | Ghi chú |
|---|---:|---:|---:|---|
| gFCS | 14 | 1 | 1 | Cầu thủ vàng/xanh sẫm, trọng tài hồng |
| k13 | 20 | 2 | 2 | Toàn sân, nhiều người rất nhỏ |
| k84 | 18 | 1 | 1 | Góc rộng GER–FRA, trọng tài áo tối |

Agent rà dựa trên ảnh và bbox nguồn, không có người kiểm độc lập.
Đây là pilot nhỏ, chưa đủ để kết luận hiệu quả tổng quát. gFCS/k13 đã
có ROI trong v3; chuyển sang toàn ảnh không tạo người/trận mới. k84
trước đây là scout, chưa dùng train. Khi ghép dataset sau cần kiểm soát
trọng số để tránh vô tình tính cả ROI lẫn full-frame thành nguồn độc lập.

## Đính chính chất lượng nguồn trước

Khi xem lại toàn cảnh các ảnh Villarreal (g30,g49,g54,g63,g90,g192),
có dấu hiệu đồ họa mô phỏng ở người và khán đài. Chưa xác minh nguồn
video, nên tuyên bố trước đây `real_match_broadcast` cho nhóm này
không đáng tin cậy. Cách ghi trong báo cáo/packet v3 trước đó cần đọc
kèm đính chính này. Không nhận các ảnh đó vào gói toàn cảnh mới.
V3 đã train ROI của nhóm này: phải coi dữ liệu của thí nghiệm v3 có
media chưa xác minh, không dùng kết quả để chứng minh model chỉ học
ảnh trận thật. Runtime vốn chưa dùng weights v3.

Không sửa lịch sử packet/hashes hoặc weights thí nghiệm cũ. Packet mới
có danh sách quarantine. k0/k63/k105 chưa giải quyết hết đối tượng
chồng nhau/xa nên cũng chưa xuất toàn ảnh, tránh biến người chưa rõ
thành background. Gói này còn ít cầu thủ áo vàng và chưa đủ để thay
toàn bộ nhu cầu bổ sung cảnh thật đa dạng.

## Nguồn và bảo toàn tập kiểm

Giữ ghi công/CC BY4.0 và revision của hai nguồn trong packet:
[skaczylo Football-Image-Dataset](https://github.com/skaczylo/Football-Image-Dataset/tree/264212872f1bfa6a9a3413f298793474da741aec)
và [keremberke football-object-detection](https://huggingface.co/datasets/keremberke/football-object-detection/tree/788fb2722316ee7cad1ace2f6c94e563556a1d3e).
Chỉ dùng ảnh đã tải ở revision khóa; không truy cập phiên bản mới.
Vai trò nguồn gộp người/thủ môn đã được phân lại riêng.

Đã kiểm hash toàn bộ ảnh/nhãn dataset v3; sàng lọc3ảnh với163ảnh
val/test bằng dHash+thumbnail, không thấy ảnh gần trùng theo phép kiểm.
Không thay val/test. Đây không phải bằng chứng độc lập tách trận tuyệt
đối; danh tính trận chưa xác minh đầy đủ. Không chuyển ảnh tập kiểm
sang train hoặc coi ảnh đã có ROI là dữ liệu kiểm độc lập.

## Nghiệm thu

```powershell
.\.venv\Scripts\python.exe -m backend.cv.export_full_frame_roles
.\.venv\Scripts\python.exe -m pytest tests/test_full_frame_roles.py tests/test_role_counterexamples.py -q --basetemp .tmp/pytest_full_frame_roles_v4
```

23test đạt. Export từ chối ghi đè thư mục đã có. Dữ liệu cục bộ:
`data/processed/full_frame_roles_v4/images/train` và `labels/train`.
Packet `docs/fixtures/full_frame_roles_v4.json` khóa bbox, nguồn, vai trò;
snapshot `full_frame_roles_audit_v4.json` khóa hash ảnh/nhãn xuất và số
người nhỏ. Chưa ghép dataset train v4 hoặc tự chạy huấn luyện; gói chỉ
có train subset, không tạo validation/test giả. Không đổi API hoặc
DATA_CONTRACT.

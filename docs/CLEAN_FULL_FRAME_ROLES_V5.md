# Dataset toàn cảnh có cầu thủ vàng và kiểm chứng vai trò

Ngày03/11/2026: đã hoàn thành bản xuất v5 gồm7ảnh nguyên khung với115
nhãn:101player,6goalkeeper,8referee.43đối tượng cao dưới24px ởimgsz640,
71từ24–48px,1từ48px. Đây là tập train bổ sung nhỏ đã rà, chưa phải bộ
huấn luyện đủ đa dạng để nghiệm thu phân vai trò trên mọi video.

## Tuyển nguồn thật

Đã tải/screen276ảnh nhóm timestamp144746 ở revision
`264212872f1bfa6a9a3413f298793474da741aec` của
[skaczylo/Football-Image-Dataset](https://github.com/skaczylo/Football-Image-Dataset/tree/264212872f1bfa6a9a3413f298793474da741aec).
Giữ giấy phép/ghi công CC BY4.0 từ packet trước.188ảnh qua sàng lọc HSV
chỉ là ứng viên, không tự động có nhãn đúng hoặc được nhận vào train.
Không nhập cả276ảnh chưa rà vào dataset.

Nhận4ảnh mới đã xem toàn cảnh/bbox: new120(Libertadores, vàng/xanh
sẫm),new11/new140(LPA–LEG, cùng nhóm cảnh),new17(ESP–BEL nữ,vàng/đỏ).
Không nhầm nhóm Libertadores thành Saudi dựa trên màu áo.4ảnh bổ sung
55nhãn:49player,2keeper,4referee.2người dưới24px,53người24–48px.
Vai trò thủ môn được sửa riêng tại hai ảnh LPA–LEG; không để nguyên
lớp người tổng quát của nguồn. Người nằm và người cắt mép được giữ.

Cộng3ảnh đã rà ởv4 (gFCS,k13,k84) thành7ảnh. Không gọi7ảnh là7trận
độc lập hoặc115người khác nhau. gFCS/k13 đã có ROI trainv3. Chưa xác
minh độc lập danh tính/ngày trận; tên timestamp không phải ngày trận.
Rà bởi agent chưa có người kiểm độc lập.

Chính sách nhãn: tất cả cầu thủ/thủ môn/trọng tài nhìn thấy trong cuộc
chơi, gồm trọng tài biên; không gán khán giả,staff hoặc người dự bị
đứng ngoài cuộc chơi thành player. Không sửa bộ lọc ngoài biên runtime.
Giữ nguyên pixel JPEG và chuẩn hóa bbox theo toàn ảnh, không crop/phóng
người nhỏ. Gói này không chứa ROI của nhóm Villarreal nghi mô phỏng.

Loại new128 vì đúng ảnh gFCS cũ, không tính mới; quarantine new112 vì
bbox chồng chưa giải quyết. Không lấy cảnh Dortmund/Bayern vì có nguy
cơ cùng nhóm validation sân vàng, kể cả khi tên file khác. Các ảnh
Villarreal chưa xác minh vẫn bị quarantine; không nhập v3 trộn media
vào gói sạch này. “Sạch” chỉ nói phạm vi nguồn được nhận và rà trong
release này, không bảo đảm nhãn hoàn hảo hoặc đã xác minh trận độc lập.

## Bảo toàn và kiểm chứng

Exporter kiểm bytes ảnh/nhãn datasetv3 và giữ val128/test35; screen
7ảnh với163ảnh tập kiểm bằng thumbnail/dHash, không có near-image hit.
Đây là sàng lọc ảnh, không chứng minh tách trận tuyệt đối. Khóa hash
ảnh nhận, Gitblob hoặc thành viên archive nguồn, giấy phép và packet.

```powershell
.\.venv\Scripts\python.exe -m backend.cv.export_full_frame_roles --packet docs/fixtures/clean_full_frame_roles_v5.json --output data/processed/clean_full_frame_roles_v5
.\.venv\Scripts\python.exe -m backend.cv.diagnose_full_frame_roles
.\.venv\Scripts\python.exe -m pytest tests/test_full_frame_roles.py tests/test_role_counterexamples.py tests/test_role_balance.py -q --basetemp .tmp/pytest_clean_fullscene_v5
```

Exporter từ chối ghi đè output có sẵn.40test liên quan đạt.
Dataset cục bộ `data/processed/clean_full_frame_roles_v5` có ảnh/nhãn
train và manifest; packet/audit/diagnostic v5 trongdocs/fixtures.
Không tạo test giả từ3/7ảnh ít dữ liệu; không thay API hoặcDATA_CONTRACT.

## Kiểm chứng lại detector, không phải kết quả train mới

imgsz640,conf0,25,ghép theo vị trí IoU0,5 trên7ảnh:

| Kết quả | V1 | V3 |
|---|---:|---:|
| Player đúng /101 |83|85|
| Keeper đúng /6 |0|0|
| Referee đúng /8 |4|3|
| Player bị gọi referee |10|3|
| FP player theo nhãn |29|41|

V3 giảm nhầm player→referee nhưng FPplayer tăng và bỏ sót vai trò
keeper/referee còn lớn. Không đạt điều kiện dùng semantic detector để
chốt chiến thuật. Đây là chẩn đoán phát triển, gFCS/k13 có liên hệ train
v3; không dùng làm đánh giá độc lập hoặc tuyên bố hiệu quả dữ liệu mới.
Chưa train lại model trênv5. Runtime vẫn giữ cấu hình trước.

## Bước tiếp theo

Khóa protocol ghép tập train đã xác minh, quản lý lặp ROI/full-frame,
không warm-start từv3 trộn media nếu muốn đánh giá bộ sạch. Cần kiểm
tra nguồn của base corpus trước khi gọi toàn bộ dataset ghép là sạch;
release7ảnh này không tự chứng minh base212ảnh sạch. Sau đó mới train
small từ nguồn khởi tạo được chốt và so sánh trên bộ kiểm cũ; chỉ
chuyển ưu tiên sang hiệu chỉnh sân khi kiểm chứng vai trò đạt yêu cầu.

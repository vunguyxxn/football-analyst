# Rà lỗi phân vai trò v3

Ngày 03/11/2026: đối chiếu từng nhãn player trên 128 ảnh validation,
v1 và v3 cùng imgsz640, conf0,25, NMS IoU0,7, max_det300, ghép theo
vị trí IoU0,5. Đếm lại đúng tổng v1 757 và v3 801 lỗi player→referee.
Không huấn luyện hoặc sửa nhãn tập kiểm trong lần rà này.

| Nhóm so với v1 | Số lượt | Người cao dưới24px ở imgsz640 |
|---|---:|---:|
| Vẫn nhầm referee ở cả hai model | 654 | 530 |
| Mới nhầm referee ở v3 | 147 | 124 |
| Hết nhầm referee ở v3 | 103 | 56 |

Trong 147 lỗi mới, v1 từng nhận đúng player132 và bỏ sót15. Trong103
lượt hết nhầm referee, v3 nhận đúng player92, gọi goalkeeper5, bỏ sót6.
Vì vậy “hết gọi referee” không đồng nghĩa nhận đúng. 654+147=801;
654+103=757. 654/801=81,6% lỗi v3 là lỗi đã tồn tại ở baseline.
654/801 người trong nhóm lỗi v3 cao dưới24px (trùng số ngẫu nhiên với
số lỗi persistent); tỷ lệ81,6%. Còn147 người cao24–48px; không có người
cao từ48px trong nhóm lỗi v3 theo bbox nhãn.

## Rà hình ảnh

Xem60crop:20persistent,20introduced,20removed, lấy cách đều theo tên
ảnh và ID nhãn trong mỗi nhóm. Đây là mẫu mô tả có chủ đích, không là
mẫu ngẫu nhiên ước lượng tỷ lệ lỗi. Ảnh ngữ cảnh đệm35px, giữ cả người
lân cận; hình contact sheet là phóng to để xem, không thêm chi tiết gốc.

Cả60mẫu thể hiện cầu thủ áo vàng, nhiều người có số áo, đang chạy hoặc
đứng theo tình huống thi đấu. Không thấy bằng chứng trực quan cần đổi
nhãn player thành referee trong60mẫu này. Đây là rà bởi agent, chưa có
kiểm độc lập; không xác nhận toàn bộ2557nhãn hoặc801lỗi đều sạch.
Không suy màu áo của toàn bộ801người chỉ từ60mẫu.

Lỗi v3 phân bố ở4prefix val:4b770a242,538438295,798b45212,cd987c52.
Các nhóm này vốn thuộc nguồn sân/áo vàng được giữ chung ở validation;
không được chuyển sang train để làm đẹp kết quả.

## Nhận định và bước nên làm

Người nhỏ và màu áo vàng là dấu hiệu quan sát được, chưa phải chứng
minh cơ chế model. Mẫu ROI bổ sung có người chiếm phần lớn crop; khi
train640 chúng lớn hơn người trong ảnh toàn cảnh validation:39ROI
player mới có chiều cao chủ thể quy640 từ234đến420px, trung vị348px,
trong khi lỗi v3 đều dưới48px. Đây là so sánh hình học trước augmentation,
chưa tính mosaic/scale của quá trình train. Vì thế
thêm crop có thể chưa khắc phục đúng phân bố kích thước/ngữ cảnh.
Cần thử nghiệm có kiểm soát để kiểm chứng giả thuyết này.

Ưu tiên tiếp theo là tuyển nguồn train toàn cảnh mới có cầu thủ vàng
và trọng tài màu khác, gán nhãn đầy đủ người trong ảnh, bảo toàn thủ
môn/trọng tài và giữ người nhỏ. Chưa lấy ảnh chưa gán nhãn đầy đủ làm
background. Giữ cả ROI trọng tài để không đánh đổi thành bỏ sót; khóa
sampling và gate trước khi train v4. Một phép thử resolution trên cùng
model có thể giúp tách vấn đề kích thước khỏi thiếu dữ liệu, nhưng chưa
thực hiện trong lần rà này. Không khuyến nghị tăng epoch đơn thuần.

## Tái lập và kết quả cục bộ

```powershell
$env:YOLO_CONFIG_DIR="$PWD/.tmp/ultralytics"
.\.venv\Scripts\python.exe -m backend.cv.audit_role_errors_v3
```

Script kiểm hash dataset/weights và mapping lớp; đối chiếu tổng lỗi với
snapshot đã khóa, từ chối ghi đè thư mục kết quả. Full audit và60crop
nằm trong `data/processed/role_error_audit_v3`, sheets0–2. Snapshot có
60ID/bbox/dự đoán và thống kê ở `docs/fixtures/role_error_audit_v3.json`.
Không đổi DATA_CONTRACT, model ứng dụng hoặc dependency.

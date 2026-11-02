# Mẫu đối chiếu vai trò cùng màu áo — v3

Gói này bổ sung dữ liệu để xử lý lỗi cầu thủ áo vàng bị nhận thành trọng
tài sau lần huấn luyện small v2. Đã tuyển chọn và xuất nhãn ROI; **chưa
huấn luyện v3, chưa có chỉ số cải thiện và chưa đổi detector ứng dụng**.

## Dữ liệu đã rà

11 ảnh phát sóng thật, chia thành 4 nhóm cảnh quan sát, tạo 58 ROI khác
nhau với khoảng đệm ngữ cảnh 48 pixel mỗi phía, cắt tại mép ảnh:

| Vai trò chính | Màu áo | Số lượt quan sát |
|---|---|---:|
| Cầu thủ không phải thủ môn | Vàng | 39 |
| Trọng tài | Vàng | 4 |
| Trọng tài | Xanh ngọc | 13 |
| Trọng tài | Hồng | 1 |
| Thủ môn | Vàng | 1 |

Lớp `player` ở đây là outfield player, người đang thi đấu trong sân và
không phải thủ môn. Bảng đếm đối tượng chính của từng ROI;
nhãn trong crop còn giữ những đối tượng phụ nhìn thấy trong vùng đã rà.
58 lượt không phải 58 người hoặc 58 trận độc lập; một người có thể xuất
hiện ở nhiều frame. Agent đã xem ảnh ngữ cảnh, crop đánh số và overlay
của toàn bộ 58 ROI; chưa có người kiểm độc lập.

Chỉ ROI đã rà được xuất thành ảnh train. Phần ngoài ROI chưa được gán
nhãn đầy đủ, không được dùng toàn frame như nền âm tính. ROI giao với
đối tượng chưa rõ bị chặn. Nhãn trọng tài là vai trò ngữ nghĩa; gói dữ
liệu này không thay quy tắc loại người ngoài biên của ứng dụng.

## Nguồn và ghi công

- [skaczylo / Football-Image-Dataset](https://github.com/skaczylo/Football-Image-Dataset/tree/264212872f1bfa6a9a3413f298793474da741aec),
  revision `264212872f1bfa6a9a3413f298793474da741aec`, tác giả skaczylo
  (2026), giấy phép nguồn CC BY 4.0: nhận 7 ảnh. Loại tập mô phỏng
  `PES_21_clip`; chỉ nhận cảnh phát sóng đã xem. Lớp player của nguồn
  gộp thủ môn nên phải rà lại vai trò từng người.
- [keremberke / football-object-detection](https://huggingface.co/datasets/keremberke/football-object-detection/tree/788fb2722316ee7cad1ace2f6c94e563556a1d3e),
  revision `788fb2722316ee7cad1ace2f6c94e563556a1d3e`, ghi công
  Augmented Startups / Roboflow `football-player-detection-kucab`, bản
  mirror keremberke; dataset card công bố CC BY 4.0: nhận 4 ảnh. Nhãn
  `player` nguồn là nhãn người tổng quát, không ánh xạ thẳng thành cầu
  thủ không phải thủ môn. Tên archive nguồn `test.zip` không liên quan tới
  test nội bộ; các ROI nhận ở đây chỉ là ứng viên train mới.

Giữ nguyên ảnh/nhãn gốc; bản rà riêng nằm trong
`docs/fixtures/role_counterexamples_v3.json`. Có một nhãn gốc của g30
gọi cầu thủ đỏ là trọng tài và trùng một bbox cầu thủ khác; đã bỏ bản
trùng sai, giữ một đối tượng player trong nhãn rà. Thủ môn được tách
riêng, không suy vai trò chỉ từ màu vàng. HSV chỉ sàng lọc ứng viên.

Đã khảo sát thêm `infactory-ai/referee-tracking` nhưng không nhận ảnh
vào gói này; nguồn có điều kiện CC BY-NC 4.0 và không bổ sung đúng nhóm
cầu thủ vàng cần tìm. Các ảnh scout mờ hoặc vai trò chưa rõ cũng không
được dùng làm mẫu âm tính. Gói nhận cuối cùng chỉ dùng hai nguồn trên.

## Bảo toàn tập kiểm và giới hạn

Khóa manifest v1 bằng SHA256
`390626f43158857feafac2823799a405000d9fa6b4007e7c8f97e65cd0e15255`.
Đã kiểm bytes ảnh và nhãn của 380 ảnh cũ, không chuyển ảnh val/test sang
train. Val 128 và test 35 giữ nguyên. Kiểm SHA nguồn, Git blob ảnh/nhãn
và giấy phép GitHub, SHA archive và thành viên archive Hugging Face.

Sàng lọc ảnh mới với 380 ảnh cũ bằng hash bytes/pixel và thumbnail:
dHash cách tối đa 4 bit **đồng thời** sai khác trung bình ảnh xám 64×36
không quá 3. Không phát hiện ảnh trùng theo các phép kiểm này. Đã xem
ngữ cảnh sân, áo và bảng tỷ số, nhưng chưa xác minh độc lập danh tính
trận/ngày thi đấu; không coi đây là bằng chứng tách trận tuyệt đối.
Tên file timestamp không được dùng làm ngày trận đấu.

## Lệnh nghiệm thu và dữ liệu cục bộ

Từ gốc repo:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.curate_role_counterexamples --packet docs/fixtures/role_counterexamples_v3.json --verify-assets
.\.venv\Scripts\python.exe -m pytest tests/test_role_counterexamples.py -q --basetemp .tmp/pytest_counterexamples_unit_v3
```

Đã xuất 58 ảnh PNG/nhãn YOLO cùng manifest vào
`data/processed/role_counterexamples_v3/reviewed_train_rois`.
Ảnh gốc nằm dưới `data/raw/role_counterexamples_v3`; không commit ảnh,
archive hoặc weights. Snapshot kiểm tra:
`docs/fixtures/role_counterexample_audit_v3.json`.

Muốn tái xuất, thêm `--export` trỏ tới một thư mục mới trong repo;
không ghi đè bản xuất đã có. Chưa tạo `data.yaml` hay ghép vào dataset
huấn luyện: bước kế tiếp cần khóa cách ghép/sampling và tiêu chí chọn
model trước khi train. Khi đánh giá tiếp phải báo cả nhầm player thành
referee, FP/FN từng lớp và giữ bộ kiểm cũ. Không đổi API, hợp đồng dữ
liệu, thư viện hoặc frontend trong bước này.

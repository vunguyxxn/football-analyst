# Độ phủ train cho thủ môn nhỏ và trọng tài biên xa

Ngày 04/11/2026. Audit dataset v10 đang có; chưa bổ sung dữ liệu, sửa GT,
đổi sampling, ngưỡng hoặc train thêm. Giữ nguyên cả val/test/heldout.

## Kết luận cần dùng trước khi thu thập thêm

Không thiếu hẳn thủ môn nhỏ hoặc trọng tài áo tối. Khoảng trống rõ nhất là
**độ đa dạng bối cảnh của trọng tài áo tối ở biên xa**, và **số quan sát
thủ môn nhỏ áo xanh/sáng ít hơn nhóm áo vàng/xanh lá**. Phát hiện thêm một
nhãn keeper đặt lên người có dấu hiệu rõ của assistant referee và một
nhãn ref còn đáng nghi. Cần xử lý chất lượng nhãn trước khi train tiếp.
Không đủ bằng chứng nói riêng phần dữ liệu mới gây hồi quy v10.

## Số lượng thật sự đang có

| Cấp đếm | Số lượng | Cách hiểu |
|---|---:|---|
| Lượt ảnh train | 405 | Gồm các lượt lặp theo sampling |
| Đơn vị pixel–label khác nhau | 311 | Cùng pixel/nhãn chỉ tính một lần |
| Khung nguồn theo SHA và frame | 248 | Gộp ROI cùng nguồn, chưa phải trận độc lập |
| Box keeper theo đơn vị ảnh–nhãn | 199 | 235 lượt box sau lặp |
| Box ref theo đơn vị ảnh–nhãn | 560 | 636 lượt box sau lặp |
| Cụm box ref cùng khung nguồn | 550 | Gộp cùng role/parent nếu IoU≥0.7 |

Cụm box không phải số cầu thủ/trọng tài duy nhất trong đời thật: một người
xuất hiện ở nhiều thời điểm vẫn là nhiều quan sát. Ngưỡng0.7 chỉ dùng sàng
lọc ROI chồng nhau trong audit này, không thay phép chấm detector.
Tên prefix, nguồn video và visual family không được gọi là trận độc lập.

## Thủ môn nhỏ: có nhiều, nhưng nhóm màu và nguồn lệch

Chiều cao box trên ảnh nạp train sau resize long-side640, trước augmentation:

| Nhóm màu nhìn gần đúng | Box khác nhau | Box nhỏ<24px | Lượt box nhỏ sau lặp |
|---|---:|---:|---:|
| Vàng / xanh lá / ánh vàng | 106 | 101 | 104 |
| Đỏ / cam / hồng / đỏ sẫm | 54 | 51 | 57 |
| Xanh lam / xanh ngọc | 25 | 24 | 27 |
| Sáng / xám / trắng | 14 | 14 | 17 |
| Tổng | 199 | 190 | 205 |

190/199 quan sát keeper vốn đã nhỏ; không nên tăng số box nhỏ một cách
đại trà rồi coi là sửa đúng vấn đề. Trong24 keeper nhỏ xanh lam/xanh ngọc,
17 thuộc prefix42ba34,6 thuộc573e61,1 từ nguồn bổ sung khác. Trong14 keeper
sáng/xám/trắng,13 thuộc family nền red_stadiums và1 từ full-frame v5.
Các prefix có thể chứa nhiều frame cùng trận; chưa kiểm danh tính trận.

Sáu keeper v8/v9 thêm vào chỉ có nhóm đỏ/hồng và vàng: **không thêm keeper
xanh hoặc sáng**, và chỉ1/6 vẫn nhỏ<24px sau crop-resize. Trong ảnh toàn
cảnh gốc có2/6 nhỏ, nhưng crop đã làm một mục tiêu lớn hơn. Cần nguồn mới
cho keeper nhỏ xanh/sáng ở trận, ánh sáng và góc quay khác; giữ ảnh toàn
cảnh hoặc ROI rộng có ngữ cảnh, không chỉ nhân bản vài crop.

## Trọng tài áo tối ở biên xa: thiếu đa dạng ngữ cảnh

Đã rà màu trên tất cả560 ref theo đơn vị ảnh–nhãn:326 vàng,162 xanh,
37 đỏ/hồng,35 tối. Đây là diện mạo từ ảnh, chưa phải nhãn kit-color độc lập.
35 ref áo tối tương ứng58 lượt box, từ20 khung nguồn. Phân loại bối cảnh
bằng ảnh gốc/crop rộng cho **toàn bộ35** trường hợp này:

| Bối cảnh ref áo tối | Box khác nhau |
|---|---:|
| Biên xa, nền khán đài/bảng quảng cáo | 12 |
| Giữa sân | 16 |
| Biên gần | 6 |
| Chưa chắc là trọng tài hay staff | 1 |

Cả12 biên xa đều nhỏ<24px, trên12 khung và chỉ12 lượt train. Prefix
121364 có11, a9f16c có1; ảnh có cùng kiểu sân/bộ áo đỏ–xanh nhạt và bảng
quảng cáo đỏ/trắng. Không khẳng định đó là hai trận khác nhau chỉ vì hai
prefix. Cả12 nằm trong visual family red_stadiums. Đây là độ phủ **hẹp**,
không phải hoàn toàn vắng mẫu. Đối chiếu với audit val: nhóm hồi quy chủ
yếu áo tối, nhiều assistant xa sát bảng quảng cáo nhưng bối cảnh khác.

Bốn ref v8/v9 mới gồm2 giữa sân và2 biên gần; **không tăng số mẫu ref tối
biên xa**. Hai ref tối full-frame v5 cũng ở giữa sân. ROI ref tối cũ là
crop phóng lớn của trọng tài giữa sân, không bù được mục tiêu biên xa nhỏ.

525 ref màu khác chưa gán vị trí biên/giữa sân trong audit này; trạng thái
này là unknown, không phải zero. Không dùng bảng35 ref tối để suy ra tổng
số assistant biên xa của mọi màu. Phần review bối cảnh tập trung đúng nhóm
áo tối được xác định trong audit hồi quy.

## Vì sao đếm ROI dễ gây hiểu sai

47 quan sát ref thuộc ROI cũ tạo87 lượt box; cả47 đều cao≥48px khi nạp
train, phần lớn khoảng540–616px. Nhưng trên khung nguồn,32/47 cao<24px,
15/47 từ24–48px. Cắt sát người đã đổi mạnh kích thước và loại bớt bối cảnh.
Các lượt lặp không tạo thêm trận, màu áo hoặc cảnh bảng quảng cáo.

Các số kích thước ở đây là trước augmentation. Không kết luận model chưa
bao giờ thấy kích thước khác vì mosaic/scale vẫn có thể thay đổi chúng.
Dataset vẫn có411 ref nhỏ từ ảnh nền toàn cảnh; khoảng trống không phải
thiếu mọi ref nhỏ mà là kết hợp **áo tối + biên xa + nguồn đa dạng**.

## Hai cờ chất lượng, chưa sửa nhãn train

1. **goalkeeper-114 / C131**: file
   `images/train/744b27_3_5_png.rf.ad8d20930f605327cf07d41e51e9a6ef.png`,
   label index17 (đánh số từ0 trong file nhãn). Box hiện có class goalkeeper
   đặt lên người áo vàng/quần đen sát biên gần; cùng ảnh đã có keeper cạnh
   cầu môn và main referee ở giữa sân. Cần rà và sửa ở phiên bản dataset
   mới, không tính case này là bằng chứng keeper thật được phủ tốt.
2. **referee-158 / C64**: file
   `images/train/42ba34_3_1_png.rf.5bb4bc1a81118c5f226a108e76bbad8a.png`.
   Label index4 (từ0). Người mặc tracksuit đen sát khu kỹ thuật, trong khi officials khác mặc
   xanh; vai trò staff hay official còn chưa chắc từ một ảnh. Đánh dấu
   cần xác minh, không tự gán lại class.

Hai case không bị sửa, xóa hay quarantine trong train v10. Các bảng tổng
vẫn tính đúng GT hiện có và giữ cờ riêng; không coi nhãn được cung cấp là
đã kiểm độc lập hoàn toàn. Chỉ một nhãn keeper đáng nghi này không giải
thích được toàn bộ hồi quy điểm của v10.

## Bằng chứng và tái tạo

- `docs/fixtures/role_train_coverage_review_v10.json`: review màu của toàn
  bộ759 box keeper/ref, bối cảnh35 ref tối, image/label hash và hai cờ lỗi.
- `docs/fixtures/role_train_coverage_summary_v10.json`: bảng tổng, nguồn,
  kích thước loaded/source, counts không gộp unknown thành thiếu mẫu.
- `data/processed/role_train_coverage_v10/inventory.json`: đầy đủ unit,
  parent, box gốc, tọa độ ROI và cụm chồng nhau. Context C131/C64 và hai
  sheet `dark-contexts-0.jpg`/`dark-contexts-1.jpg` giữ bằng chứng trực quan.
- Crop review cục bộ ở `data/processed/role_train_coverage_v10_preview/`.
  Đã xem19 sheet keeper/ref,6 sheet context chung, toàn bộ35 context ref
  tối riêng và hai ảnh toàn cảnh native của nhãn đáng nghi. Agent rà một
  lần, chưa có người kiểm độc lập.

```powershell
.\.venv\Scripts\python.exe -m backend.cv.audit_role_train_coverage inventory
.\.venv\Scripts\python.exe -m backend.cv.audit_role_train_coverage summarize
.\.venv\Scripts\python.exe -m pytest -q tests/test_role_train_coverage.py --basetemp .tmp/pytest-train-coverage-targeted
```

Lệnh inventory yêu cầu output chưa tồn tại; summarize kiểm hash inventory,
manifest, review image/label và prefix từ manifest. Kiểm lại toàn bộ dataset
sau audit; không thay file ảnh/label, weights, frontend hoặc schema.
575 test Python đạt;7 test đích đạt sau thêm kiểm ràng buộc review/source.

## Việc tiếp theo đã có căn cứ

Ưu tiên chốt bản sửa/loại nhãn sai cho keeper-114 và xác minh referee-158
trước khi train lại. Sau đó mới tìm nguồn thật khác bối cảnh cho2 nhóm:
keeper nhỏ áo xanh/sáng và ref áo tối biên xa sát bảng quảng cáo. Gán đầy
đủ mục tiêu trong ảnh/ROI rộng, chia theo trận trước inference và giữ nguyên
heldout. Chưa tăng epoch hoặc tăng lặp crop hiện có.

# Làm sạch và bổ sung dữ liệu phân vai trò v11

Ngày 04/11/2026. Chỉ chuẩn bị dữ liệu ngoại tuyến, chưa huấn luyện và chưa
thay detector của ứng dụng. Giữ nguyên hợp đồng dữ liệu.

## Hai nhãn v10 được xử lý

- `goalkeeper-114`: ảnh `744b27_3_5_png.rf.ad8d20930f605327cf07d41e51e9a6ef.png`,
  dòng index 17, đổi class 1 → 2. Ảnh gốc cho thấy người áo vàng ở biên gần;
  thủ môn áo xanh lá ở cầu môn trái và trọng tài chính áo vàng giữa sân.
  Chỉ đổi token class, giữ nguyên tọa độ, các dòng khác và kiểu xuống dòng.
- `referee-158`: ảnh `42ba34_3_1_png.rf.5bb4bc1a81118c5f226a108e76bbad8a.png`,
  dòng index 4. Người mặc tracksuit ở khu kỹ thuật chưa đủ căn cứ phân biệt
  staff/official. Cách ly **nguyên ảnh train**, không xóa riêng box rồi biến
  người chưa chắc vai trò thành nền âm. Chưa kết luận vai trò thật của người này.

Các quyết định dựa vào ảnh tĩnh toàn cảnh, không tuyên bố đã xác minh bằng
chuỗi video hay được người thứ hai gán nhãn. Cả v10 và các bản cũ giữ nguyên.

## Nguồn mới được nhận

Ảnh đã lưu trong kho raw khảo sát nhưng chưa có trong train v10. Chọn và
rà nhãn bằng ảnh gốc, không dùng dự đoán vai trò v6/v10 để chọn hoặc gán nhãn.
Ba ảnh giữ toàn khung; hai ảnh Bayern cắt dải khu kỹ thuật phía dưới nhưng
giữ nguyên chiều rộng 1920 px và mọi đối tượng thi đấu nhìn thấy trong ROI.

| ID khảo sát | Bối cảnh theo bảng tỷ số/khán đài | Đối tượng ưu tiên | Cao khi thu cạnh dài về 640 |
|---|---|---|---:|
| 141 | RBL–FCH | Thủ môn xanh lam, đổ người | 14,41 px |
| 66 | BAR–MLL | Thủ môn sáng/xám, ngồi thấp | 21,53 px |
| 54 | CEL–VIL | Trợ lý áo tối, biên xa | 28,47 px |
| 98 | BAY–BVB, sân nhà Bayern | Trợ lý áo tối, biên xa | 16,86 px |
| 269 | Cùng nhóm BAY–BVB | Trợ lý áo tối, biên xa | 21,95 px |

Tổng **5 khung, 4 nhóm bối cảnh**, thêm **76 box player, 4 goalkeeper,
8 referee**. Có hai keeper khác màu nằm trong các khung ref; vẫn gán nhãn
đầy đủ. Nhóm BAY–BVB có hai thời điểm của cùng bối cảnh, không tính thành
hai trận độc lập. Không suy số người hoặc số trận độc lập từ số box.

Hai keeper ưu tiên đạt định nghĩa nhỏ theo chiều cao box nhưng tư thế đổ
người/ngồi làm box thấp; **chưa thay thế mẫu thủ môn đứng xa**. Trong ba ref
biên xa chỉ hai box dưới 24 px. Đây là bổ sung ban đầu, chưa đủ chứng minh
đã giải quyết toàn bộ thiếu đa dạng hoặc cải thiện model.

Nhãn nguồn có class 0 ball, 1 player **gồm thủ môn**, 2 referee. Rà và tách
thủ môn sang class 1 của dự án, player thành 0, referee thành 2. Ở ảnh 98,
source line 19 là box player trùng người với referee line 21: bỏ bản trùng,
giữ nhãn referee. Không lấy màu áo đơn thuần làm vai trò.

Loại các proposal 0, 67, 105 khỏi bản phát hành: ảnh 0 thiếu nhãn người đá
phạt góc và có người ngoài sân chưa chắc vai trò; ảnh 67 có nhãn vào cỏ;
keeper 105 áo xanh lá, không phải nhóm xanh lam/sáng cần bổ sung. Keeper
xanh ở 0/67 cũng không nhỏ dưới 24 px theo phép đo đã chốt.

## Nguồn gốc và giấy phép

[Football Image Dataset của skaczylo](https://github.com/skaczylo/Football-Image-Dataset),
revision `264212872f1bfa6a9a3413f298793474da741aec`.
Ảnh và nhãn được nguồn công bố theo
[CC BY 4.0](https://github.com/skaczylo/Football-Image-Dataset/blob/264212872f1bfa6a9a3413f298793474da741aec/LICENSE).
Ghi công: skaczylo, Football Image Dataset, 2026. Thay đổi: rà/tách vai trò,
gỡ một box trùng, cắt ROI rộng. Không tuyên bố mọi ảnh trong kho nguồn đều
là bóng đá thật: bản này chỉ nhận các khung broadcast đã xem, không nhận
nguồn mô phỏng bị cách ly trước đây.

Fixture review giữ Git blob SHA ảnh/nhãn, SHA256 bản local, tọa độ từng box,
ROI, quyết định vai trò và ghi công. Nhãn được agent rà, **chưa kiểm chứng
độc lập**. Các nhóm trận là suy luận từ scoreboard/venue/kit, không phải
danh tính trận chính thức đã xác minh.

## Bộ dữ liệu đã khóa

- Train **409 lượt / 315 đơn vị pixel–label**: nền 405 lượt trừ một khung
  cách ly, cộng 5 khung mới ×1. Giữ nguyên số lần lặp của nền; không nhân ROI.
  Tổng lượt box: **4921 player / 236 goalkeeper / 642 referee**.
- Val **128**, test **35**: giữ nguyên từng byte ảnh và nhãn.
- Match `128057` tiếp tục là heldout, không đưa vào train hoặc val.
- Sàng trùng với **478 ảnh tham chiếu có SHA256 khác nhau**, gồm mọi split
  v10 và các ảnh release v8/v9 riêng: không có trùng pixel hoặc hit theo
  dHash/thumbnail ở ngưỡng cũ. Sàng cả ảnh gốc lẫn ROI mới.
- Kiểm ảnh và bối cảnh cũng được dùng: BAY–BVB ở sân nhà Bayern khác nhóm
  Dortmund-home khán đài vàng của val. Cùng CLB không đồng nghĩa cùng trận;
  hash/perceptual không tự chứng minh độc lập theo trận.

Đường dẫn local: `data/processed/role_clean_dataset_v11/dataset`.
Manifest SHA256: `acbd3e8617abf0577f149051fd4b39ec21dacdd600dcc7e8d7a0f34e5a6da23b`.
Protocol, review, nhóm nguồn và snapshot nằm trong `docs/fixtures/*v11.json`.
Không đưa raw/dataset vào git.

## Kiểm tra và bước tiếp theo

Tạo ở thư mục đích chưa tồn tại:

```powershell
.venv/Scripts/python.exe -m backend.cv.curate_role_dataset_v11
.venv/Scripts/python.exe -m pytest tests/test_curate_role_dataset_v11.py -q --basetemp .tmp/pytest_role_v11
```

Không chạy đè dataset đã phát hành. Kiểm lại bản có sẵn bằng
`verify_dataset` với protocol v11; đối chiếu `protected_rows` với v10.
Code chặn sửa split bảo vệ, hash sai, nhãn lặp, nhầm mapping nguồn,
ROI chứa người chưa chắc vai trò và thay cách lấy mẫu.

Nghiệm thu: lệnh tạo hoàn tất, tạo lại cho cùng manifest SHA256; 566 file
nhãn nền còn lại giữ nguyên hash, mọi ảnh nền được giữ có hash không đổi.
Nhãn xuất mới khớp hình học trong packet review. 583 test toàn bộ đạt
(1 network deselected, 4 warning cũ); sau bổ sung test hồi quy summary với
dòng legacy thiếu `sampling_origin`, cả 7 test đích đều đạt.

Bước tiếp theo: khóa cấu hình small cho một phép thử có kiểm soát trên v11,
đánh giá cả ba lớp ở 640/1280 bằng cùng ngưỡng và phép ghép như v6/v10.
Chưa được coi kết quả train là đạt trước khi đo; tiếp tục ưu tiên keeper
xanh/sáng **đứng xa** và thêm bối cảnh trợ lý tối độc lập nếu còn hồi quy.

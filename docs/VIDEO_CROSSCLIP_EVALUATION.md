# Kiểm thử luồng upload trên ba clip khác

Ngày01/11/2026. Kết luận: tracking chạy hết ba video, nhưng **0/3clip tự
tạo được tọa độ sân và phân tích chiến thuật** với phiên bản61f1359.
Kết quả tốt trên clip mẫu không đại diện cho khả năng xử lý video bất kỳ.
Đây là đo baseline, chưa sửa thuật toán sản phẩm để làm đẹp số liệu.

## Đầu vào và cách kiểm

Ba clip cục bộ có camera lia, góc sân/độ sáng/màu áo khác nhau; đều là
đoạn quay truyền hình, không coi là bộ kiểm độc lập đại diện mọi trận.
Khóa SHA256nguồn, hai trọng số detector/mốc sân, metadata và lịch ảnh
rà tại `fixtures/upload_crossclip_manifest_v1.json`. Không dùng mốc tay,
không fit hoặc đổi ngưỡng theo nhãn của ba clip này.

- Giữ tác vụ người dùng đang mở cho `Video Project15(2).mp4`, chờ xử lý
  hoàn tất; không hủy hoặc thay kết quả của tác vụ đó.
- Tải hai file còn lại đầy đủ qua API hiện hành, chạy tuần tự trên GPU,
  không lấy kết quả của clip mẫu để minh họa cho clip mới.
- Rà ảnh thô đầu/giữa/cuối và cặp giữa/giữa+15frame (0,5s).
  Chốt48điểm chân/vai trò mẫu trước khi xem box dự đoán; có36lượt cầu thủ
  tuyến ngoài,6trọng tài,4thủ môn và2người ngoài sân.
- Dùng cùng phép ghép điểm không dựa vào màu/ID, gate chính35px,
  kiểm nhạy25/50px. A/B là tên cụm tùy ý: xác định hoán vị từ ảnh đầu
  của cặp và giữ nguyên cho ảnh sau, không đảo nhãn để làm tăng kết quả.
- Kiểm cấu trúc/số đếm tracking bằng `tracking_summary.summarize`,
  source hash/metadata và trạng thái tác vụ. Nếu có tọa độ thì kiểm
  bằng audit hiện có; nếu không có thì ghi không đánh giá được.

Nhãn do agent rà ảnh, là mẫu thưa, không độc lập và không đầy đủ mọi
người trong khung hình. Không suy ra precision/recall toàn frame,
IDF1/MOTA hoặc accuracy toàn trận từ các số đếm bên dưới.

## Kết quả toàn video

| Clip | Thời lượng | Frame có người được giữ | Frame nhận được biên | ID / ID ngắn dưới1s | Tọa độ sân / cửa sổ chiến thuật |
|---|---:|---:|---:|---:|---:|
| Project12 |46,93s|1.402/1.408 (99,6%)|1.402|256 /140|0 /0|
| Project15(1) |35,90s|502/1.077 (46,6%)|506|95 /46|0 /0|
| Project15(2) |80,93s|237/2.428 (9,8%)|241|96 /43|0 /0|

Tỉ lệ lượt quan sát gán `unknown` lần lượt6,9%;7,6%;15,5%. Những số
này chỉ tính trên box còn được giữ, không tính những người bị bộ lọc
biên loại trước tracking. ID ngắn/nhiều không tự bằng số lần đổi ID.

Các job đã hoàn tất:

| Clip | Job |
|---|---|
| Project12 |`f27ce9794f0c42cfb9f2fdca127e701a`|
| Project15(1) |`6b996615df664a0cb99f47d2c7bdd819`|
| Project15(2) |`ed6ed422cb6443f6ad239f3fab0addef`|

Cả ba có tracking=`completed`, calibration=`needs_input`,
analysis=`awaiting_calibration`. `/pitch-estimate` và `/tactics` trả200
kèm `not_available`, không trả heatmap/quãng đường/gợi ý giả. Video
nguồn vẫn trảRange206. Không có tọa độ nghĩa là chưa đo được, không
phải cầu thủ chạy0m hoặc đội không hoạt động.

## Rà màu áo và ID trên mẫu

- Project12:12/12điểm cầu thủ tuyến ngoài ghép được; ảnh sau6/6vai trò
  áo trắng/đen khớp hoán vị đã chốt. Sáu cặp danh tính0,5s giữ ID.
  **Hai lượt trọng tài bị gán B**; hai lượt HLV ngoài sân không có box
  tương ứng. Đây không phải chứng nhận loại đúng mọi người ngoài sân.
- Project15(1):12/12điểm tuyến ngoài ghép được; ảnh sau6/6vai trò màu
  khớp, sáu cặp0,5s giữ ID. **Hai lượt trọng tài bị gán B**; hai lượt
  thủ môn cũng ở B, chưa có cơ chế xác nhận/tách vai trò tuyến ngoài.
- Project15(2):0/12điểm tuyến ngoài ghép được tại1214/1229 vì hai frame
  không có box được giữ. Không có cặp ID/vai trò để kết luận; không
  tính số đổi ID bằng0 thành kết quả tốt.
- Các kết quả trên giữ nguyên với cả gate25/35/50px. Chỉ có12cặp
  tuyến ngoài đo được và0thay đổi ID trong mẫu; chưa đánh giá ID toàn clip.

## Nguyên nhân và ưu tiên sửa

1. **Hiệu chỉnh sân không tổng quát được.** Cả ba không có anchor vượt
   kiểm ứng dụng ở lịch tự động, kể cả Project12 có tracking gần toàn
   clip. Đây là nút thắt trực tiếp khiến heatmap/vận động/chiến thuật
   chưa có kết quả. Cần đánh giá khả năng tìm mốc khi thiếu vòng tròn
   hoặc thấy một phần vùng cấm, vẫn đối chiếu sai số trước khi công bố.
2. **Bộ lọc biên làm mất nhiều dữ liệu khi camera không quay đủ hai
   biên dọc.** Đây là chính sách từ chối hiện tại, không phải detector
   không thấy người. Ở ảnh1214 của Project15(2), biên gần không hiện
   đủ trong ảnh; không được nới bằng cách coi toàn vùng cỏ là sân.
   Cần thử biên theo homography/chuyển động có kiểm chứng và ngắt khi
   mất dấu/chuyển cảnh, thay vì gán ID cho người ngoài sân.
3. **Màu áo hai cụm ép trọng tài vào một đội.** Luồng upload dùng hai
   tâm Lab với ngưỡng khoảng cách, không dùng nhánh ba vai trò đã có
   hiệu chỉnh. Cần phân biệt/reject màu thứ ba không chắc chắn, ưu tiên
   giữ `unknown` thay vì đưa người đó vào nhiệt/sơ đồ đội. Không thể tự
   gọi mọi màu thứ ba là trọng tài vì còn thủ môn và điều kiện sáng.
4. **Chưa thể đánh giá chất lượng chiến thuật trên ba clip.** Không
   có tọa độ nên không có gợi ý để đối chiếu thực tế. Việc không trả
   gợi ý thiếu căn cứ là đúng; không đồng nghĩa engine chiến thuật đã
   được kiểm chứng trên ba video. Sau khi sửa1–3 cần đo lại và bổ sung
   nhãn/đo đạc độc lập; không chỉ nhìn số lượng gợi ý tăng.

Không tự hạ ngưỡng hình học, nội suy người khuất hoặc thay dữ liệu
demo trong phiên kiểm này. Thứ tự tiếp theo: hiệu chỉnh/biên có kiểm
chứng, loại vai trò chưa chắc khỏi phân tích đội, rồi mới mở rộng đánh
giá ID và nhận xét chiến thuật trên các đoạn thực sự có dữ liệu.

## Lặp lại kiểm và bàn giao

Từ gốc repo, khi còn các job cục bộ:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.evaluate_crossclip_uploads `
  --manifest docs/fixtures/upload_crossclip_manifest_v1.json `
  --labels docs/fixtures/upload_crossclip_visual_labels_v1.json `
  --jobs docs/fixtures/upload_crossclip_jobs_v1.json `
  --output data/processed/upload_crossclip_v1/evaluation-rerun.json

.\.venv\Scripts\python.exe -m pytest -q -m "not network" `
  --basetemp=.tmp/pytest_crossclip_rerun
```

Runner chỉ đọc job, không fit/chạy lại detector, không sửa tác vụ, không
ghi đè báo cáo. Exit0 là đo xong, **không phải đạt nghiệm thu tự động**;
`automatic_analysis_ready_clips=0` thể hiện kết quả sản phẩm. Dữ liệu
thử có hash không khớp hoặc chưa hoàn tất sẽ bị từ chối.

428test Python đạt,1network deselected;3test mới kiểm thiếu hiệu chỉnh
không thành kết quả phân tích, khóa hoán vị màu/đổi ID/trọng tài, từ
chối nguồn sai/tác vụ chưa xong và phát hiện gợi ý thiếu hỗ trợ.
Frontend/thuật toán upload không đổi; không tuyên bố đã thao tác UI.
Khóa kết quả gọn: `fixtures/upload_crossclip_results_v1.json`.
Báo cáo đầy đủ/ảnh rà ở `data/processed/upload_crossclip_v1`.

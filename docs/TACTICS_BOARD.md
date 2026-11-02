# Bảng chiến thuật — 02/11/2026

## Mục đích và phạm vi

Trang `/tactics` có trong menu **Bảng chiến thuật**, phục vụ HLV bố trí đội
hình và giải thích kế hoạch trên sân tương tác. Bố cục tham khảo ảnh người
dùng và [Free Tactics Board](https://freetacticsboard.com/): sân lớn, công
cụ bên trái, thư viện sơ đồ/thuộc tính bên phải. Mã React/SVG và giao diện
được viết trong dự án, không tải mã, tài sản hoặc thành phần trả phí của
trang tham khảo. Không thêm dependency.

Đây là bảng soạn thủ công, không phải sơ đồ tự nhận diện hoặc số đo từ
video. Sân ghi rõ “Kế hoạch huấn luyện · Bố trí thủ công”. Không ghi các
vị trí này vào TrackingRow, heatmap, kết quả xG hay báo cáo CV. Không đổi
DATA_CONTRACT/backend/API. Bảng hoạt động tại trình duyệt kể cả khi backend
không chạy; chỉ báo backend chung ở đầu ứng dụng vẫn phản ánh kết nối thật.

## Sử dụng

1. Mở **Bảng chiến thuật**, đặt tên buổi tập. Mặc định có hai đội, mỗi đội
   11cầu thủ và một bóng; độiA4-3-3, độiB4-4-2.
2. Chọn độiA/B, chọn một trong6mẫu:4-3-3,4-2-3-1,4-4-2,3-5-2,3-4-3,5-4-1.
   Mẫu chỉ bố trí lại đội đang chọn trong pha hiện tại. Giữ ID/tên/số áo
   của các slot đã có, không đụng nét vẽ hoặc đội còn lại. Mẫu là lựa chọn
   của HLV, không là kết luận đội đang chơi sơ đồ đó.
3. Công cụ **Chọn**: kéo cầu thủ/bóng/nét vẽ; chọn token để sửa số áo hoặc
   tên/vai trò. Có danh sách đối tượng bên phải để chọn bằng bàn phím.
4. **Cầu thủ/Bóng/Chữ**: chạm trên sân để đặt. Chỉ một bóng trong mỗi pha;
   đặt bóng mới thay vị trí bóng cũ. Nhãn chữ mặc định “Điểm hỗ trợ”, sửa
   nội dung ở bảng thuộc tính. **Chuyền/Chạy/Vùng**: kéo trên sân để vẽ
   mũi tên liền, mũi tên nét đứt hoặc vùng chữ nhật.
5. **Xóa**: chạm đối tượng để xóa; hoặc chọn rồi dùng nút Xóa/Del. Nút
   thùng rác cạnh Toàn sân làm trống pha, có thể hoàn tác.
6. Phím mũi tên dịch đối tượng0,5m; giữShift dịch3m. Ctrl/Cmd+Z hoàn tác,
   Ctrl/Cmd+Shift+Z làm lại. Escape bỏ chọn/công cụ. Các phím này không
   chiếm thao tác gõ trong ô nhập. Một lượt kéo chỉ ghi một bước hoàn tác;
   giữ tối đa40bước trong phiên, không lưu undo/redo vào file.
7. Đổi màu hai đội, bật5hành lang dọc, đặt tên pha và ghi chú HLV.
8. **Thêm pha** sao chép pha hiện tại để phát triển bước tiếp theo; chỉnh
   vị trí và ghi chú riêng. Tối đa8pha, mỗi pha150đối tượng. Có chuyển/xóa
   pha; luôn giữ ít nhất1pha. **Trình chiếu** lần lượt hiện các pha mỗi
   1,4giây rồi dừng ở pha cuối. Đây là slideshow, chưa nội suy chuyển động
   hoặc xuất video.
9. **Xuất PNG** dựng ảnh sân của pha hiện tại ở1680×1088, mở xem trước rồi
   chọn **Tải ảnh PNG**. Ảnh bỏ dấu chọn của editor; không chứa ghi chú ở
   sidebar. **Tải bảng JSON** giữ toàn bộ pha, màu, tên/notes và đối tượng;
   **Mở bảng JSON** khôi phục file chỉnh sửa, có thể undo thao tác nhập.

## Dữ liệu và lưu trữ

`frontend/src/lib/tacticsBoard.ts` định nghĩa định dạng file frontend riêng
`tactics_board_v1`. Tọa độ `x_m/y_m` dùng mét105×68, gốc trái dưới; lúc vẽ
SVG chỉ đảo y qua `toSvg`. Các nét có `end_x_m/end_y_m`. Bóng/vị trí chỉ là
đối tượng đồ họa của HLV. Không đổi hệ tọa độ hoặc schema backend hiện có.

File giới hạn1MiB UTF-8. Parser kiểm kind,1–8pha, ID không trùng trong
cùng pha, màuhex6ký tự, loại đối tượng, độiA/B, số áo nguyên1–99, tọa độ
hữu hạn trong sân và đủ hai đầu nét vẽ. Giới hạn title100/name80/label60/
notes4000ký tự. Từ chối TrackingRow hoặc file không đúng cấu trúc; không
tải mô hình hoặc chạy code từ file nhập. Tên/nhãn được React/XML escape.

localStorage key `football-analyst.tactics-board.v1` giữ một bảng đang làm
việc cho origin hiện tại. Lưu sau400ms ngừng sửa, đồng thời thử lưu khi
pagehide/rời route. Trạng thái phân biệt đang lưu/đã lưu/thất bại. Có nút
Lưu trên máy để ghi ngay. Lỗi quota/quyền không thay thế bản lưu thành công
trước. Nếu bản cũ hỏng, mở bảng mặc định và ngừng tự ghi đè; người dùng
chọn Lưu trên máy mới ghi bảng hiện tại. Có thể tải JSON để giữ bản ngoài
trình duyệt. Đổi origin, xóa dữ liệu site hoặc chế độ riêng tư có thể không
giữ bản cũ. Chưa thêm đồng bộ server, chia sẻ link hoặc thư viện nhiều bảng.

`Pitch.tsx` chỉ thêm propSVG tùy chọn để nhận ref/pointer/keyboard ở trang
mới; các trang đang dùng Pitch không phải đổi lời gọi.

## Kiểm tra

Từ frontend chạy `npm test`, `npm run build`, `npm run lint`:32test đạt,
gồm9test mới cho sơ đồ11người/hai đội phản chiếu, chỉ đổi đội được chọn,
giữ danh tính/tên, tránh trùng ID từ file nhập, dịch cả nét không méo khi
chạm biên, undo/redo, round-trip/pha độc lập, từ chối file sai/giới hạn và
lưu có kiểm tra trước ghi/quota. Còn FastRefresh/bundle warning có sẵn.
Không đổi backend nên không chạy lại test Python cho tính năng này.

Đã kiểm in-app browser thật:

- Desktop1360×900: bố cục3cột, kéo cầu thủA6 từ(33,17) tới khoảng(38,9;20,7),
  undo về đúng vị trí rồi redo; sửa nhãn Tiền vệ trụ.
- Vẽ chuyền/chạy/vùng; tổng đối tượng từ23→24→26 giữa các pha. Đổi độiB
  sang3-5-2 vẫn giữ cầu thủA và nhãn đã sửa.
- Thêm pha2với notes riêng, trình chiếu tự đến pha2/dừng; reload rồi mở
  lại pha2 có đủ nét vẽ/notes. Rời sang Hồ sơ cầu thủ rồi quay lại vẫn giữ
  ghi chú. Phím ArrowRight tăng x0,5m, Ctrl+Z khôi phục.
- PNG đã dựng/giải mã trong hộp xem trước, naturalWidth1680/naturalHeight1088;
  đã rà ảnh sân/nhãn/mũi tên/vùng. Không tự lưu download vào thư mục ngoài
  dự án; chưa kiểm hộp Save của hệ điều hành.
- Viewport390×844: công cụ chuyển thành hàng cuộn, inspector xuống dưới;
  document scrollWidth=clientWidth=375px (trừ scrollbar), không tràn ngang
  trang. Chưa kiểm thao tác trên thiết bị cảm ứng vật lý. Đã reset viewport
  sau QA. File chooser JSON chưa kiểm UI; parser/round-trip đã kiểm tự động.

Ảnh kiểm: `docs/screenshots/tactics-board-desktop.png` và
`docs/screenshots/tactics-board-mobile.png`. Các cảnh trong ảnh được bố trí
thử khi kiểm UI, không phải kết quả tracking hoặc phân tích trận thực tế.

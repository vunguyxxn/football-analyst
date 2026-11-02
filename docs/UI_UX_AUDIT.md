# Đánh giá giao diện Touchline — 02/11/2026

## Phạm vi và cách đọc

Yêu cầu: đánh giá toàn bộ giao diện và đề xuất hướng hiện đại, đẹp hơn. Phiên này
chỉ khảo sát và viết tài liệu; chưa thay đổi frontend, backend hoặc hợp đồng dữ liệu.

Đã xem trực tiếp sáu trang `/overview`, `/match`, `/video`, `/players`, `/reports`,
`/tactics` trên trình duyệt cục bộ, viewport 1440×1000 và 390×844. Chiều rộng nội
dung khi có scrollbar lần lượt thường là 1425 và 375 px. Xem dữ liệu StatsBomb trận
8650, hồ sơ Metrica, báo cáo mẫu dạng thẻ/bảng, video trống và video mẫu có kết quả,
bảng chiến thuật hiện có. Đối chiếu thêm CSS và các thành phần React.

Ảnh và số đo cục bộ: `data/processed/ui_audit_20261102/` (không đưa dữ liệu này vào
Git). Các số đo phản ánh đúng mẫu đang mở, không đại diện mọi trận, mọi clip hay
mọi thiết bị. Đây là đánh giá chuyên môn về bố cục và khả năng sử dụng, chưa phải
nghiên cứu với HLV, kiểm định WCAG đầy đủ hay phép đo Lighthouse. Chưa kiểm chứng
mọi trạng thái lỗi, upload/xử lý đang chạy, bàn phím toàn luồng hoặc zoom 200%.

## Nhận định chung

Nền tảng hình ảnh khá tốt: nền tối xanh than, font Geist, icon cùng phong cách,
số KPI nổi bật, nhận diện Touchline rõ, sân bóng và nhóm dữ liệu có khung riêng.
Đặc biệt nên giữ cách phân biệt dữ liệu thật, mẫu, ước lượng, nguồn và phạm vi.

Điểm yếu lớn nhất là thứ tự ưu tiên thông tin. Nhiều trang dành phần đầu cho
metadata, giải thích kỹ thuật và các khối lồng nhau; nội dung HLV cần xem lại nằm
quá thấp. Chữ phụ thường 8–11 px, quá nhỏ cho phiên đọc dài. Mobile chủ yếu xếp
dọc bố cục desktop nên chiều dài trang tăng mạnh và sân tương tác bị thu nhỏ.

Hướng phù hợp: không gian phân tích thể thao rõ ràng, gọn và tập trung vào sân,
video, tình huống. Độ hiện đại nên đến từ hệ chữ, phân cấp, tương tác và tính nhất
quán. Chưa cần thêm thư viện hoặc thay stack hiện có.

## Các vấn đề xuyên suốt

| Vấn đề | Bằng chứng hiện tại | Đề xuất |
| --- | --- | --- |
| Chữ nhỏ và mờ | Nhiều CSS 8–11 px; nhãn công cụ, caption và nguồn khó đọc | Body 14–16 px; caption 12–13 px; tiêu đề khối 16–18 px; KPI 28–36 px; line-height khoảng 1,45–1,6 |
| Quá nhiều tầng khung | KPI nằm trong thẻ con, thẻ con lại trong thẻ lớn; nhiều đường viền cạnh nhau | Chỉ giữ khung cho nhóm có ý nghĩa; dùng khoảng cách, tiêu đề và divider để phân nhóm bên trong |
| Thiếu một hệ thành phần chung | Mỗi trang có header, nút, tab, KPI và nhãn nguồn với kích thước riêng | Chuẩn hóa PageHeader, MetricCard, SourceBadge, EmptyState, SectionHeader, nút và tab bằng stack hiện có |
| Thứ tự nội dung chưa theo nhiệm vụ | Metadata báo cáo và mô tả xử lý đứng trước kết quả | Đặt ngữ cảnh ngắn → kết quả chính → căn cứ → phương pháp/chi tiết kỹ thuật |
| Trạng thái và màu dễ mang nghĩa sai | Mũi tên tăng/giảm trên thống kê không có phép so sánh; tiến độ 100% dù tọa độ chỉ một phần | Mũi tên chỉ dùng khi có baseline thật; tách hoàn tất xử lý khỏi mức đủ dữ liệu |
| Chưa nhất quán cách biểu diễn | Số thập phân dấu chấm ở Match, dấu phẩy ở Reports; thuật ngữ Việt/Anh xen kẽ | Dùng chung định dạng vi-VN, đơn vị và độ chính xác theo từng chỉ số; dịch nhãn nghiệp vụ, giữ tên nguồn/mã trong phần chi tiết |
| Điều hướng mobile tốn chỗ | Sidebar biểu tượng 60 px luôn hiện | Drawer có nhãn hoặc thanh điều hướng dưới với mục thêm; thiết kế lại thứ tự nội dung ở màn hình nhỏ |
| Tên trang lặp | Topbar đã có tiêu đề, bên dưới lại header lớn cùng tên | Topbar gọn phục vụ điều hướng; page header chỉ giữ một tiêu đề chính và hành động quan trọng |
| Thông tin trang trí giống chức năng | Dấu “•••” ở hồ sơ sidebar không phải nút | Bỏ phần gợi hành động khi chưa có chức năng; không thêm tài khoản giả |
| Nhãn nguồn toàn cục thiếu ngữ cảnh | Footer luôn ghi StatsBomb cả ở video và bảng thủ công | Đưa nguồn đúng theo từng nội dung; footer chỉ giữ nhận diện và nguồn chung ở vị trí thích hợp |

### Hệ hình ảnh đề xuất

- Giữ nền hiện có `#0b0f14`, surface `#121821`, chữ chính `#e5e7eb`; tăng độ rõ
  của chữ phụ quan trọng. Dùng tối đa khoảng ba cấp surface có mục đích.
- Giữ xanh lá làm màu thương hiệu và hành động chính. Tím có thể dành cho chế độ
  biên tập chiến thuật; màu đội phải có quy tắc rõ và luôn kèm tên/nhãn.
- Không ép màu áo thật, nhóm A/B ước lượng và đội của bảng thủ công thành cùng một
  danh tính. Chỉ đồng bộ quy ước khi nguồn/mapping thực sự tương ứng.
- Khoảng cách theo hệ 4/8 px: 8, 12, 16, 24, 32. Radius khoảng 12–16 px; giảm
  glow, gradient và viền lặp để sân, video và số liệu thu hút mắt trước.
- Nút chính cao khoảng 40–44 px; hướng tới vùng chạm 44 px trên điện thoại.
  Đây là mục tiêu thiết kế đề xuất, không phải cách diễn đạt yêu cầu WCAG AA.
- Tên cầu thủ tiếp tục dùng `short_name`; tên đầy đủ qua tooltip/focus hoặc vùng
  nhận diện. Không tự đổi tên dựa trên phỏng đoán danh tính.

## Đánh giá từng trang

### Tổng quan

Trang mặc định chỉ có “Sắp có”, khiến sản phẩm trông chưa hoàn thiện ngay lần mở
đầu tiên. Đây là điểm cần ưu tiên cao dù các trang bên trong đã có nhiều chức năng.

Đề xuất thay bằng điểm bắt đầu có hành động thật: mở video, chọn trận, mở bảng
chiến thuật và tiếp tục báo cáo đã có. Chỉ hiện dữ liệu gần đây khi hệ thống thực
sự có nguồn; chưa có thì dùng empty state có hướng dẫn. Có thể tạm điều hướng vào
luồng đang hoàn thiện tốt nhất trong lúc xây trang tổng quan.

### Phân tích trận

Điểm tốt: bộ chọn trận rõ, tỷ số dễ nhận diện, KPI có giải thích cách tính, sân
chuyền bóng trực quan. Nguồn sự kiện và xG nhà cung cấp được nêu.

Vấn đề: scorecard và khối bốn KPI chiếm nhiều chiều cao; sân bắt đầu khoảng vùng
780 px ở màn desktop đã khảo sát. Trên mobile các KPI thành bốn thẻ dọc, đẩy sân
xuống sâu. Mũi tên lên/xuống ở thẻ thống kê chưa tương ứng một xu hướng đo được.

Đề xuất:

1. Gộp tỷ số/ngày/giải vào match header gọn, đặt bộ lọc ngay dưới.
2. KPI thành một hàng gọn desktop và lưới 2×2 mobile; giải thích dài qua nút thông tin.
3. Sân là vùng chính, thống kê mạng chuyền là panel phụ có thể thu gọn.
4. Khi hover/focus cầu thủ, làm nổi đường liên quan, hiện tên đầy đủ và chú giải
   rõ node/edge; cần đảm bảo vẫn có cách đọc tương đương trên cảm ứng.
5. Nêu ngắn phạm vi ngay bên tiêu đề biểu đồ. KPI toàn trận và mạng trước thay
   người đầu không được khiến người dùng tưởng đang cùng một cửa sổ.
6. Kiểm tra lại phạm vi mạng: màn mẫu hiện 14 cầu thủ trong khi mô tả nói trước
   lần thay người đầu. Đây là dấu hiệu cần xác minh dữ liệu, chưa kết luận lỗi
   thuật toán trong phiên đánh giá UI này.
7. Tooltip hiện gọi `touches` là “lần chạm”, trong khi backend đếm sự kiện của cầu
   thủ. Cần sửa cách diễn đạt cho đúng trước khi làm đẹp tooltip.

### Phân tích video

Điểm tốt: video, tracking, sân mini, timeline, heatmap và căn cứ có kết nối; thông
tin giới hạn của ước lượng được công khai. Không biến giả thuyết sơ đồ thành kết
luận chắc chắn là một điểm phải giữ.

Vấn đề: ở trạng thái trống, khối xử lý và nút disabled xuất hiện trước chọn file;
nhiều vùng kết quả trống cùng hiện. Với clip mẫu đã xử lý, trang dài khoảng
5.920 px desktop và 10.699 px mobile. Đây là số đo trên clip mẫu cũ được nút
“Mở clip mẫu” mở ra, không phải phép kiểm chất lượng CV mới nhất trong PROGRESS.

Đề xuất:

1. Trạng thái đầu: vùng chọn video nổi bật, giới hạn file ngắn, nút xem mẫu phụ;
   nhập tracking có sẵn chuyển vào tùy chọn nâng cao.
2. Khi xử lý: hiển thị các bước cùng trạng thái riêng, lỗi có hành động thử lại
   phù hợp. Không cần hiển thị tất cả panel kết quả chưa có dữ liệu.
3. Khi có kết quả: video/sân và timeline lên đầu; trạng thái độ phủ gọn nhưng luôn
   thấy. Câu “đã xử lý xong” cần đi kèm “tọa độ một phần” nếu đúng thực tế.
4. Chia nội dung thành tab “Tổng quan”, “Không gian đội”, “Vận động”, “Hiệu chỉnh”.
   Các nút xem đoạn căn cứ vẫn liên kết đúng trình phát và thời điểm.
5. Gộp cảnh báo lặp thành một tóm tắt phạm vi và phần mở rộng. Giữ cảnh báo riêng
   ở nơi có nguy cơ hiểu nhầm cụ thể: giả thuyết sơ đồ, hướng tấn công suy luận,
   vận động trên đoạn hiệu chỉnh. Không giấu toàn bộ giới hạn trong tooltip.
6. Heatmap cần legend màu có ý nghĩa, đơn vị hoặc chuẩn hóa rõ; không làm mượt
   vùng thiếu quan sát thành dữ liệu có thật.
7. Giảm hai tầng thanh tua/native player controls nếu trùng nhiệm vụ; vẫn đảm bảo
   điều khiển media và timeline có nhãn, focus và thao tác bàn phím phù hợp.

### Hồ sơ cầu thủ

Điểm tốt: phân biệt StatsBomb và Metrica, có search/filter, KPI đúng loại nguồn,
heatmap chuyển động và thông tin độ phủ. Không ghép danh tính chéo nguồn tùy tiện.

Vấn đề: panel danh sách chiếm gần trọn màn hình đầu trên điện thoại; hồ sơ bên
dưới khó khám phá. Nhiều nhãn 9–11 px. Bảng tham chiếu vai trò và index sự kiện
đang chiếm vị trí ưu tiên hơn nội dung chuyên môn.

Đề xuất giữ hai cột trên desktop, mobile dùng chọn cầu thủ dạng drawer/combobox,
hiện hồ sơ ngay sau chọn. Nhận diện cầu thủ gọn: số áo, short_name, đội và nguồn;
không cần khối avatar quá lớn nếu chưa có ảnh. Các tab “Tổng quan”, “Hoạt động”,
“Dữ liệu nguồn” giúp chuyển index và bảng vai trò sang nơi phù hợp. Với Metrica,
legend heatmap và thời gian quan sát nằm cạnh biểu đồ. Không dựng radar kỹ năng
nếu dữ liệu hiện tại không hỗ trợ phép đánh giá đó.

### Báo cáo HLV

Điểm tốt: có gợi ý đi cùng căn cứ, thẻ/bảng, các cú sút nguồn và SHAP; phân biệt
xG dự án với xG nhà cung cấp; thời điểm tạo không bị bịa từ thời điểm mở.

Vấn đề: khối nguồn/phiên bản nằm ngay đầu và khá lớn; trên mobile hết gần màn
đầu mới tới matchcard, còn “Điều cần xem lại” ở xa hơn. Nhiều panel liên tiếp
làm báo cáo giống trang kiểm tra mô hình hơn báo cáo đọc nhanh cho HLV.

Đề xuất thứ tự: ngữ cảnh trận/nguồn ngắn → KPI → điều cần xem lại → tình huống
căn cứ → giải thích chi tiết. Chuyển hash, lịch sử, thông tin phiên bản vào panel
thu gọn; vẫn hiển thị nhãn mẫu, phạm vi và giới hạn quan trọng. Gợi ý nên có cấu
trúc “Quan sát / Cần xem lại / Căn cứ”, tránh biến một rule thành kết luận tối ưu.
SHAP là lớp giải thích mở sâu, giữ tên feature, đơn vị log-odds và nền mô hình cho
người cần kiểm chứng. Có thể đồng bộ cú sút đang chọn với hình sân nếu đã có dữ
liệu tọa độ phù hợp; đây là đề xuất tiếp theo, chưa có thay đổi ở phiên này.

### Bảng chiến thuật

Điểm tốt: có bản sắc coach studio, sân hai đội, bộ công cụ, thư viện sơ đồ,
các pha, hoàn tác và xuất file. Nhãn “bố trí thủ công” giúp tránh nhầm với CV.

Vấn đề: toolbar dùng nhiều icon và chữ rất nhỏ, inspector dài và có cuộn riêng.
Mobile sân còn khoảng 277×180 px trong ảnh khảo sát, bóng/cầu thủ khó chọn;
toolbar và danh sách pha cần cuộn ngang. Header và điều hướng chiếm phần lớn
không gian trước khi tới sân.

Đề xuất:

- Ưu tiên chế độ tập trung vào sân/toàn màn hình với lối thoát rõ ràng.
- Inspector chia “Bố trí / Hiển thị / Kế hoạch”; trên mobile mở dưới dạng panel
  hoặc sheet khi cần, giữ sân ở vị trí trung tâm.
- Công cụ có tooltip khi hover/focus và nhãn công cụ đang dùng luôn thấy trên
  cảm ứng; tăng vùng chạm mà không đổi tọa độ vật thể.
- Thêm khả năng phóng/di chuyển vùng nhìn nếu làm giai đoạn tương tác tiếp theo;
  danh sách đối tượng hiện có tiếp tục là cách chọn thay thế khi vật thể quá nhỏ.
- Thanh pha hiển thị pha hiện tại rõ, tên dễ sửa, vị trí “thêm” không chen lên tên
  pha; trạng thái lưu “trình duyệt này” rõ, giữ JSON làm đường chuyển máy.
- Giữ tím cho chức năng biên tập có chủ đích nhưng đồng bộ font, nút, border,
  radius với phần còn lại; không cần sao chép toàn bộ giao diện trang tham khảo.

## Accessibility và trạng thái

- W3C SC 1.4.3 quy định tương phản chữ thường tối thiểu 4,5:1, chữ lớn 3:1,
  có các ngoại lệ. Footer `#596473` trên nền `#0b0f14` khoảng 3,20:1; cần tăng
  tương phản khi phần chữ đó truyền tải thông tin. Chưa suy rộng thành kết luận
  toàn app đạt hoặc không đạt WCAG.
- W3C SC 2.5.8 có mức 24×24 CSS px hoặc đáp ứng ngoại lệ về khoảng cách/chức
  năng tương đương. Không coi bounding box input ẩn hay đối tượng SVG dày đặc
  là bằng chứng tự động không đạt. Mục tiêu 44 px ở trên nhằm dễ thao tác hơn.
- Có focus-visible và aria-live tại một số nơi; cần chuẩn hóa cho các nút custom,
  tab, menu và điều khiển biểu đồ. Không chỉ dựa vào màu để biểu diễn đội/trạng thái.
- Chưa thấy xử lý `prefers-reduced-motion`/`useReducedMotion` trong frontend;
  bổ sung khi chuẩn hóa chuyển cảnh. Không thêm animation dài vào phân tích.
- Phân biệt loading, rỗng, lỗi kết nối, không hỗ trợ và chỉ đủ dữ liệu một phần.
  Skeleton nên gần cấu trúc kết quả để giảm nhảy bố cục; lỗi có nút thử lại đúng
  tác vụ và không che mất kết quả cũ còn hợp lệ.
- Thay chữ kỹ thuật “Backend: OK” bằng trạng thái dễ hiểu khi cần; bảng chiến
  thuật lưu cục bộ không nên tạo cảm giác mọi thao tác phụ thuộc backend.

Nguồn tiêu chí:
[W3C Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html),
[W3C Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).

## Thứ tự thực hiện đề xuất

| Đợt | Phạm vi | Kết quả cần thấy |
| --- | --- | --- |
| 1 — ưu tiên cao | Typography, độ tương phản, bỏ icon xu hướng không có baseline, sửa nhãn lần chạm, trang đầu có hành động thật | Dễ đọc và không gây hiểu sai ngay từ lần mở đầu |
| 2 — cấu trúc | Chuẩn hóa header/KPI/nút/tab/source badge; rút ngắn Match và Reports; video theo giai đoạn | Nội dung chính xuất hiện sớm, chi tiết kỹ thuật mở khi cần |
| 3 — mobile | Điều hướng, chọn cầu thủ, tab video, inspector chiến thuật và sân tập trung | Dễ chọn và đọc, giảm cuộn không cần thiết |
| 4 — hoàn thiện | Tương tác chart/focus, legend heatmap, empty/error/loading, reduced motion | Cùng một chất lượng sử dụng trên mọi trang |

Các đợt là đề xuất triển khai, chưa phải các thay đổi đã làm. Mỗi đợt nên có ảnh
trước/sau ở cùng dữ liệu; kiểm build/lint và các kiểm thử có liên quan. Kiểm tra
ít nhất desktop 1440×1000, tablet 1024×768 và mobile 390×844; bàn phím, zoom 200%,
chữ tiếng Việt dài, dữ liệu thiếu và kết quả từng phần. Không đo thành công chỉ
bằng việc trang ngắn hơn: phải giữ được nguồn, phạm vi, căn cứ và khả năng đọc.

Không cần thêm dependency, đổi API hoặc sửa hợp đồng tọa độ để bắt đầu các đợt
thiết kế trên. Việc kiểm tra lại phạm vi mạng chuyền là đầu việc xác minh riêng,
không nên che bằng thay đổi nhãn hoặc trình bày đẹp hơn.

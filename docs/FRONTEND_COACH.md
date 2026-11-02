# Bước 8c — báo cáo HLV trên giao diện

## Bổ sung thẻ/bảng, phiên bản và lịch sử — 02/11/2026

Theo yêu cầu tích hợp phần phù hợp từ football-predictions, trang `/reports`
thêm chuyển **Thẻ / Bảng** ở mục Điều cần xem lại. Hai cách xem dùng cùng
những gợi ý đã qua parser, không tạo luật, dự đoán hay điểm tin cậy mới.
Bảng có tiêu chí nhóm, số cú sút/tổng, tỷ lệ nhóm, xG trung bình và nút mở
căn cứ. SHAP trung bình của nhóm vẫn xem được ở cả hai cách; cú sút và
giải thích bên dưới dùng chung. Đổi đội/gợi ý không giữ cú sút đội trước.
Bảng cuộn ngang khi không đủ chiều rộng, có caption/th/region để đọc bằng
bàn phím hoặc công cụ hỗ trợ. Thành phần: CoachRecommendations.tsx.

Mục **Nguồn và phiên bản báo cáo** bổ sung:

- Thời điểm tạo nếu JSON có trường ISO `generated_at`; nếu không, ghi rõ
  chưa có. Báo cáo hiện tại không có thời điểm tạo; không tự dùng ngày mở
  file, ngày trận hay ngày commit để thay thế.
- Lần mở trên trình duyệt theo UTC+7; không coi đây là độ mới của dữ liệu.
- SHA256 của JSON.stringify(report.original) để phân biệt bản nội dung.
  Khoảng trắng JSON không tạo bản mới; thứ tự khóa JSON vẫn ảnh hưởng hash.
- Chi tiết hash mô hình, revision dữ liệu và hash sự kiện nếu JSON ghi mã
  đúng định dạng. Hiển thị mã không phải xác minh độc lập nguồn dữ liệu.

**Báo cáo gần đây** lưu bản JSON đầy đủ của các báo cáo đã mở hợp lệ trong
localStorage của origin hiện tại. Đây là lịch sử mở báo cáo trên trình
duyệt, không phải danh sách mọi job chạy trên backend. Không gửi file tới
server hoặc dịch vụ ngoài, không đổi DATA_CONTRACT hoặc thêm thư viện.

- Tối đa5bản, tổng ngân sách2MiB ước lượng theo chuỗi UTF-16, gồm metadata.
  Khi đầy, bỏ bản có lần mở cũ nhất. Cùng nội dung chỉ cập nhật tên/lần mở;
  bản khác của cùng trận vẫn được giữ riêng. Giữ thứ tự theo timestamp khi
  tác vụ bất đồng bộ hoàn tất khác thứ tự.
- Báo cáo trên ngân sách lịch sử vẫn mở/xuất được theo giới hạn10MB cũ.
  Có thông báo không lưu được; không xóa lịch sử cũ để cố lưu file quá lớn.
- Mở lại phải khớp SHA256, parser kiểm lại schema/số liệu/SHAP/căn cứ và
  kiểm metadata đội/trận khớp nội dung. Lịch sử hỏng được báo, không âm
  thầm ghi đè. Lỗi quyền/quota của storage giữ báo cáo đang xem.
- Nút mở file và mở từ lịch sử cùng dùng generation guard để kết quả đọc
  cũ không ghi đè lựa chọn mới. Sau reload vẫn có thể mở lại bản đã lưu.
- Dữ liệu gắn với origin: localhost và127.0.0.1 hoặc port khác có kho riêng;
  trình duyệt riêng tư/xóa dữ liệu site có thể làm mất lịch sử. Tải JSON
  vẫn là cách giữ bản độc lập với cache trình duyệt.

Kiểm tra: `cd frontend`, chạy `npm test`, `npm run build`, `npm run lint`.
23test Node đạt, gồm8test lịch sử mới (khôi phục, dedup/phiên bản, thứ tự/
giới hạn5, sửa nội dung/metadata, storage hỏng/quota, file quá lớn, ngân sách,
ngày tạo thiếu). Còn cảnh báo FastRefresh và bundle size đã có. Không đổi
backend nên không chạy lại test Python cho phần giao diện này.

Đã kiểm trực tiếp bằng in-app browser trên mẫu8650: thẻ↔bảng, đổi Brazil/
Belgium (13/25=52% và6/8=75%), chọn Chadli đúng7:35/#330, SHAP nhóm,
revision/hash, lịch sử còn sau reload và mở bản đã lưu (có nút Mở lại mẫu).
Ảnh kiểm tại `docs/screenshots/coach-report-table-history.png`; không tuyên
bố đã kiểm mọi kích thước màn hình hoặc file nhập tùy ý qua UI. Các lỗi
history/giới hạn/schema được kiểm tự động. Tính toán xG/advisor không đổi.

Các phần dưới ghi lại luồng và kiểm tra ban đầu.

Ngày 26/10/2026. Trang `/reports` đã thay trang chờ bằng báo cáo xG và
gợi ý rà soát có căn cứ. Đọc JSON `shot_advisor_v1` đã có ở bước 7,
không đổi DATA_CONTRACT, thêm API, thư viện, mô hình hoặc luật gợi ý.

## Sử dụng

Từ `frontend`, chạy `npm run dev`, mở `/reports`. Báo cáo mẫu trận 8650
tự tải nếu đã chuẩn bị asset cục bộ. Có thể:

- Chọn Brazil hoặc Belgium để xem số cú sút hợp lệ, tổng/trung bình xG
  dự án và số gợi ý. Đây không phải tỷ số trận hoặc xG StatsBomb.
- Xem định nghĩa nhóm làm căn cứ, số lượng/tỷ lệ và xG trung bình. Mở
  **Xem SHAP trung bình của nhóm** để xem giá trị feature và đóng góp
  trung bình hỗ trợ diễn giải của luật.
- **Xem N cú sút căn cứ** hoặc bật **Xem tất cả cú sút của đội**; chọn
  một pha để xem người sút, phút/hiệp/index, xG, đủ tám feature và SHAP.
- Mở **Event ID nguồn** để truy vết đầy đủ, hoặc phần phương pháp/giới
  hạn để đọc phạm vi và hash mô hình.
- Mở báo cáo advisor JSON khác, tối đa 10 MB/10.000 cú sút. Đọc tại
  trình duyệt, không upload lên backend. Đổi báo cáo/đội/gợi ý bỏ lựa
  chọn cũ, không giữ cú sút của đội khác.
- **Tải JSON** tạo tải xuống bằng object URL của toàn bộ báo cáo gốc đã
  đọc hợp lệ, gồm cả hai đội và provenance; không chỉ xuất phần đang lọc,
  không gửi báo cáo đi dịch vụ ngoài. Chưa thêm xuất PDF/Word.

Có loading, lỗi đọc/schema/số liệu không khớp, thử lại mẫu, báo cáo không
có đội/cú sút và trạng thái chưa đủ dữ liệu/không luật nào đạt. Gợi ý vẫn
được ghi là bản nháp sau trận; không ép sinh khi nguồn không có.

## Diễn giải số liệu

Mẫu có 33 cú sút không penalty trong hiệp 1–4. Brazil 25 cú sút, tổng
xG 2,990; nhóm xG <0,08 gồm 13/25 (52%), xG trung bình 0,049. Belgium
8 cú sút, tổng 0,558; nhóm thấp gồm 6/8 (75%), trung bình 0,045.
Các tỷ lệ này là **tỷ lệ nhóm căn cứ**, không phải confidence của AI hoặc
accuracy tư vấn. Đây là trận thuộc tập validation của mô hình bước 6;
nhãn này hiện ngay trên trang, không gọi là đánh giá độc lập.

SHAP dùng log-odds. Biểu đồ xanh/hồng thể hiện chiều tăng/giảm dự đoán
so với nền mô hình, không phải feature tốt/xấu hay điểm phần trăm cải
thiện. Có cả feature bằng 0 với đóng góp khác 0, vì giải thích so với
phân bố nền chứ không phải phép nhân giá trị feature với một hệ số.

Trang hiển thị base + tổng SHAP = margin, rồi sigmoid = xG, dùng đúng
66 cây tốt nhất như bước 7. SHAP nhóm và SHAP từng cú sút được phân biệt
bằng tiêu đề/phạm vi. Không vẽ bản đồ vị trí sút: báo cáo chỉ có feature
khoảng cách/lệch ngang tuyệt đối, không đủ thông tin để tự gán hướng y.

Ngưỡng luật giữ nguyên, không tạo gợi ý mới trong trình duyệt. Không
kết luận nên chuyền hơn sút, đổi sơ đồ/thay người hoặc hiệu quả nhân quả.
Giới hạn xG/advisor vẫn theo `XG_BASELINE.md` và `ADVISOR_BASELINE.md`.

## Kiểm tra JSON

`frontend/src/lib/coachReport.ts` tạo kiểu view nội bộ. Kiểm kind/source/
post-match, số hữu hạn, xác suất 0–1, cờ nhị phân, hiệp 1–4, event ID/index
không trùng và đúng đội, chỉ hai đội của cùng báo cáo. Kiểm phương pháp/
đơn vị SHAP và số cây bằng best_iteration+1.

Từng cú sút được tính lại base + tám đóng góp, so với margin (1e-5) và
sigmoid/xG (1e-6); các base phải cùng mô hình. Tính lại tổng/trung bình
xG đội. Với mỗi gợi ý, kiểm đủ và đúng tập event theo luật, tử số/mẫu số/
tỷ lệ, xG/feature/SHAP trung bình, dấu các feature hỗ trợ, ngưỡng số mẫu
và trạng thái. Từ chối báo cáo sai, không âm thầm sửa số hoặc bỏ một
phần gợi ý. Chỉ hỗ trợ ba luật đã có ở protocol bước 7.

Đây là kiểm tra nhất quán nội bộ, không chứng minh tính xác thực của mọi
file người dùng mở hoặc hiệu quả chuyên môn của gợi ý. Mẫu trên máy
được kiểm riêng với snapshot/hash nguồn và mô hình trước khi sao chép.

## Chuẩn bị mẫu

Từ gốc repo, sau khi có model và advisor bước 6–7:

```powershell
.\.venv\Scripts\python.exe -m backend.advisor.prepare_coach_demo
```

Helper kiểm `advisor_8650_v1_final/advisor.json` bằng hash trong
`docs/fixtures/advisor_result_v1.json`, kiểm model/metadata và sự kiện
nguồn. Sau đó sao chép sang `frontend/public/coach-demo/advisor.json`
cùng manifest, yêu cầu thư mục output mới, không ghi đè hoặc huấn luyện
lại. Thư mục public này ignore Git; Vite sao chép vào dist nếu đã chuẩn
bị trước build. Không commit bản ghi cú sút hoặc dữ liệu nhà cung cấp.

Hash báo cáo mẫu:
`49698a9fd6a19dd20f55acbab525335cfd1007ecdfef22779fde5ddd40f4b20b`.
Model SHA256:
`7f46f5bc2ea89e3d73fa432b44725407574d8ed3b8446d7fc5e3d7cb83989c2d`.

## Nghiệm thu

Từ `frontend`: `npm run test`, `npm run build`, `npm run lint`.
Tổng **12 Node test qua**, gồm bốn test mới cho báo cáo: đọc/truy vết/
round-trip payload xuất JSON, từ chối tổng sai/SHAP không khớp, căn cứ
thiếu/trùng/khác đội và dấu hỗ trợ sai, báo cáo rỗng/ít mẫu và hiệp lỗi.

Đã parse 33 cú sút, hai đội/hai gợi ý thật. Kiểm tra trình duyệt:

- Brazil 13/25, Belgium 6/8; đổi đội xóa nhóm/cú sút cũ.
- Bật toàn bộ Belgium thấy tám pha, tắt trở về sáu pha căn cứ.
- Chọn Fellaini index 508, phút 12:05: xG 0,059 và event ID
  `44ec04e4-1a9a-4aaf-a8a5-04cb997a203f`; chọn De Bruyne index 85:
  xG 0,038, margin −3,2424 từ nền −2,2673 + SHAP −0,9751.
- SHAP nhóm Belgium: khoảng cách −0,1598, góc −0,6944, lệch ngang
  −0,0292 log-odds; khác với các đóng góp của cú sút đang chọn.
- 1280 px có hai cột căn cứ/giải thích; 375 px một cột, đủ tám thanh
  SHAP, không tràn ngang. Đã sửa thẻ gợi ý mobile thành xếp dọc, giữ
  giải thích dùng đủ chiều rộng. Không có console error; trả viewport
  về mặc định sau kiểm tra.
- Ảnh `data/processed/frontend_coach_review_v1/desktop.jpg`.

Payload xuất JSON được kiểm bằng round-trip trong test; không tự tải file
qua trình duyệt sang thư mục ngoài workspace khi nghiệm thu.
Build/lint exit 0; còn cảnh báo bundle >500 kB và Fast Refresh button UI.
Python từ gốc repo:
`pytest -q --basetemp .tmp/pytest_frontend_coach_full_v1`:
**280 passed, 1 network deselected**, cảnh báo Starlette/SHAP cũ.

Các trang chức năng cơ bản của bước 8 đã có; dashboard Tổng quan vẫn là
trang chờ của shell. Chưa có job upload/xử lý video qua API hoặc nghiệm
thu chất lượng CV/chiến thuật/advisor độc lập. Bước tiếp theo theo ROADMAP
là đánh giá tổng thể, số liệu báo cáo và slide (bước 9).

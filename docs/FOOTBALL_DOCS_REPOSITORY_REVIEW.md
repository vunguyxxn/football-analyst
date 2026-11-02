# Đánh giá withqwerty/football-docs — 02/11/2026

## Kết luận và phạm vi

Có giá trị cho chuẩn hóa chỉ số, tra cứu tài liệu và kiểm nguồn; giá trị trực
tiếp cho sửa tracking/hiệu chỉnh sân hiện tại thấp. Đề xuất học cách tổ chức
tri thức trước, cân nhắc MCP hỗ trợ lập trình sau; chưa thêm dịch vụ này vào
đường xử lý video hoặc báo cáo HLV.

Phiên này chỉ đọc/đánh giá theo yêu cầu. Không sửa thuật toán, API, frontend,
DATA_CONTRACT hoặc dependency; không cài/chạy MCP, không tải model/dataset.
Bản sao mã để đọc ở `.tmp/repo_audits/football-docs` (Git ignore).

Nguồn: [withqwerty/football-docs](https://github.com/withqwerty/football-docs),
khóa commit `b1fb1c175226b9726ac31524bf232d54cf960745`.
`package.json` tại commit này ghi phiên bản `0.17.4`, Node `>=22.13.0`.
Các liên kết mã bên dưới ghim commit; không suy tính năng từ nhánh tương lai.

## Những phần thực sự đã đọc

| Thành phần | Nguồn trong repo | Giá trị với hệ thống |
| --- | --- | --- |
| MCP stdio | `src/index.ts`, `src/tools.ts` | Tra cứu tài liệu provider, so sánh khái niệm, thông báo kết quả chỉ khớp một phần/không có dữ liệu |
| Chỉ mục tài liệu | `src/ingest.ts`, `src/data-format.ts`, `src/sqlite.ts` | Chia Markdown theo đề mục, SQLite FTS5, lưu URL/loại nguồn/phiên bản/ngày thu thập; không bắt buộc vector DB |
| Metric cards | `src/metrics.ts`, `metrics/cards/*.toml`, `metrics/cards.json` | Một khái niệm có nhiều variant ID; mỗi biến thể có công thức, vùng sân, quy tắc đếm, nguồn, giới hạn và trạng thái exact/approximation |
| Mã tham chiếu | `metrics/reference/football_metrics/{ppda,territory,xt}.py` | Hàm tính trên JSON sự kiện StatsBomb gốc, không phải bảng CSV chuẩn hóa của mình |
| Kiểm số liệu | `metrics/tests/{conftest,test_reference}.py`, `metrics/fixtures.json` | Khóa commit/SHA256 dữ liệu; đối chiếu kết quả hàm với số kỳ vọng, mặc định sai số 1e-4 |
| Kiểm tài liệu/tra cứu | `src/__tests__/statsbomb-truth.test.ts`, `golden-retrieval.test.ts` | Kiểm ID/nhãn với tập tham chiếu; câu hỏi cố định phải tìm được bằng chứng cần thiết |
| Tài liệu mở rộng | `docs/{statsbomb,kloppy,reep}/`, `docs/metric-cards/` | Quy ước nguồn, chuẩn hóa provider, liên kết danh tính; dùng làm điểm tìm tới tài liệu gốc |

Repo cung cấp công cụ đọc/tìm bài nghiên cứu và kiểm trích dẫn, nhưng phiên
này chưa chạy chúng. Việc có test trong mã không chứng minh test hiện tại đều
đạt; chưa cài dependency hoặc chạy test của repo bên ngoài.

## Có thể áp dụng thế nào

### 1. Chuẩn hóa định nghĩa chỉ số — ưu tiên cao

Học cấu trúc metric card cho các chỉ số đã có: xG mô hình của mình, xG từ
StatsBomb, tỷ lệ chuyền thành công và các số đo hình học video. Ghi công
thức, đơn vị, nguồn, phạm vi và điều kiện thiếu dữ liệu trong tài liệu nội
bộ trước; không cần thêm trường vào `MetricItem` hoặc đổi API.

`backend/tactics/xg.py` đã có mô hình pre-shot và kiểm xác suất; metric card
không thay thế mô hình đó. Hàm cộng `shot.statsbomb_xg` của repo tham khảo là
tổng dự đoán do provider cung cấp, không phải bộ huấn luyện xG mới. Giữ rõ
hai nguồn trong giải thích và đánh giá.

Ví dụ PPDA có biến thể đếm mọi đường chuyền và biến thể chỉ đếm chuyền thành
công, danh sách hành động phòng ngự cũng khác. Không nên thêm một nhãn PPDA
chung rồi so với mọi nguồn. xA theo mô hình trên đường chuyền cũng khác xG
của cú sút được kiến tạo (`xg_assisted`); không dùng hai tên thay nhau.

### 2. Công cụ tra cứu cho agent phát triển — khả thi, chưa cài

MCP độc lập có thể giúp tra event type, ý nghĩa trường, API và nguồn phương
pháp khi viết mã. Node 24 của dự án đáp ứng yêu cầu Node khai báo; đây mới
là tương thích phiên bản, chưa phải bằng chứng chạy tốt trên máy Windows.

Nếu được chọn triển khai ở phiên sau: ghim phiên bản gói và snapshot chỉ mục;
ban đầu dùng `FOOTBALL_DOCS_DATA=bundled`, `FOOTBALL_DOCS_PAPERS=off` cho
tra cứu tài liệu có thể tái lập. Đặt `XDG_DATA_HOME`, cache npm và mọi dữ
liệu phát sinh trong repo để tuân thủ quy định không ghi ngoài workspace.
Không thêm vào `backend/requirements.txt` hay `frontend/package.json` chỉ
để phục vụ agent. Công cụ phát triển mới vẫn cần duyệt theo quy định dự án.

### 3. Chỉ số sự kiện mới — khả thi có điều kiện, chưa triển khai

| Hướng | Đầu vào và điều kiện | Ưu tiên đề xuất |
| --- | --- | --- |
| PPDA theo một variant StatsBomb xác định | Pass/outcome, Duel/type, Interception, Dribbled Past, Foul, period và vị trí; mẫu số 0 phải là thiếu giá trị | Sau khi đã tài liệu hóa chỉ số hiện có |
| Field tilt | Chốt dùng pass hay touch, danh sách sự kiện, ranh giới một phần ba sân và kỳ thi đấu | Cùng nhánh StatsBomb; không thay bằng tỷ lệ người trong heatmap |
| Progressive passes/carries | Vị trí đầu/cuối, thành công/thất bại, bóng chết, định nghĩa khoảng cách và đơn vị cụ thể | Sau PPDA; cần test ranh giới và hướng tấn công |
| xT | Chuỗi sự kiện có vị trí đầu/cuối, tập hành động, lưới giá trị có nguồn/phiên bản và quyền sử dụng phù hợp | Nghiên cứu sau; không chỉ cài thêm thư viện để có nhãn xT |

Đây là đề xuất, không phải tính năng đã được phép thêm. Theo ROADMAP hiện
tại, không khởi động lại nhận diện chuyền/sút từ video. Các chỉ số trên dùng
dữ liệu sự kiện đủ trường; tracking cầu thủ đơn thuần không đáp ứng đầu vào.

### 4. Căn cứ cho báo cáo HLV — học cách tổ chức, chưa nối tự động

`backend/tactics/video_tactics.py` đã nối quan sát/số đo với điều kiện áp
dụng, hành động, đánh đổi và nguồn. Có thể bổ sung tài liệu phương pháp có
phiên bản và câu hỏi kiểm nguồn theo cách repo làm. Một bài báo giải thích
pressing không chứng minh đội trong clip đang pressing hoặc nên đổi sơ đồ;
khuyến nghị vẫn phải dựa trên đoạn quan sát hợp lệ và số đo thực tế.

Nếu sau này cần hỏi đáp tài liệu, có thể nghiên cứu FTS5 với tài liệu đã
duyệt trước khi thêm vector DB/LLM. Không đưa nguyên kết quả tìm kiếm từ
Internet thành kết luận chiến thuật cho trận của người dùng.

## Những điểm không được chép nguyên

1. **Chiều trục y:** `docs/statsbomb/coordinate-system.md` có hàm sang mét
   dùng `y / 80 * 68`, giữ gốc trên. Dự án dùng gốc dưới:
   `y_m = (80 - y) * 68 / 80` tại `backend/common/pitch.py`. Công thức
   tham khảo không khớp hợp đồng của mình; không thay hàm hiện có.
2. **Ngưỡng PPDA:** mã gốc dùng x>=48 cho hành động đội pressing và x<72
   cho chuyền đối thủ trên lưới120. Sang hệ105m lần lượt là42m và63m,
   vì mỗi đội StatsBomb đều tấn công về x tăng. Không dùng cùng một vùng
   x cho cả hai đội hoặc lật thêm lần nữa. Tracking video có quy ước khác.
3. **Dạng dữ liệu:** mã tham chiếu đọc nested JSON (`event['type']['name']`,
   `pass.outcome`); loader mình dùng DataFrame/CSV với nhiều trường phẳng và
   bỏ `location` sau chuẩn hóa. Cần adapter được kiểm thử hoặc dùng nguồn
   JSON gốc có khóa phiên bản; kiểm cache có đủ trường, không coi thiếu
   `outcome` toàn bộ dataset là mọi đường chuyền thành công.
4. **Danh tính:** Reep giúp ghép ID giữa provider. Nó không xác định cầu thủ
   thật từ ByteTrack ID; vẫn cần bước gắn danh tính video riêng. Với một
   nguồn StatsBomb hiện tại, chưa cần thêm Reep/kloppy/socceraction.
5. **Quyền tái sử dụng:** README/package khai báo MIT, nhưng điều đó không
   cấp quyền chung cho dữ liệu provider, bài báo hay lưới xT bên ngoài.
   `metrics/fixtures.json` ghi lưới xT tham chiếu chưa nêu licence và tải
   lúc test; không đóng gói lưới này vào sản phẩm chỉ vì repo khai báo MIT.

## Thứ tự khuyến nghị và nghiệm thu nếu triển khai sau

1. Giữ ưu tiên sửa biên/mốc sân, phân vai và kiểm độc lập trên nhiều clip:
   baseline trong PROGRESS hiện có0/3clip tạo được phân tích sân tự động.
   football-docs không cung cấp model/homography để giải quyết nút thắt đó.
2. Tài liệu hóa các chỉ số đã có, tách rõ xG tự huấn luyện/provider và số đo
   video; mỗi card phải truy được công thức cùng giới hạn thực tế.
3. Nếu bổ sung PPDA/field tilt ở nhánh sự kiện, chốt variant và adapter trước.
   Kiểm fixture cùng commit/hash với kết quả tham chiếu; thêm ca mẫu số0,
   thiếu trường, biên vùng sân, đổi đội, hiệp phụ và loại luân lưu. Số liệu
   trận chuẩn trong card là đối chiếu tính toán, không chứng nhận hiệu quả
   huấn luyện hoặc tính đúng cho mọi provider.
4. MCP cho agent là hạng mục công cụ tùy chọn; thử smoke test tìm tài liệu
   đúng nguồn, không tìm thấy phải báo rõ, và kiểm mọi ghi file nằm trong repo.

## Kiểm tra phiên đánh giá

Đã đối chiếu source với mã/dữ liệu hợp đồng cục bộ và kiểm `git diff --check`.
Không sửa mã chạy nên không chạy lại test backend/frontend; không tuyên bố
đã kiểm runtime MCP hoặc tái lập số liệu tham chiếu của repo bên ngoài.

Nguồn mã ghim:
[metric cards](https://github.com/withqwerty/football-docs/tree/b1fb1c175226b9726ac31524bf232d54cf960745/metrics),
[PPDA](https://github.com/withqwerty/football-docs/blob/b1fb1c175226b9726ac31524bf232d54cf960745/metrics/reference/football_metrics/ppda.py),
[tọa độ](https://github.com/withqwerty/football-docs/blob/b1fb1c175226b9726ac31524bf232d54cf960745/docs/statsbomb/coordinate-system.md),
[chỉ mục](https://github.com/withqwerty/football-docs/blob/b1fb1c175226b9726ac31524bf232d54cf960745/src/data-format.ts),
[MCP](https://github.com/withqwerty/football-docs/blob/b1fb1c175226b9726ac31524bf232d54cf960745/src/index.ts).

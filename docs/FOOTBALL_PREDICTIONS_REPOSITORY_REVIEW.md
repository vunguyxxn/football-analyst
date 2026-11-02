# Đánh giá karidasd/football-predictions — 02/11/2026

## Kết luận

Repo là dashboard dự đoán kết quả/kèo bóng đá lấy dữ liệu API-Football,
chạy Python bằng GitHub Actions rồi phục vụ JSON/HTML/CSS/JavaScript tĩnh.
Giá trị tham khảo cho hệ thống hỗ trợ HLV chủ yếu ở cách trình bày và tổ
chức cập nhật dữ liệu; không có thành phần CV, hiệu chỉnh sân, phân tích
đội hình hoặc mô hình xG để cải thiện pipeline hiện tại.

Đọc tại commit `6e82ae048919b27222a3c56810f9dc8e331560c2`, commit cuối ghi
01/11/2026 13:18:01 UTC. Bản sao chỉ để đọc trong
`.tmp/repo_audits/football-predictions` (Git ignore, không checkout media).
Không cài dependency, chạy script repo, dùng API key hay gọi API-Football.
Không sửa chức năng hoặc hợp đồng dữ liệu của dự án mình.

## Những gì thực sự có

| Thành phần | Mã đã đọc | Hoạt động |
| --- | --- | --- |
| Thu thập | `scripts/fetch_predictions.py` | Gọi fixtures, predictions và odds từ API-Football; lấy tối đa10fixture và lưu tối đa5dự đoán/ngày |
| Dữ liệu dự đoán | Cùng script | Lưu đội/giải/logo, phần trăm thắng-hòa-thua, advice của provider, short_tip, GG/NG, Over/Under và odds vào JSON |
| Chấm kết quả | `scripts/fetch_results.py` | Đọc dự đoán, lấy tỷ số, so short_tip với kết quả và cộng bộ đếm; log giữ100mục |
| Giao diện | `index.html`, `script.js` | Chuyển thẻ/bảng bằng class CSS; thanh tỷ lệ, mục nổi bật, lịch sử, widget livescore, nhạc nền |
| Tự động hóa | `.github/workflows/*.yml` | Lịch06:17 UTC và23:22 UTC, có chạy tay, commit data/*.json; khác phút so với README mô tả |

Không thấy mã nguồn huấn luyện, chia train/test, fit model hoặc predict_proba
trong các script Python tracked. `requirements.txt` liệt kê scikit-learn,
XGBoost/joblib nhưng script đã đọc không dùng để huấn luyện/dự đoán cục bộ.
Có bytecode `scripts/__pycache__/ml_utils.cpython-314.pyc` trong cây Git,
không có source tương ứng ở commit này; không thực thi hay suy chức năng
từ bytecode. Vì vậy chưa có căn cứ gọi đây là mô hình ML do repo tự xây
hoặc xác nhận các tuyên bố “highly accurate/profitable” trong README.

## Điểm có thể học cho football-analyst

1. **Tách dữ liệu và hiển thị:** script xuất JSON, frontend đọc để dựng UI.
   Dự án mình đã có API JSON và snapshot/demo; có thể học cách trình bày
   báo cáo gọn, không chuyển xử lý video/GPU sang GitHub Actions/Pages.
2. **Chế độ thẻ và bảng:** phù hợp nghiên cứu cho báo cáo HLV hoặc danh sách
   cửa sổ chiến thuật. Cùng một dữ liệu có thể xem tóm tắt hoặc so nhiều
   dòng; chưa cần thêm thư viện. Đây là đề xuất, chưa triển khai.
3. **Lịch sử kết quả:** học ý tưởng truy xuất lần chạy, nhưng mình cần giữ
   version/hash/video/model/phạm vi dữ liệu và kiểm chất lượng rõ ràng.
   Các pitch_runs/snapshot hiện có đã làm một phần; không thay bằng bộ đếm
   accuracy tổng không tái lập được.
4. **Hiển thị độ mới:** snapshot repo cho thấy cần hiện ngày thu thập, ngày
   trận và trạng thái lỗi/rỗng riêng. Không gán lỗi API thành “không có trận”.

Không đề xuất tích hợp tỷ lệ cược, VIP bet, nhạc nền hoặc dự đoán thắng/thua:
ROADMAP của dự án loại dự đoán kết quả trận; các phần đó không phục vụ mục
tiêu phân tích video/chiến thuật HLV hiện tại. Chưa có nhu cầu thêm provider
API-Football hoặc dependency từ repo này.

## Những hạn chế phát hiện khi đọc mã

- **Đường dẫn trạng thái trong updater không nhất quán:** fetch_predictions
  đọc `f['fixture']['status']['short']`; fetch_results kiểm
  `result.get('status', {}).get('short')` ở root sau khi nhận cùng loại
  phần tử fixture. Với cấu trúc dùng trong script đầu, nhánh chấm kết quả
  của script sau không chạy. Chưa chạy API sống để đo hậu quả thực tế.
- Updater chỉ truy vấn lại mục `Pending`; mục đã ghi `In Play` không được
  truy vấn lại bởi vòng lặp đó. Không nên suy “history đầy đủ” từ giao diện.
- **Cách chấm không phải accuracy thắng-hòa-thua đơn:** dùng
  `actual_1x2 in short_tip`. Tip1X/X2 chấp nhận hai kết quả; mặc định1X2
  chấp nhận cả ba. Không thể so trực tiếp tỷ lệ này với phân loại ba lớp.
- `history.json` ghi220/314=70,06%, nhưng chỉ còn100dòng log;90/100dòng là
  tip1X hoặc X2. Không đủ314bản ghi để tái lập bộ đếm từ snapshot hiện có.
  Không kết luận mô hình đạt70,06% accuracy ba lớp hoặc hiệu quả đặt cược.
- `home_goals_pred`/`away_goals_pred` bị xử lý như số điểm kỳ vọng: thay
  ký tự dấu trừ bằng0 rồi cộng để suy Over/Under; GG/NG cũng chỉ suy theo
  chuỗi khác0. Không có mô hình xác suất riêng hoặc đánh giá xác nhận cho
  hai đầu ra này trong mã đã đọc; không nhầm với xG từng cú sút của mình.
- Mục nổi bật chọn giá trị p×odds lớn nhất từ mốc0, không bắt buộc vượt1;
  đánh dấu trên từng odds dùng1,1. Không suy nhãn nổi bật luôn có lợi thế.
- Thiếu key/API thất bại có thể trở thành danh sách rỗng rồi ghi đè JSON;
  requests không đặt timeout hay retry. UI nhánh matches=[] diễn giải
  thành không có lịch thi đấu, không phân biệt lỗi nguồn.
- Workflow công khai có credential ghi trực tiếp, HTML có khóa widget.
  Không sao chép, thử hoặc ghi lại giá trị khóa; khi tự thiết kế giữ secret
  trong cấu hình phù hợp, không đưa credential server vào frontend.

## Snapshot và kiểm tra

Đọc JSON trực tiếp từ commit, không lấy trạng thái live website làm bằng
chứng. `predictions.json` và `predictions_today.json` đều ngày01/11/2026,
matches=[]; yesterday ngày22/06/2026 và tomorrow ngày24/06/2026, mỗi file
5trận. Script main hiện chỉ cập nhật today/alias; không coi tên file là bảo
đảm ngày dữ liệu còn mới. Không thấy bộ test tracked trong cây Git này.

Đã kiểm cây file, tìm dấu huấn luyện/inference trong script, tổng hợp bộ đếm
và100log JSON; kiểm riêng biểu thức fallback1X2 nhận cả ba kết quả. Đây là
kiểm tĩnh và kiểm dữ liệu snapshot, không là benchmark mô hình/API sống.
Thay đổi dự án chỉ gồm tài liệu; kiểm `git diff --cached --check`, không
chạy lại backend/frontend hoặc sửa các thay đổi CV song song.

Nguồn ghim:
[README](https://github.com/karidasd/football-predictions/blob/6e82ae048919b27222a3c56810f9dc8e331560c2/README.md),
[fetch_predictions.py](https://github.com/karidasd/football-predictions/blob/6e82ae048919b27222a3c56810f9dc8e331560c2/scripts/fetch_predictions.py),
[fetch_results.py](https://github.com/karidasd/football-predictions/blob/6e82ae048919b27222a3c56810f9dc8e331560c2/scripts/fetch_results.py),
[script.js](https://github.com/karidasd/football-predictions/blob/6e82ae048919b27222a3c56810f9dc8e331560c2/script.js),
[data](https://github.com/karidasd/football-predictions/tree/6e82ae048919b27222a3c56810f9dc8e331560c2/data).

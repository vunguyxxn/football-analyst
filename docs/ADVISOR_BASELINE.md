# Bước 7 — gợi ý rà soát cú sút bằng xG + SHAP

Ngày 23/10/2026: đã có baseline ngoại tuyến tạo JSON và báo cáo tiếng Việt
cho HLV. Mỗi gợi ý gắn với tập cú sút cụ thể, chỉ số tổng hợp và đóng góp
SHAP. Chưa thêm API/giao diện hoặc đổi schema dùng chung. Không dùng LLM,
không thêm thư viện, không huấn luyện lại mô hình xG của bước 6.

## Cách hoạt động

`backend/advisor/shot_advisor.py` đọc sự kiện StatsBomb đã khóa nguồn,
lọc cú sút không penalty hiệp 1–4, trích đúng tám feature của bước 6,
chạy xG và Tree SHAP. Không cần outcome hoặc `statsbomb_xg` trong input;
hai trường này, vị trí kết thúc và diễn biến sau cú sút không tham gia
sinh gợi ý. Team ID dùng để nhóm; player ID, tên ngắn, phút/giây, event
index và event ID dùng tra cứu, không làm feature.

Đây là mô hình xG đã học cộng **luật gợi ý được viết trước**, không phải
mô hình học chính sách chiến thuật từ đánh giá của HLV. Luật chỉ hướng
HLV tới các pha cần xem lại. Không suy ra việc chuyền sẽ tốt hơn sút,
thay người, đổi sơ đồ hoặc hiệu quả của một bài tập từ dữ liệu hiện có.
Chưa đánh giá độ hữu ích của gợi ý với HLV hoặc trên nhãn chiến thuật.

## SHAP giải thích đúng mô hình

Dùng [SHAP TreeExplainer](https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html)
0.51.0, `tree_path_dependent`, đầu ra raw. Với XGBoost binary, đóng góp
có đơn vị **log-odds**, không phải xác suất hoặc điểm phần trăm:

```text
margin = base_log_odds + tổng SHAP của tám feature
xG = sigmoid(margin)
```

Mô hình bước 6 lưu 106 cây sau early stopping, nhưng XGBClassifier dùng
best_iteration 65, tức 66 cây. Advisor cắt một **bản Booster trong RAM**
đến 66 cây để TreeExplainer giải thích cùng bộ cây với predict_proba;
không sửa file trọng số gốc. Kiểm hash mô hình/metadata, tên feature và
best_iteration. Bật check_additivity và kiểm tra bổ sung với margin/xG
của XGBClassifier; nếu sai số vượt 1e-5 log-odds hoặc 1e-6 xác suất thì
dừng, không xuất gợi ý.

Không lấy trận phân tích làm background. Tree-path-dependent sử dụng
thống kê đường đi đã có trong cây. Những feature hình học tương quan
nhau; đóng góp riêng tùy phương pháp giải thích. Đóng góp âm là giảm dự
đoán so với nền của mô hình, không chứng minh feature gây giảm cơ hội
trong thực tế. SHAP giải thích mô hình, không cải thiện AUC/Brier của nó.

## Luật và điều kiện từ chối

Protocol ở `docs/fixtures/advisor_protocol_v1.json`. Các ngưỡng chỉ là
heuristic phục vụ bản nháp, không phải ngưỡng học từ test hoặc đã được
HLV nghiệm thu. Không tinh chỉnh ngưỡng theo báo cáo mẫu.

Đội cần ít nhất năm cú sút hợp lệ; nhóm căn cứ cần ít nhất ba cú sút:

| Luật | Điều kiện số lượng/xG | Điều kiện SHAP của nhóm |
| --- | --- | --- |
| Rà soát lựa chọn vị trí dứt điểm | xG < 0,08, chiếm ≥50% cú sút đội | Tổng đóng góp trung bình khoảng cách/góc/lệch ngang <0 |
| Rà soát hỗ trợ khi dứt điểm dưới áp lực | Under pressure, chiếm ≥40% | Đóng góp under_pressure trung bình <0 |
| Rà soát cách tạo cơ hội xG cao | xG ≥0,20, chiếm ≥25% | Tổng đóng góp trung bình khoảng cách/góc/lệch ngang >0 |

Chỉ liệt kê feature có dấu hỗ trợ đúng hướng; một component âm không đủ
để gọi toàn bộ nhóm hình học là bất lợi nếu tổng nhóm dương. Không ép
sinh gợi ý khi số lượng đạt nhưng SHAP không hỗ trợ diễn giải.

Đội ít cú sút có trạng thái `insufficient_data`; đủ số lượng nhưng không
luật nào đạt có trạng thái `no_rule_triggered`. Trường hợp này không có
nghĩa đội chơi tốt. Vẫn giữ đội có Starting XI nhưng không có cú sút hợp
lệ. Phân biệt hai đội cùng tên bằng ID, từ chối event ID thiếu/trùng và
team ID có tên mâu thuẫn. Loại dữ liệu feature lỗi và ghi số bị loại.

## Truy vết đầu ra

JSON nội bộ `shot_advisor_v1`, không phải thay đổi DATA_CONTRACT:

- `model_audit`: hash mô hình/metadata, số cây, phương pháp/phiên bản SHAP,
  đơn vị và sai số khôi phục lớn nhất.
- `shots`: từng event ID/index, đội/cầu thủ, tên ngắn, phút/giây, feature,
  xG, margin, base và đủ tám đóng góp SHAP. Không chép outcome vào đây.
- `teams`: số cú sút hợp lệ, tổng/trung bình xG, trạng thái và gợi ý.
- Mỗi gợi ý: rule ID, tiêu đề/hành động tiếng Việt, `event_ids`, tử số/mẫu
  số/tỷ lệ, xG trung bình, feature trung bình, SHAP trung bình và các
  feature hỗ trợ. Tất cả event ID phải thuộc cùng đội trong `shots`.
- `provenance`: revision StatsBomb, hash sự kiện/protocol/inventory và
  phân tập của trận trong bước xG. Ghi rõ đây là phân tích sau trận.

Bản Markdown hiển thị số liệu và ba pha minh họa mỗi gợi ý theo phút,
tên ngắn và index sự kiện. JSON giữ toàn bộ event ID để truy về nguồn.
Nguồn và điều kiện sử dụng StatsBomb theo `XG_BASELINE.md`; không ghép
những người của StatsBomb với track ID trong video/Metrica.

## Kết quả minh họa trận 8650

Brazil–Belgium, 33 cú sút hợp lệ: Brazil 25, Belgium 8. Trận thuộc tập
**validation** của mô hình xG, chỉ minh họa chức năng, không phải đánh
giá độc lập mô hình hoặc chất lượng khuyến nghị.

| Đội | Tổng xG dự án | Nhóm xG <0,08 | xG trung bình nhóm | Gợi ý được sinh |
| --- | ---: | --- | ---: | --- |
| Brazil | 2,990 | 13/25 (52%) | 0,049 | Rà soát lựa chọn vị trí dứt điểm |
| Belgium | 0,558 | 6/8 (75%) | 0,045 | Rà soát lựa chọn vị trí dứt điểm |

Hai luật còn lại chưa đủ điều kiện, không tự điền thêm nội dung. Tổng xG
là tổng xác suất cú sút từ baseline dự án, không phải xG StatsBomb hoặc
dự đoán tỷ số. Số Goal thực tế không dùng để chọn gợi ý hay kết luận khả
năng dứt điểm của cầu thủ.

Đã đối chiếu 2/2 gợi ý: mọi tham chiếu event tồn tại, thuộc đúng đội,
không trùng; tính lại số lượng/xG/SHAP trung bình khớp. Sai số khôi phục
lớn nhất 9,54e-7 log-odds, 1,79e-7 xác suất, dưới ngưỡng đã đặt. Đây là
kiểm chứng số học/truy vết, không phải accuracy chiến thuật.

## Chạy và kiểm tra

Cần chạy bước 6 để có nguồn và trọng số với đúng hash:

```powershell
.\.venv\Scripts\python.exe -m backend.advisor.shot_advisor --match-id 8650 --output data/processed/advisor_8650_repro
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_advisor_full_v1
```

Mặc định nguồn `data/raw/statsbomb_xg_v1`, mô hình
`data/processed/xg_model_v1`; có thể truyền `--source-directory` và
`--model-directory`. Match phải có trong inventory bước 6, các file
sự kiện/match phải đúng hash và revision nguồn của mô hình. Output phải
mới. Không tự tải dữ liệu, không ghi đè báo cáo cũ.

Artifact chốt: `data/processed/advisor_8650_v1_final/advisor.json` và
`report.md`. Bản chạy nháp trước đó ở `advisor_8650_v1` không phải kết
quả chốt. Snapshot tổng hợp/hash ở `docs/fixtures/advisor_result_v1.json`,
không đưa bản ghi cú sút hoặc toàn bộ nguồn vào Git.

Bảy test mới: phân nhóm ID/loại penalty và luân lưu, từ chối gợi ý khi
thiếu mẫu/SHAP không hỗ trợ, ranh giới xG và hai luật còn lại, số liệu
căn cứ, Tree SHAP thật với best trees, bất biến khi thay outcome/xG
nguồn, báo cáo rỗng, hash trọng số và dừng khi SHAP không khôi phục được
dự đoán. Toàn bộ **280 passed, 1 network deselected**; cảnh báo Starlette
cũ và ba cảnh báo deprecation bên trong bảng màu SHAP.

Nghiệm thu được chức năng baseline và tính truy vết. Cần HLV đánh giá
gợi ý trên dữ liệu độc lập trước khi khẳng định hiệu quả hỗ trợ chuyên
môn. Phần tiếp theo theo ROADMAP là giao diện bước 8a/8b/8c.

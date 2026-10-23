# Bước 5: rà soát bằng nhãn nháp của agent

Ngày 23/10/2026. Đã rà 24 cửa sổ Metrica đã khóa; không chỉnh thuật toán
hoặc ngưỡng theo nhận xét này. Giữ gap mặc định, template thử nghiệm.

## Nguồn nhãn

Reviewer: Codex. Đây là giả thuyết nhóm vị trí thành tuyến, không phải
đội hình được HLV/nguồn dữ liệu xác nhận hoặc nhãn độc lập của con người.
Agent xem bốn bảng trung vị (24 ô) và ba thời điểm trong mỗi cửa sổ gán
nhãn: tổng 15 ảnh đủ 11 cầu thủ. Ảnh chỉ có tọa độ, ID và thủ môn đã cấu
hình, không hiện dự đoán hay nhóm tuyến tự động. Tuy vậy agent **đã biết
kết quả tổng hợp của hai phương pháp**, nên không phải đánh giá mù.

Fixture `fixtures/metrica_formation_agent_review.json` giữ các cờ
`human_reviewed: false`, `independent_ground_truth: false`, `blinded: false`,
`prior_model_summary_exposure: true`. Mọi quyết định có lý do; nhãn sơ đồ
còn có thành viên tuyến và ba ảnh tọa độ nguồn. Nhóm được đề xuất theo
vị trí và sự duy trì tương đối của ID qua ảnh, không suy vai trò chỉ từ
số ID. Vẫn có cách nhóm khác; mức tin cậy tất cả nhãn có sơ đồ chỉ vừa phải.

Ba trạng thái:

- `draft_shape`: 5 cửa sổ có giả thuyết nhóm tuyến.
- `unscorable`: 14 cửa sổ mơ hồ/co cụm/chồng tuyến, không dùng để chấm.
- `insufficient_data`: 5 cửa sổ không có trung vị đạt guard đủ người.

Hai trạng thái sau **không phải nhãn thật unknown**. Dự đoán chưa xác
định ở đó không tự tính là đúng; dự đoán có nhãn cũng không tự tính sai.
Không gán toàn bộ Game 2 thành một sơ đồ chỉ vì vài cửa sổ gợi ý như vậy.

## Đối chiếu năm giả thuyết

| Cửa sổ Game 2 | Nhãn nháp | Gap | Template |
|---|---|---|---|
| A 60–70s | 4-4-2 | Chưa xác định | Chưa xác định |
| A 70–80s | 4-4-2 | Chưa xác định | 4-1-4-1 |
| A 80–90s | 4-4-2 | Chưa xác định | Chưa xác định |
| B 100–110s | 4-3-3 | 4-2-4 | Chưa xác định |
| B 110–120s | 4-3-3 | Chưa xác định | 4-4-2 |

Nháp A nhóm 1/2/3/4, 5/6/7/8, 9/10 thành 4/4/2. Các tuyến nghiêng và
x chồng lấn; ID 7 đôi lúc lùi gần hàng sau. Nháp B nhóm 1015–1018,
1019–1021, 1022–1024 thành 4/3/3; 1019 có lúc dâng cao và các tuyến gần
nhau. Không tuyên bố vai trò đó đã được xác nhận.

Gap có 4 lần chưa xác định và 1 lần không đồng ý nháp; template có 3 lần
chưa xác định và 2 lần không đồng ý. Mỗi phương pháp có 19 cửa sổ không
chấm. Hai nhãn gap ở A 90–100s và A 110–120s thuộc tập không chấm, không
tự tính là lỗi. Đây là đếm đối chiếu, **không phải accuracy thực tế**.

Các tuyến nghiêng/chồng x và đổi vị trí là giả thuyết nguyên nhân khác
biệt giữa bố trí hình học lý tưởng và trận thật, chưa phải nguyên nhân
được chứng minh bằng nhãn chuẩn. Chưa có bằng chứng template tốt hơn gap.

## Truy nguồn và chạy lại

Fixture giữ hash canonical JSON của packet nguồn, không phụ thuộc LF/CRLF.
Packet giữ hash CSV và báo cáo trung vị. Đã đối chiếu 165 điểm (15 × 11)
với hai CSV Game 2 có hash khóa: frame, timestamp, tọa độ sau chuẩn hóa
trùng chính xác. Điều này xác nhận thao tác trích dữ liệu, không chứng
minh nhãn sơ đồ là đúng.

CLI kiểm tra đủ 24 quyết định, không trùng/ngoại lai, đủ 10 ID ngoài sân
trong các tuyến không lặp, đủ ba ảnh đúng thời gian/cadence/roster và tọa
độ hợp lệ. Nhãn mơ hồ không được mang một sơ đồ giả để chấm.

Từ gốc repo, dùng thư mục đầu ra mới:

```powershell
.\.venv\Scripts\python.exe -m backend.tactics.review_formation --output-dir data/processed/formation_v1/agent_review_replay_v1 --render
.\.venv\Scripts\python.exe -m pytest -q tests/test_formation_agent_review.py --basetemp .tmp/pytest_formation_agent_check
```

Chạy lại không cần CSV lớn: tọa độ ảnh thời điểm đã có trong fixture.
Đầu ra có `evaluation.json`, bảng `review.md`; `--render` thêm bốn bảng
trung vị và năm bảng ảnh thời điểm. Đây là hình QA ngoại tuyến, không phải
ảnh API sản phẩm. Không đổi schema/API/dependency/thuật toán nhận diện.

11 test mới kiểm tra đối chiếu, không coi cửa sổ chưa chấm là đúng/sai,
truy nguồn, lỗi tuyến/ảnh, thiếu/trùng cửa sổ và chống ghi đè.
Toàn bộ dự án: **218 passed, 1 network deselected**, cảnh báo Starlette cũ.

## Quyết định

Đã hoàn tất đợt rà soát nháp này. Giữ nhận diện sơ đồ ở mức thử nghiệm,
không tinh chỉnh tiếp trên năm nhãn nháp rồi báo đó là tập kiểm định.
Chức năng ngoại tuyến bước 5 đã có; chất lượng chiến thuật chưa nghiệm
thu. Cần tiêu chí nhãn nhất quán và tập đánh giá mới có nhãn độc lập,
tách khỏi cửa sổ đã dùng phát triển. Người dùng không phải nhập lại nhãn
trong phiên này.

# Bước 6 — baseline xG bằng XGBoost

Ngày 23/10/2026. Đã triển khai chuẩn bị dữ liệu, huấn luyện, lưu/nạp mô
hình và đánh giá ngoại tuyến trên giải đấu giữ riêng. Backend CLI xuất
JSON/CSV; chưa thêm API hoặc giao diện, không đổi hợp đồng dữ liệu.

## Mục tiêu và phạm vi

xG là xác suất thành bàn của **một cú sút** từ ngữ cảnh khi sút. Nhãn học
là Shot Goal = 1, các outcome cú sút hợp lệ khác = 0; không học bằng cách
bắt chước xG StatsBomb. Mô hình này chỉ nhận cú sút không penalty trong
hiệp 1–4, có cả hiệp phụ; loại loạt luân lưu. Own Goal là loại sự kiện
riêng, không cộng vào Shot Goal. Không dự đoán kết quả trận hoặc nhận diện
cú sút từ video.

## Nguồn và chia tập

Dữ liệu: [StatsBomb Open Data, hiện thuộc hudl/open-data](https://github.com/hudl/open-data),
revision `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`.
Nguồn khóa theo revision, tải JSON gốc và kiểm kích thước/Git blob SHA1;
inventory 185 file ở `docs/fixtures/xg_source_inventory_v1.json`.
Không thay cache sự kiện StatsBomb đang có. Bảng cú sút mới dùng CSV.

Ghi công StatsBomb. Điều kiện sử dụng ở
[LICENSE.pdf của revision](https://github.com/hudl/open-data/blob/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/LICENSE.pdf)
và [README của nguồn](https://github.com/hudl/open-data/blob/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/README.md).
Nguồn yêu cầu ghi công và dùng logo StatsBomb khi công bố nghiên cứu/phân
tích; tham khảo Media Pack được dẫn trong README khi làm báo cáo/slide.
Không đưa dữ liệu cú sút/trọng số vào Git; chỉ lưu protocol, hash và tổng
hợp kết quả. Đây không phải bộ dữ liệu mang giấy phép CC BY của bước 5b.

| Tập | Giải đấu | Trận | Cú sút | Shot Goal |
| --- | --- | ---: | ---: | ---: |
| Train | World Cup 2018 + Euro 2020 | 92 | 2.251 | 214 |
| Validation | World Cup 2018 + Euro 2020 | 23 | 621 | 43 |
| Test | World Cup 2022 | 64 | 1.430 | 152 |

Chia 115 trận phát triển thành train/validation theo hash seed 20261023
và match ID, không chia ngẫu nhiên từng cú sút; không chọn trận dựa vào
nhãn bàn thắng. Toàn bộ 64 trận World Cup 2022 làm test, diễn ra sau các
trận phát triển. Không giao match ID hay event ID giữa các tập. Kiểm tra
ngày trận, hash CSV và phân tập trước huấn luyện. Có 4.302 cú sút được
giữ; loại 69 penalty trong trận và 118 cú sút ở period ngoài 1–4. Không
có cú sút bị loại do thiếu feature hoặc thiếu xG tham chiếu ở lượt này.

Tỷ lệ Goal train/validation/test lần lượt khoảng 9,51% / 6,92% / 10,63%.
Đây là mẫu giải quốc tế nam tương đối nhỏ, có dịch chuyển phân phối;
chưa đánh giá giải quốc nội, bóng đá nữ hoặc video người dùng.

## Feature và chống rò rỉ nhãn

Tám feature theo thứ tự cố định:

1. Khoảng cách từ điểm sút đến giữa cầu môn, mét.
2. Góc mở giữa hai cột dọc, radian.
3. Khoảng cách ngang tới trục giữa sân, mét, lấy trị tuyệt đối.
4. Đánh đầu hay không.
5. Bộ phận khác đầu/chân trái/chân phải hay không.
6. Sút phạt trực tiếp hay không.
7. First time hay không.
8. Under pressure hay không.

Tọa độ dùng helper chung StatsBomb 120×80 → 105×68, cầu môn ở x=105,
y=34, rộng 7,32 m. Đây là quy ước sân cố định; không khẳng định kích
thước thật của mọi sân. Tính góc bằng atan2 để xử lý cả gần/vị trí ngay
vạch cầu môn. Giữ đối xứng hai cánh. Boolean bị lược khỏi JSON nguồn
được hiểu là false theo cách biểu diễn flag của nguồn.

Không đưa outcome, vị trí kết thúc/quỹ đạo bóng, thời gian bay, xG nhà
cung cấp, ID/tên cầu thủ/đội/trận hoặc thông tin sau cú sút vào feature.
Chưa dùng freeze frame thủ môn/hậu vệ hoặc kỹ thuật sút; đây là baseline
ngữ cảnh đơn giản. `statsbomb_xg` chỉ là cột tham chiếu. Mọi mô hình trong
bảng dưới được chấm trên **cùng 1.430 cú sút và nhãn Goal thật**.

## Huấn luyện và lưu mô hình

Protocol khóa trước lượt chạy ở `docs/fixtures/xg_protocol_v1.json`:
XGBClassifier binary:logistic, CPU hist, tối đa 600 cây, max_depth 3,
learning_rate 0,03, min_child_weight 10, reg_lambda 10, subsample và
colsample_bytree đều 1, n_jobs 4, random_state 20261023. Không tăng trọng
số lớp dương để tránh biến xác suất học thành bài toán cân bằng lớp.

Early stopping 40 vòng theo log loss **validation**, chọn best_iteration
65 (đếm từ 0). Test không nằm trong eval_set, không dùng để chọn cấu hình,
ngưỡng hoặc hiệu chỉnh xác suất. Một cấu hình, không tìm hyperparameter.
Tài liệu [giao diện sklearn chính thức XGBoost](https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html)
mô tả eval_set và cách predict dùng best iteration.

Môi trường lượt chạy: Python 3.11.3, XGBoost 3.2.0, scikit-learn 1.9.1;
phiên bản NumPy/Pandas cũng lưu trong metadata. Không thêm thư viện.
Lưu native `model.json` và metadata/hash, không pickle. Nạp lại bằng
XGBClassifier cho dự đoán khớp trong 1e-7 trên cả ba tập. Helper inference
cũng đã chạy năm cú sút thật với outcome/xG StatsBomb bị bỏ khỏi input.
Khi dùng lại cần giữ cơ chế best_iteration của XGBClassifier; không tự
gọi native Booster với mọi cây sau early stopping rồi coi là cùng mô hình.

## Kết quả test World Cup 2022

| Mô hình | ROC AUC ↑ | Brier ↓ | Log loss ↓ |
| --- | ---: | ---: | ---: |
| XGBoost của dự án | 0,7665 | 0,08467 | 0,29367 |
| xG StatsBomb tham chiếu | 0,8148 | 0,07619 | 0,26650 |
| Xác suất cố định bằng tỷ lệ Goal train | 0,5000 | 0,09512 | 0,33940 |

AUC đo khả năng xếp hạng cơ hội thành bàn; Brier là trung bình bình phương
sai số xác suất, càng thấp càng tốt. Không gọi AUC là tỷ lệ dự đoán đúng
của từng cú sút. Không cần ngưỡng 0,5 cho các chỉ số này. XGBoost tốt hơn
baseline xác suất cố định nhưng kém StatsBomb trên tập này.

Bootstrap ghép cặp theo **trận**, 500 lượt, seed đã khóa; giữ các cú sút
cùng trận chung một cụm. Chênh lệch XGBoost trừ StatsBomb:

- AUC −0,04823; khoảng percentile 95% [−0,07735; −0,01658].
- Brier +0,00847; khoảng percentile 95% [+0,00501; +0,01215].

Các khoảng phản ánh lấy mẫu lại các trận test, không bao gồm bất định do
huấn luyện lại mô hình. StatsBomb có thể dùng nhiều ngữ cảnh hơn; không
biết tập huấn luyện hoặc mức giao dữ liệu của mô hình nhà cung cấp. Đây
là đối chiếu tham chiếu, không phải cuộc so sánh hai mô hình được huấn
luyện trên cùng điều kiện. Không chỉnh lại cấu hình theo kết quả test.

Đã lưu thêm mười bin calibration có count/xG trung bình/tỷ lệ Goal thật
cho từng mô hình và từng tập, cả bin rỗng. xG trung bình trên test là
0,09710 (dự án), 0,09642 (StatsBomb), tỷ lệ Goal thật 0,10629. Đây là
chẩn đoán hiệu chỉnh xác suất, chưa áp dụng calibration học từ test.

## Chạy lại và dùng kết quả

Từ gốc repo, dùng output mới:

```powershell
.\.venv\Scripts\python.exe -m backend.tactics.prepare_xg --download --output data/processed/xg_dataset_repro
.\.venv\Scripts\python.exe -m backend.tactics.train_xg --dataset data/processed/xg_dataset_repro --output data/processed/xg_model_repro
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_xg_full_v1
```

Input nguồn đã tải ở `data/raw/statsbomb_xg_v1/`; khi đã đủ file, có thể
bỏ `--download`. Lệnh từ chối nguồn sai hash hoặc output đã tồn tại.
Lượt thật ở `data/processed/xg_dataset_v1/` và `data/processed/xg_model_v1/`:

- `shots.csv`, `manifest.json`: cú sút, feature và danh sách trận/phân tập.
- `model.json`, `model_metadata.json`: trọng số và thông tin nạp mô hình.
- `evaluation.json`: AUC/Brier/log loss, calibration bins, bootstrap.
- `predictions.csv`: từng event ID, match ID, tập, nhãn và hai xác suất xG.
- `inference_smoke.json`: năm input không có outcome/xG nguồn và dự đoán.
- Snapshot tổng hợp Git: `docs/fixtures/xg_result_v1.json`.

Helper `backend.tactics.train_xg.predict_events(model_directory, events)`
nhận JSON sự kiện StatsBomb và trả danh sách `{event_id, xg}`; không cần
outcome hoặc xG nguồn. Từ chối penalty, period ngoài 1–4 và sự kiện không
phải Shot; không tự áp mô hình ngoài phạm vi. Có thể cộng xG các cú sút
hợp lệ theo cùng cầu thủ/đội/trận khi làm phần báo cáo sau này.

Đã có chín test mới: hình học/đối xứng/biên, chống rò outcome/xG/ID,
lọc penalty/luân lưu, chia theo trận và thời gian, metric/calibration,
bootstrap tái lập, huấn luyện–lưu–nạp–inference và từ chối sửa dataset/
chia sai tập/trọng số. Toàn bộ **273 passed, 1 network deselected**, có
cảnh báo Starlette cũ. Chất lượng của các bước CV/đội hình trước đó không
được nâng đánh giá nhờ kết quả xG này.

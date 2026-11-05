# Nguồn bổ sung vai trò v12 — kiểm nhãn trước huấn luyện

Ngày 05/11/2026. Đã xuất **7 ROI từ 6 ảnh gốc, 5 nhóm bối cảnh**:
4 vùng sân có nhãn và 3 vùng nền âm không có đối tượng thuộc ba lớp.
Tổng **52 player, 4 goalkeeper, 6 referee**. Đây là bộ nguồn riêng, chưa
ghép vào dataset v11 và chưa huấn luyện. Model ứng dụng giữ nguyên.

Nguồn ảnh và nhãn: skaczylo, Football Image Dataset, revision
`264212872f1bfa6a9a3413f298793474da741aec`;
[giấy phép CC BY 4.0 do nguồn công bố](https://github.com/skaczylo/Football-Image-Dataset/blob/264212872f1bfa6a9a3413f298793474da741aec/LICENSE).
Các ảnh được chọn đã xem ở kích thước gốc, là hình ảnh truyền hình trận đấu.
Không mặc định toàn bộ kho đều là ảnh thật. Giữ Git blob SHA, SHA256 ảnh/
nhãn/license, đường dẫn upstream và attribution; không suy diễn danh tính
trận chính thức từ ảnh khi không có bằng chứng.

| Ảnh survey | Bối cảnh nhìn thấy | Vùng xuất, pixel gốc | Điểm cần học |
|---|---|---|---|
| 29 | Libertadores, trắng/xanh dương gặp xanh neon; chưa rõ trận | 0,0–1920,1080 | Thủ môn xanh đứng, sân rộng, khung thành |
| 79 | WOB–RBL 1–3, 74:08 | 0,0–1920,1080 | Thủ môn tối đứng, trợ lý tối cầm cờ ở biên xa |
| 186 | WOB–RBL 0–1, 25:09 | 0,0–1920,880 | Thủ môn cyan di chuyển thẳng người, trợ lý tối biên xa |
| 25 | ESP–BAR 0–0, 50:25, RCDE | 0,0–1920,700 | Thủ môn hồng đứng rất xa; giữ người nhỏ |
| 29 | Cùng ảnh 29 | 0,230–220,420 | Nền âm: cột/lưới gôn, bóng phụ, bảng quảng cáo |
| 270 | FCU–VFB 3–2, 41:30 | 0,0–1920,200 | Nền âm: đèn sáng, mái sân, khán đài |
| 151 | Okayama–Machida 0–0, 25:43 | 1800,540–1920,830 | Nền âm: cờ góc, vạch biên, đường chạy |

Hai ảnh WOB–RBL là **một nhóm**, không phải hai trận độc lập. ROI âm/dương
từ ảnh29 cũng cùng nhóm và cùng parent. Các nguồn cũ BVB-home, M05–WOB
được loại bảo thủ khi chưa đủ bằng chứng tách trận. Kiểm bối cảnh dựa
scoreboard, sân và trang phục; kiểm ảnh gần trùng không chứng minh hai
ảnh thuộc hai trận khác nhau. Các parent và ROI đều chỉ dành cho train.

Chiều cao khung người khi letterbox về cạnh dài640:

| Đối tượng | Cao, px | Diễn giải |
|---|---:|---|
| GK29 xanh đứng | 27,77 | Không tính vào nhóm nhỏ dưới24px |
| GK79 tối đứng | 23,08 | Nhỏ dưới24px |
| GK186 cyan di chuyển | 30,97 | Thẳng người, không phải mẫu đứng yên hay dưới24px |
| GK25 hồng đứng | 14,22 | Nhỏ dưới24px |
| Trợ lý79 tối biên xa | 18,36 | Nhỏ dưới24px |
| Trợ lý186 tối biên xa | 28,22 | Biên xa, không thuộc nhóm dưới24px |

## Đối chiếu nhãn

Đã xem toàn bộ 7 ảnh xuất có khung, ảnh gốc và phóng lớn vùng đáng nghi.
Source lớp1 gộp thủ môn với cầu thủ; tách tay bốn thủ môn, giữ hệ lớp xuất
`0 player / 1 goalkeeper / 2 referee`. Không dùng dự đoán role detector để
chọn ảnh hoặc tạo nhãn. Mỗi dòng nhãn nguồn có quyết định và lý do; mọi
đối tượng đang thi đấu/góp mặt với vai trò trọng tài trong ROI phải được
gán nhãn. Người xem, nhân viên sân, dự bị khởi động và staff ngoài cuộc
chơi là nền theo phạm vi bộ vai trò này. Bóng không thuộc ba lớp.

Ba sửa chữa chỉ áp dụng cho bản xuất, không sửa nhãn gốc hay v11:

- Ảnh29, dòng14 (index từ0): khung referee trên cấu trúc gôn/quảng cáo,
  không có người; bỏ nhãn giả này.
- Ảnh25, dòng19: nhãn referee trùng trên cầu thủ áo tối; giữ dòng20 là
  player. Trọng tài thật áo đỏ ở dòng9/21 được giữ.
- Ảnh151, dòng16: nguồn gán player lên cờ góc/cột cờ; vùng âm được xem
  riêng và xác nhận không có người.

Ảnh186 cắt trước người bị cụt ở đáy ảnh; ảnh25 cắt trước nhóm cầu thủ gần
biên dưới, giữ chiều rộng1920 để không phóng lớn thủ môn. Không bỏ đối
tượng đang thi đấu bị ROI cắt dở: validator từ chối trường hợp đó. Không
coi cụm ba người che nhau ở ảnh79 là ba khung trùng một người.

## Kiểm tra và tái tạo

Fixture nguồn/nhãn: `docs/fixtures/role_sources_review_v12.json`.
Fixture nhóm/ROI khóa trước inference: `role_source_groups_v12.json`.
Kết quả và thông tin rà ảnh: `role_source_release_summary_v12.json`.

Đầu vào cục bộ: ảnh trong `data/raw/fullscene_roles_v5/`, nhãn upstream
đã kiểm Git blob ở `data/raw/role_sources_v12/`. Không commit các ảnh/dữ
liệu thô. Từ gốc repo chạy:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.prepare_role_source_release_v12
.\.venv\Scripts\python.exe -m pytest -q tests/test_prepare_role_source_release_v12.py --basetemp .tmp/pytest_v12_sources
```

Lệnh xuất từ chối ghi đè; tái chạy dùng `--output` trỏ tới thư mục mới
trong repo. Bản xuất hiện tại:
`data/processed/role_source_release_v12/` gồm PNG, YOLO TXT (âm = file
rỗng), manifest, ảnh review có khung và attribution. Không tạo lệnh train.

Kiểm482 SHA ảnh tham chiếu duy nhất qua mọi split v11 và release v8/v9
(bao gồm heldout128057), so SHA file, SHA pixel và bộ lọc gần trùng
dHash≤4 kết hợp MAE grayscale≤3. Không có hit. Đồng thời kiểm giữa các
parent mới, cho phép ROI chung parent đã khai báo. Kiểm toàn bộ hash
ảnh/nhãn v11 lại sau xuất;128val/35test không thay đổi, không inference
trên test hay match128057. Heuristic gần trùng có giới hạn, không thay
kiểm scene thủ công.

Sáu test đích đạt; toàn bộ Python: **602 passed, 1 network deselected**,
4 cảnh báo Starlette/SHAP đã có. Các test kiểm vùng âm, target bị cắt,
actor chưa rà/không chắc, coverage ledger/geometry/mapping và đối chiếu
toàn bộ packet không cần dữ liệu ảnh cục bộ.

Manifest SHA256:
`56a7563d1cb66852e2d88545ff629d74b3acf7809e1332e142d2683901967927`.
Packet SHA256:
`9820bdaec0bc640a9c3b69b29fc9d2b7f97b5381f47fe7e75be9c38793fd93ad`.

Nhãn do agent rà, **chưa được người độc lập nghiệm thu**; chưa có bằng
chứng mô hình nhận tốt hơn. Hai ảnh trọng tài tối vẫn chỉ từ một nhóm
trận; mẫu thủ môn xanh/cyan đứng nhỏ dưới24px vẫn thiếu. Bước tiếp theo:
bổ sung thêm bối cảnh độc lập cho hai nhóm này, rồi khóa việc ghép/lấy
mẫu (tính cả quan hệ parent của vùng âm) trước khi train và chấm lại đủ
ba lớp tại640/1280. Không tăng epoch hoặc đổi model ứng dụng ở bước này.

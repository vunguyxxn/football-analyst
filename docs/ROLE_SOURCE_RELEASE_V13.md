# Bổ sung bối cảnh độc lập v13

Ngày 05/11/2026. Bổ sung **hai ảnh gốc thuộc hai nhóm bối cảnh mới** so
với bộ nguồn v12. Một nhóm đáp ứng thủ môn xanh đứng nhỏ, một nhóm đáp
ứng trợ lý áo tối biên xa nhỏ. Không thêm ảnh cùng WOB–RBL rồi tính thành
trận mới. Chưa ghép train, chưa huấn luyện và chưa đổi model ứng dụng.

| Nguồn | Bằng chứng bối cảnh | ROI gốc | Mẫu mục tiêu tại640 |
|---|---|---|---|
| Survey88 | Libertadores; đội trắng gặp sọc đen-trắng, sân khán đài đỏ ban đêm; chưa xác định danh tính trận chính thức | 0,0–1920,920 | Thủ môn xanh đứng, dòng18: **13,50px** |
| Survey143 | Scoreboard Kobe–Hiroshima0–0,46:49+2; trợ lý cầm cờ ở biên xa, áo đen như trọng tài chính | 0,0–1920,1080 | Trợ lý áo tối, dòng16: **22,80px** |

Giữ chiều rộng gốc1920 để không phóng lớn người nhỏ. Ảnh88 loại toàn bộ
người ở dòng12, bắt đầu dưới y920; đường cắt không đi qua target khác.
Người áo xanh gần biên dưới ảnh88 là người ngoài cuộc chơi, nằm ngoài
ROI; thủ môn mục tiêu là người trong vùng cầu môn bên phải. Ảnh143 giữ
toàn ảnh. Hai thủ môn (88:18 và143:14) được tách từ lớp player gộp của
nguồn; thủ môn áo vàng143 là nhãn hỗ trợ, không tính vào mẫu xanh/sáng
nhỏ mục tiêu. Không sửa geometry nguồn, không xóa nhãn trùng/giả trong
hai ảnh này vì rà ảnh không phát hiện trường hợp đó.

Tổng bản xuất v13: **33 player, 2 goalkeeper, 4 referee** trên2 vùng sân.
Đã xem cả hai ảnh xuất có khung, ảnh gốc và hai crop mục tiêu. Mọi dòng
nhãn nguồn có quyết định; không chỉ gán nhãn cho hai đối tượng mục tiêu.
Không dùng role detector để chọn ảnh hoặc gán nhãn. Ảnh88 mờ và đối
tượng nhỏ; không suy ra danh tính cầu thủ từ ảnh này.

Nguồn cùng kho skaczylo/Football-Image-Dataset, revision
`264212872f1bfa6a9a3413f298793474da741aec`,
[ảnh và nhãn theo CC BY4.0 do nguồn công bố](https://github.com/skaczylo/Football-Image-Dataset/blob/264212872f1bfa6a9a3413f298793474da741aec/LICENSE).
Giữ attribution, SHA256 ảnh/nhãn/license và Git blob trong packet. Chỉ
chọn ảnh truyền hình thật đã xem; không mặc định cả kho đều là ảnh thật.
Ảnh gốc cache ở `data/raw/fullscene_roles_v5/`, nhãn upstream nguyên vẹn
ở `data/raw/role_sources_v13/`; dữ liệu ảnh không đưa vào Git.

Các ứng viên loại có lý do trong packet. Đáng chú ý: ảnh181 nhìn thumbnail
dễ đọc nhầm thành WOB–Kiel nhưng native vẫn WOB–RBL; ảnh28 cùng nhóm.
Ảnh194 cùng bối cảnh Libertadores trắng/xanh–xanh neon của v12 và thủ môn
đang đổ người; không dùng để chứng minh đa dạng hoặc tư thế đứng. Ảnh111
thủ môn xanh cao25,49px tại640, không đạt điều kiện nghiêm ngặt <24px.

Kiểm hash mọi ảnh/nhãn của v11 và releasev8/v9/v12: **489 SHA ảnh duy
nhất**. Không trùng SHA file/pixel hoặc hit dHash≤4 kết hợp MAE grayscale≤3;
kiểm cả giữa hai parent mới. Mọi split cũ và heldout128057 chỉ dùng đối
chiếu dữ liệu, không chạy inference. V11 vẫn128val/35test; v12 giữ nguyên
manifest. So sánh sân, áo và scoreboard thủ công để tách nhóm, không coi
heuristic ảnh là bằng chứng danh tính trận hoặc tính độc lập thống kê.

Fixture: `docs/fixtures/role_sources_review_v13.json`,
`role_source_groups_v13.json`, `role_source_release_summary_v13.json`.
Artifact: `data/processed/role_source_release_v13/` chứa PNG, YOLO TXT,
manifest, attribution và ảnh kiểm nhãn. Runner v13 bổ sung điều kiện:
hai loại mục tiêu, bối cảnh mới so v12, chiều rộng gốc, tư thế thẳng người,
chiều cao thực tại640 dưới24px và bắt buộc screen releasev12. Dùng lại
validator ledger/coverage và exporter v12; v12 không đổi packet/nhãn.

```powershell
.\.venv\Scripts\python.exe -m backend.cv.prepare_role_source_release_v13
.\.venv\Scripts\python.exe -m pytest -q tests/test_prepare_role_source_release_v12.py tests/test_prepare_role_source_release_v13.py --basetemp .tmp/pytest_v13_sources
```

Không ghi đè bản xuất; dùng `--output` là thư mục mới trong repo để
tái tạo. Replay thực tế cho manifest giống hệt; manifest v12 giữ nguyên.
12 test đích (v12/v13) đạt; toàn bộ Python **608 passed, 1 network
deselected**,4 cảnh báo Starlette/SHAP cũ. Sáu test mới kiểm nhóm/parent
khác v12, kích thước sau letterbox, tư thế, màu, crop rộng, bắt buộc
screen v12 và replay ledger đầy đủ không phụ thuộc ảnh cục bộ.

Manifest SHA256:
`8ee91dfacb8c2251b20f9830f811f2648e6351e2427ccc3023606164bf88fb3c`.
Packet SHA256:
`c49662ad6023f9f2d50a1c5db8162cb2e8ebd130cc29b312deebbab108440c76`.

Cộng nguồn v12 và v13 (chưa ghép train):6 vùng sân,3 vùng âm,8 parent,
7 nhóm bối cảnh,85 player/6 goalkeeper/10 referee. Trọng tài tối biên xa
trong nguồn mới đã có hai nhóm WOB–RBL và Kobe–Hiroshima. Đây vẫn là bộ
bổ sung nhỏ, nhãn agent rà chưa nghiệm thu độc lập, chưa có số đo cải thiện.

Bước tiếp theo: ghép v11 với hai release đã kiểm, khóa repeats/lấy mẫu
(ROI chung parent29 của v12 không coi độc lập), giữ nguyên val/test và
quy trình chấm. Sau đó mới huấn luyện small theo cấu hình đối chiếu đã
khóa và so đủ ba lớp ở640/1280, không tự thay model ứng dụng.

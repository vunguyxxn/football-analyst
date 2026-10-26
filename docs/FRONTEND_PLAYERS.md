# Bước 8b — hồ sơ cầu thủ trên giao diện

Ngày 26/10/2026: trang `/players` đã thay trang chờ bằng danh sách cầu
thủ và hồ sơ chi tiết. Dùng các báo cáo JSON nội bộ đã có ở bước 5,
không đổi DATA_CONTRACT, thêm API, thư viện hoặc thuật toán phân tích.

## Mở và xem

Từ thư mục `frontend`, chạy `npm run dev`, mở `/players`. Hai nút nguồn:

- **StatsBomb**: 27 hồ sơ trận 8650 Brazil–Belgium. Tên ngắn có sẵn,
  tên đầy đủ, player ID, đội, số áo/xuất phát nếu nguồn có; chuyền và tỷ
  lệ hoàn thành, Carry, cú sút/cú sút thành bàn, số sự kiện ghi nhận,
  ngữ cảnh vai trò và index để tra sự kiện.
- **Metrica**: 22 hồ sơ Game 1, hiệp 1, giây 60–120. Chỉ dùng ID tracking,
  không tự gán tên/số áo thật; hiển thị quãng đường quan sát, tốc độ trên
  các khoảng được nhận, thời gian đại diện, hai mức bao phủ và heatmap.

Tìm theo tên đầy đủ/tên ngắn/ID, có bỏ dấu tiếng Việt khi tìm. Lọc đội,
chọn cầu thủ, chuyển Pass/Carry/Shot và mở thêm index sự kiện. Đổi nguồn
reset bộ lọc, tên cầu thủ và lựa chọn trước đó. Không có kết quả thì bỏ
hồ sơ cũ và hiện trạng thái rỗng. Dữ liệu thiếu/null hiển thị **—**; số 0
thực sự vẫn là 0. Thiếu số áo StatsBomb không lấy player ID giả làm số áo.

Có thể mở file JSON báo cáo khác bằng **Mở hồ sơ JSON**, tối đa 5 MB và
1.000 hồ sơ. Đọc tệp tại trình duyệt, không upload lên backend. Có loading,
thông báo lỗi, nút thử lại khi mẫu chưa tải được và trạng thái báo cáo rỗng.
Không cần backend hoạt động để đọc mẫu/file; badge health chung vẫn có.

## Phạm vi và danh tính

Mỗi nguồn giữ khóa riêng. StatsBomb dùng match ID + player ID, từ chối
ID lặp/lẫn trận, không ghép theo tên; Metrica dùng game/hiệp/khoảng thời
gian/đội/track ID. Không gán người StatsBomb cho ID Metrica hoặc video.

Thống kê StatsBomb là sự kiện hiệp 1–4, không phải phút thi đấu/lần chạm
bóng. Cú sút thành bàn không gồm own goal hoặc luân lưu và không phải tỷ
số trận. Vai trò là tham chiếu nguồn theo index, không nhận diện vị trí
chiến thuật thật. Khi nguồn ghi unknown thì hiện chưa xác định, không
mượn vị trí cũ. Xem `STATSBOMB_PLAYER_PROFILES.md`.

Metrica chỉ mô tả cửa sổ 60 giây, không xếp hạng toàn trận hoặc nhân bù
lên 90 phút. Phân biệt bao phủ vị trí với thời gian chuyển động thực sự
được nhận; khoảng mất mẫu/vượt ngưỡng vẫn bị loại theo báo cáo gốc.
Tốc độ cao nhất là trên khoảng lấy mẫu, không phải tức thời. Đây là
tracking Metrica, không chứng nhận độ chính xác video của người dùng.
Xem `STEP5_PLAYER_PROFILES.md`.

Heatmap đếm khung quan sát, 21 cột ×14 hàng, gốc trái dưới. Vẽ rect với
SVG y=68−(hàng+1)×68/14, không đảo thành gốc trái trên. Độ sáng được
chuẩn hóa trong **hồ sơ đang xem**, không dùng so tuyệt đối hai cầu thủ.
Điểm trắng là vị trí trung vị, không phải vai trò/sơ đồ đội hình.

## Kiểm tra dữ liệu đầu vào

`frontend/src/lib/playerProfiles.ts` chỉ nhận hai kind JSON hiện có.
Kiểm số hữu hạn/không âm, kiểu boolean, ID, số đếm, tổng/index sự kiện,
tỷ lệ chuyền, số bàn không vượt cú sút, tổng event trong ngữ cảnh vai trò.
Metrica cần hệ 105×68 gốc trái dưới, metadata heatmap đúng, tổng ô bằng
số mẫu, tọa độ trong sân và chỉ số chuyển động nhất quán với thời gian
đại diện; không ép dữ liệu sai về giá trị hợp lệ hoặc tự điền số 0.

Parser tạo kiểu view nội bộ cho UI, không sửa JSON nguồn/backend schema.
Không bổ sung xG hoặc cố tính quãng đường từ sự kiện thưa. Việc tích hợp
xG/advisor vào báo cáo HLV là bước 8c.

## Chuẩn bị dữ liệu mẫu

Từ gốc repo sau khi có artifact bước 5:

```powershell
.\.venv\Scripts\python.exe -m backend.tactics.prepare_player_demo
```

Helper yêu cầu output mới `frontend/public/player-demo/`, không ghi đè.
Kiểm cache StatsBomb theo hash, tính lại `build_profiles` và so toàn bộ
27 hồ sơ; kiểm hai nguồn Metrica với manifest đã khóa, tính lại từng
profile và so đủ 22 hồ sơ. Không chạy lại detector hoặc suy luận tên.

Sao chép `statsbomb.json`, `metrica.json`, thêm `manifest.json` cục bộ.
Thư mục này được ignore Git; khi build, Vite xử lý như public asset bình
thường. Nguồn và điều kiện sử dụng giữ theo tài liệu StatsBomb/Metrica
đã có. Không đưa bản ghi cầu thủ/nguồn dữ liệu vào commit.

Hash báo cáo mẫu đã đối chiếu:

- StatsBomb: `96e3c54abae55b0ffd5040d6f82ad38b768acc7f143dc9446699934e6cf68546`.
- Metrica: `3cce6969c7e48d2c771f4d7522599604f8d0f2b5a2cfc00aa97050d128763f38`.

## Nghiệm thu

Từ `frontend`: `npm run test`, `npm run build`, `npm run lint`.
Tổng **8 Node test qua**, gồm bốn test mới cho hồ sơ: nguồn/tên/ID/null,
từ chối trùng/lẫn trận và chỉ số bịa, cửa sổ Metrica/0 khác null, heatmap/
hệ tọa độ/thời gian sai. Không thêm test runner hoặc dependency.

Đã parse dữ liệu thật: 27 StatsBomb, 22 Metrica. Nghiệm thu trình duyệt:

- Tìm Kevin De Bruyne: 42 chuyền/33 hoàn thành/78,6%, 3 cú sút/1 thành
  bàn; Shot có index 85/1214/1567; mở đủ 42 index Pass rồi thu gọn.
- Lọc Brazil trong khi tìm De Bruyne: 0 kết quả, không còn hồ sơ Belgium.
- Đổi sang Metrica xóa bộ lọc cũ, hiện đúng 22 người; ID 4 đội A:
  117,8 m/7,6 km/h trung bình/17,5 km/h cao nhất/55,6 s đại diện,
  1.407 mẫu; heatmap có 22 ô khác 0 và vị trí trung vị y SVG=26,4248.
- 1280 px: danh sách/chi tiết hai cột; 375 px: một cột, không tràn ngang
  ở cả hai nguồn. Đã khôi phục viewport; không có console error.
- Ảnh `data/processed/frontend_player_review_v1/statsbomb.jpg` và
  `metrica.jpg`. Không coi ảnh giao diện là kiểm định độ chính xác nguồn.

Build/lint exit 0; còn cảnh báo bundle >500 kB/Fast Refresh ở button UI.
Từ gốc repo chạy
`pytest -q --basetemp .tmp/pytest_frontend_players_full_v1`:
**280 passed, 1 network deselected**, cảnh báo Starlette/SHAP cũ.
Phần tiếp theo: bước 8c báo cáo HLV.

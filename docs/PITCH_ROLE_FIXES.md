# Sửa hiệu chỉnh sân và lọc vai trò theo màu áo

Ngày02/11/2026. Đã sửa cơ chế học/loại màu ngoài hai đội và bổ sung một
nhánh hiệu chỉnh từ phần sân nhìn thấy. **Chưa giải quyết hoàn toàn hiệu
chỉnh tự động cho mọi clip**: hai clip kiểm vẫn cần mốc tay; clip mới có
tọa độ chỉ khoảng1s nên chưa đủ đưa gợi ý chiến thuật.

## Màu áo và vai trò

Luồng upload vẫn học hai cụm Lab bằng K-means, giữ ngưỡng khoảng cách45
và chênh lệch8. Thêm kiểm màu ngoài bảng màu đội trong không gian hue
tròn, trọng số saturation×value. Tâm/mức phân tán lấy median/MAD từ dữ
liệu hiệu chỉnh; ellipse ba sigma, sàn sigma4. Màu không phù hợp trả
`unknown`, không bị ép vào đội gần nhất.

Đây là **lọc màu ngoài đội**, không phải nhận diện chắc chắn trọng tài
hay thủ môn. Không thể phân biệt vai trò chỉ từ màu khi áo trùng nhau.
Unknown vẫn có ID quan sát trong sân, nhưng không vào các nhóm A/B dùng
tính nhiệt và chiến thuật đội. TrackRoleSmoother không mang nhãn đội cũ
qua một quan sát hiện tại bị từ chối.

Học màu dùng tối đa300mẫu torso. Nếu12khung lấy đều không học được hai
đội, thử lịch bổ sung tối đa72khung (bỏ trùng), chỉ chạy detector ở khung
có biên hợp lệ; dừng khi đủ bằng chứng hoặc12khung bổ sung có biên.
Lưu frame/mẫu/tâm/ngưỡng ở `jersey-palette.json` để kiểm lại. Test giả lập
kiểm trường hợp toàn bộ lượt đầu không thấy biên. Bốn lượt replay thật
đã học được màu ngay ở lịch đầu, không tuyên bố fallback được kiểm trên
clip thật chỉ vì test giả lập đạt.

## Hiệu chỉnh phần sân

Giữ hai fitter hiện có. Thêm nhánh `partial_pitch_calibration.py`:

- Keypoint chỉ gợi vùng/hướng tìm; tối đa ba giả thuyết vạch thật cho mỗi
  vị trí. Chỉ dùng đoạn trắng dài có hỗ trợ pixel, không dùng điểm khuất
  do model đoán như một giao vạch đã nhìn thấy.
- Fit từ hai họ x và hai họ y: có thể là giữa sân/vùng cấm hoặc các cạnh
  vùng cấm. Giao đại số có thể nằm ngoài ảnh, không được gọi là mốc nhìn
  thấy. Không yêu cầu thấy đủ11người hoặc đủ cả sân.
- Cần vòng tròn/cung phạt đền làm bằng chứng riêng, bỏ vùng gần các
  đường fit8px. Bằng chứng cong không tham gia fit ma trận. Mọi vạch đủ
  quan sát vẫn phải qua kiểm đầy đủ; nghiệm gương, horizon cắt sân, nhiều
  nghiệm lệch nhau quá1m bị từ chối.
- Thử ảnh native trước, rồi ảnh640×640 khi chưa có nghiệm. Tọa độ pixel
  ảnh vuông phải đổi về kích thước nguồn trước khi tính homography; không
  kéo giãn hệ sân105×68m.
- Mask tìm kiếm có thể lấy vạch mảnh bị lẫn xanh cỏ nếu đồng thời sáng
  hơn và ít bão hòa hơn lân cận. Mask **duyệt kết quả** giữ giới hạn
  saturation<140 đã có. Không dùng mask tìm rộng để nới duyệt tọa độ.
- Giữ median4px và hỗ trợ65% trong5px cho đường thẳng. Siết vòng tròn/
  cung đối chiếu lên75%: một vòng tròn khớp yếu không được bù bởi các
  đường thẳng đã khớp. Giữ buffer kiểm đóng, optical flow, tuổi300frame,
  giới hạn40km/h và không nối chuyển động qua khoảng trống.

Policy mới: `hybrid_opening_closing_marking_checks_curve75_v2`.
Không đổi TrackingRow/DATA_CONTRACT, thêm dependency hoặc đổi bộ lọc biên
ảnh sản phẩm. Đã thử mask biên rộng hơn nhưng không giữ vì làm giảm một
số khung hợp lệ; baseline lọc người ngoài sân vẫn được giữ nguyên.

## Đo trước/sau trên cùng tracking

Giữ nguyên toàn bộ box, ID, thời gian và polygon của baseline; học lại
màu bằng detector/mẫu nguồn rồi tính lại nhóm. Đã kiểm bằng so sánh mọi
chunk sau khi bỏ riêng trường `group`. Các clone mới chạy hiệu chỉnh
tự động qua API thật; không thêm mốc tay hay fit theo nhãn đánh giá.
Đây là replay có kiểm soát, không gọi là chạy detector mới lần nữa.
Các lượt upload GPU đầy đủ ban đầu của nhánh thử cũng được giữ riêng.

| Clip | Hiệu chỉnh trước | Bản cuối | Vị trí / cửa sổ chiến thuật |
|---|---:|---:|---:|
| Project12 |0s|1,067s|538 /0|
| Project15(1) |0s|0s|0 /0|
| Project15(2) |0s|0s|0 /0|
| Project15 mẫu |24,467s|25,267s|13.978 /4|

Clip mẫu vẫn chỉ khoảng48,3%thời lượng có hiệu chỉnh, không phải cả clip.
Ba clip mới vẫn **0/3đủ dữ liệu chiến thuật**. Không biến một đoạn1s có
tọa độ thành nghiệm thu chiến thuật. Không tuyên bố đã sửa xong độ phủ.

Mẫu vai trò khóa từ phiên trước: Project12 và15(1) giữ24/24lượt tuyến
ngoài ghép được, ảnh sau12/12nhóm màu đúng hoán vị đã chốt. Bốn lượt
trọng tài đổi từ B sang unknown; hai lượt thủ môn cũng unknown.12cặp
ID0,5s giữ nguyên do replay không đổi ID. Project15(2) vẫn0/12mẫu có
box tại các frame đã chốt nên không có kết luận màu/ID tại đó. Palette
cuối của clip này học được từ25mẫu, không còn biến thể thử bị100%unknown.
Đây là mẫu thưa do agent rà, không là accuracy/IDF1 hoặc nhãn độc lập.

## Kiểm sai số và biến thể đã loại

- Clip mẫu cuối: audit nhiệt/vận động/hash không có lỗi nhất quán;
  7/18frame tham chiếu có vị trí để đo đều≤1m,11không đánh giá được.
  Không tính11frame này là đạt và không suy accuracy toàn video.
- Một biến thể phát triển có27,2s nhưng checkpoint1350 lệch1,035m. Giữ
  kết quả/audit đó làm lịch sử, không chấp nhận bằng cách nâng ngưỡng1m.
  Bản cuối dùng witness cong75%; frame đó không thuộc đoạn xuất vị trí.
  Đây là chỉnh theo dữ liệu phát triển, không phải kiểm mù.
- Project12 có một kiểm mốc600 được chọn có điều kiện. Nhãn v1 chứa
  một điểm thực tế bị cầu thủ che, cho max1,807m. Giữ nguyên v1; v2 bỏ
  điểm không nhìn thấy, không dời ba điểm còn lại hoặc fit lại ma trận.
  Kiểm ba điểm còn lại tối đa khoảng0,751m. Đây là sửa nhãn sau khi xem
  lỗi, không dùng để tuyên bố accuracy độc lập.
- 80phép chiếu lệch±5m nhân tạo vẫn bị từ chối; thử âm này không thay
  thế kiểm mốc thật hoặc tạo thành false-positive rate ngoài thực tế.

Tọa độ vẫn là ước lượng với sân105×68m giả định, chưa có đo đạc quãng
đường độc lập. Hiệu chỉnh/nhận dạng vai trò trên hai clip khó và các
trường hợp áo trùng màu vẫn là việc còn lại.

## Kiểm tra và dữ liệu bàn giao

474test Python đạt,1network deselected;8test mới về vùng cấm không thấy
giữa sân, đường fit không tự làm đối chứng, gate toàn ảnh, loại màu lạ,
tìm vạch có lẫn xanh, đổi pixel ảnh vuông, lượt lấy màu bổ sung và witness
vòng tròn. Sửa polling test API: chờ worker xong rồi đọc trạng thái mới,
tránh lấy trạng thái running ngay trước lúc lock được nhả; không nới
yêu cầu ready/các kiểm sản phẩm.

Các job baseline/demo cũ giữ nguyên. File khóa kết quả:
`fixtures/pitch_role_fix_verification_v1.json`; nhãn Project12 v1/v2
được lưu riêng. Chi tiết local tại `data/processed/pitch_role_fix_v1`.
API report/tracking/tactics và Range media đã kiểm, frontend không đổi
bởi nhiệm vụ CV này; chưa có visual UI QA mới.

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m "not network" `
  --basetemp=.tmp/pytest_pitch_role_rerun
```

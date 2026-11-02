# Đánh giá StrikerAI và hướng tham khảo

Ngày02/11/2026, thực hiện sau khi chốt bản sửa CV `d95d663`.
Repo: [KavinSivaharan/StrikerAI](https://github.com/KavinSivaharan/StrikerAI),
khóa commit `b0972ff77905583fd15fae23612e61624ddf23af` ngày14/10/2025.
Đã đọc README, toàn bộ module xử lý chính và notebook huấn luyện;
tree41entry/29file. Không chạy code ngoài, tải model, dùng khóa API,
cài gói hoặc tích hợp mã từ repo trong phiên đánh giá này.

**Đáng tham khảo nhất là detector tách vai trò trước phân nhóm đội và
cách trình bày kết quả trên video. Repo không cung cấp cách hiệu chỉnh
tự động mạnh hơn để giải quyết hai clip khó hiện tại.**

## Phần thực sự có

| Phần | Mã đã kiểm | Ý nghĩa với dự án |
|---|---|---|
| Detector theo lớp + tracker | [tracker.py](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/trackers/tracker.py) | Có nhánh player/referee/ball và đọc goalkeeper; thực tế dùng supervision.ByteTrack, không phải DeepSORT như bảng README |
| Nhóm màu áo | [team_assigner.py](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/team_assigner/team_assigner.py) | K-means trong nửa trên crop, dùng màu các góc làm nền; có thể học ý tưởng tách nền để thử ngoại tuyến |
| Camera | [camera_movement_estimator.py](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/camera_movement_estimator/camera_movement_estimator.py) | Lucas–Kanade lấy vector dịch chuyển; không có bộ phát hiện vạch/mốc sân tự động |
| Chiếu sân | [view_transformer.py](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/view_transformer/view_transformer.py) | Bốn pixel cố định, hình chữ nhật cục bộ23,32×68m; không phải template toàn sân105×68m |
| Vận động | [speed_and_distance_estimator.py](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/speed_and_distance_estimator/speed_and_distance_estimator.py) | Khoảng dịch chuyển trong cửa sổ5frame, FPS cố định24 |
| Hiển thị | [stats_overlay.py](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/utils/stats_overlay.py), tracker.py | Marker ở chân/ID, panel gọn; có thể chuyển ý tưởng sang SVG/frontend đọc JSON |
| xG | [xg_calculator.py](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/utils/xg_calculator.py) | Quy tắc chia khoảng cách/góc, không thấy huấn luyện hoặc đánh giá xác suất |

README liệt kê heatmap, formation, nhận diện chuyền/sút và giao diện web
ở phần kế hoạch. Không thấy triển khai tương ứng trong các module đã
đọc, nên không có engine chiến thuật/khuyến nghị sẵn để cắm vào dự án.
[Nguồn README](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/README.md).

## Ưu tiên1: detector tách vai trò

Tracker giữ trọng tài riêng trước phân nhóm màu. Đây là hướng phù hợp
với lỗi của mình: palette mới chỉ biết từ chối màu lạ thànhunknown,
chưa xác nhận được vai trò. Tuy nhiên, repo đổi goalkeeper thànhplayer
trước tracking/phân đội; không nên lấy thao tác gộp đó vì có thể đưa thủ
môn vào suy sơ đồ tuyến ngoài. [Mã tracker](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/trackers/tracker.py).

Hướng thử phù hợp, chưa triển khai trong phiên này:

1. Dùng YOLO nano/small trong stack hiện có để nghiên cứu các lớp player,
   goalkeeper, referee. Bóng vẫn ngoài luồng chính theo phạm vi đã chốt.
2. Giữ vai trò và đội là hai thông tin riêng trong artifact nội bộ:
   detector nói vai trò, palette nói màu đội. Trọng tài không vào đội;
   thủ môn giữ vai trò để loại khỏi mẫu đội hình tuyến ngoài. Chưa rõ
   thìunknown. Không ép class goalkeeper vào Literal`team` hiện hành.
3. Khóa dữ liệu/model/hash/class-map và nhãn kiểm riêng. Đo precision/
   recall từng vai trò và số lượt trọng tài/thủ môn lọt vào nhóm tuyến
   ngoài; so cùng frame với palette hiện tại. Cần giữ chất lượng cầu
   thủ và đo thời gian/VRAM trên RTX3050 6GB trước khi nối upload.

[Notebook huấn luyện](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/training/football_training_yolo_v5.ipynb)
chỉ định YOLOv5x/100epochs, dùng dataset Roboflow phiên bản1. Không có
checkpoint trong Git, hash/checkpoint card hoặc kết quả mAP để chứng
minh model tải ngoài tốt hơn. Không lấy cấu hình modelx làm mặc định cho
máy6GB. Notebook có chuỗi khóa được ghi là đã thu hồi; không sử dụng.

## Ưu tiên2: thử tách nền crop áo

Ý tưởng lấy cụm nền theo góc crop có thể giúp khi màu cỏ lọt vào vùng
áo. Nên thử như một đặc trưng bổ sung cho torso crop/Lab hiện tại, đo
trên cùng box với nhãn vai trò khóa nguồn. Có thể giữunknown khi hai
cách không nhất quán, thay vì ép một đội.

Không thay nguyên TeamAssigner: nó học màu từ frame đầu, cache nhãn đầu
cho mỗi ID và ép riêng ID91 vào đội1. Thiếu ngưỡng từ chối màu lạ/
confidence; giả định các góc là nền có thể sai khi áo chiếm crop hoặc
có người chồng nhau. Không thấy kiểm crop rỗng/mẫu thiếu. Dự án mình
đã có nhiều khung hiệu chỉnh, gate màu lạ và bỏ phiếu theo thời gian;
cần giữ những kiểm đó. [Nguồn](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/team_assigner/team_assigner.py).

## Ưu tiên3: cách xem kết quả theo thời điểm

Có thể học marker gọn ở chân cầu thủ và panel ít thông tin, đặt ID/nhóm
và chỉ số hợp lệ theo đồng hồ video. Mình đã có SVG box, sân mini đồng
bộ, heatmap và chọn quỹ đạo xem vận động. Phần mới đáng thử là liên kết
chọn một ID giữa video/sân mini/panel, hoặc marker chân thay box khi cần
đỡ che trận đấu; không làm lại các chức năng đã có.

Nếu triển khai, giữ render ở React/SVG từ JSON và hiển thị thiếu dữ liệu
ở đoạn không hiệu chỉnh. Không vẽ ảnh phân tích sẵn ở backend để thay
API JSON; không hiển thị dữ liệu cuối clip như chỉ số hiện tại. Ý tưởng
giao diện này ưu tiên sau chất lượng tọa độ/vai trò.

## Các phần cần giữ thiết kế hiện tại

**Hiệu chỉnh/camera.** Bốn điểm pixel cố định phải được thay cho từng
clip;23,32m là một vùng cục bộ, không phải toàn chiều dài sân. Không thể
đổi thành105m bằng cách kéo tỉ lệ rồi coi mọi vạch là đúng. Cần mốc có
ý nghĩa/offset sân và kiểm độc lập như hiện tại. Homography là phép
chiếu mặt phẳng2D, không dựng sân3D.
[Nguồn](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/view_transformer/view_transformer.py).

Camera chọn vector optical-flow lớn nhất từ hai dải ảnh x cố định,
không fit homography/RANSAC hoặc kiểm thuận-nghịch. Hàm chỉnh vị trí
trừ vector theo frame, không tổng chuyển động về mốc hiệu chỉnh ban đầu.
Vector tịnh tiến không mô tả zoom/phối cảnh. Không thay CameraMotion,
kiểm vạch, kiểm đóng và giới hạn tuổi chuỗi của mình bằng module này.
[Nguồn](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/camera_movement_estimator/camera_movement_estimator.py).

**FPS/vận động.** FPS24 cố định cho tính tốc độ và xuất video. Với nguồn
30fps, công thức đó cho tốc độ bằng24/30=80%giá trị theo thời gian đúng;
ghi frame30fps ở24fps làm video dài1,25lần. Cửa sổ cuối có thể códt0 khi
số frame≡1(mod5), không thấy kiểm trước phép chia. Giữ FPS thật, ngắt
chuỗi khi mất dấu và kiểm tốc độ40km/h của mình.
[Tính vận động](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/speed_and_distance_estimator/speed_and_distance_estimator.py),
[xuất video](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/utils/video_utils.py).

**Bộ nhớ/cache.** read_video giữ toàn bộ ảnh trong list, tracker giữ toàn
bộ detections/tracks; batch20 không biến nó thành xử lý theo đoạn. Stub
pickle không kiểm hash video/FPS/model. Giữ chunk, JSON, nguồn/hash và
phiên bản bất biến của mình để tránh video mới đọc nhầm kết quả cũ.
[Video IO](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/utils/video_utils.py),
[cache tracker](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/trackers/tracker.py).

**xG và bóng.** xG của repo dùng hai đầu đoạn23,32m làm hai khung thành,
hướng tấn công cố định theo số đội và các mức khoảng cách/góc đặt tay.
Ví dụ cách phối trọng số cho mức xa/góc nhỏ vẫn có sàn9,5%. Không có
dataset, training, AUC/Brier để gọi đó là xác suất đã kiểm chứng.
Overlay hiện mỗi khi cóhas_ball, không phải khi xác nhận cú sút.
Giữ xG XGBoost/StatsBomb và các kiểm hiện có của dự án.
[Công thức](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/utils/xg_calculator.py),
[điều kiện hiện](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/utils/xg_overlay.py).

Ball assigner dùng khoảng cách70px; tracker nội suy/bfill bóng và main
giữ chủ bóng trước đó khi không gán được. Không có chặn mất bóng dài
đáng tin cậy; lần đầu không gán được có thể truy cập danh sách rỗng.
Không khởi động lại phát hiện bóng/chuyền/sút từ các thành phần này.
Stats overlay còn dùng tổng cảclip cho từng frame, khác overlay bóng
cắt theo thời điểm; không lấy nó làm baseline realtime.
[Main](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/main.py),
[bóng](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/player_ball_assigner/player_ball_assigner.py),
[stats](https://github.com/KavinSivaharan/StrikerAI/blob/b0972ff77905583fd15fae23612e61624ddf23af/utils/stats_overlay.py).

## Quyền sử dụng và đề xuất hành động

Không tìm thấy LICENSE/COPYING/NOTICE hoặc thư mục kiểm thử trong tree
đã khóa; GitHub metadata cũng không nhận diện license. Model nằm ở link
Drive ngoài repo, chưa kiểm license/hash/class-map của weights. Cần làm
rõ quyền sử dụng trước khi chép mã hoặc đưa checkpoint đó vào sản phẩm.
Đánh giá này chỉ đề xuất ý tưởng, không nhập mã/model từ repo.
[Tree nguồn](https://github.com/KavinSivaharan/StrikerAI/tree/b0972ff77905583fd15fae23612e61624ddf23af).

Đề xuất bước kế tiếp: thử detector vai trò ngoại tuyến trên đúng bộ clip
đã kiểm, giữ unknown và baseline palette; báo lỗi lọt trọng tài/thủ môn,
độ phủ và chi phí GPU. Sau đó mới cân nhắc tách nền áo và overlay chọn
ID. Hiệu chỉnh sân vẫn cần tiếp tục hướng mốc/vạch có kiểm chứng của
dự án; StrikerAI không cung cấp detector mốc sân để thay phần đó.

Khóa nguồn/module đọc và phạm vi kiểm tại
`fixtures/strikerai_review_snapshot_v1.json`. Phiên chỉ đánh giá này
không đổi mã ứng dụng/dependency/DATA_CONTRACT và không chạy lại474test
vừa đạt cho phần sửa CV trước đó.

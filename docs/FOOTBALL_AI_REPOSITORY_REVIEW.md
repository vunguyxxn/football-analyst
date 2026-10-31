# Đánh giá cepat-ai/football-ai — 31/10/2026

## Kết luận

Phù hợp tham khảo Computer Vision, nhất là mốc sân tự động và phân biệt
vai trò. Nên thử từng thành phần ngoại tuyến rồi mới quyết định đưa vào
upload. Chưa có bằng chứng mô hình của repo tốt hơn pipeline hiện tại
trên clip mẫu hoặc RTX3050 6GB; không công bố độ chính xác/hiệu năng
khi chưa chạy benchmark. Phiên này chỉ đọc/đánh giá, không thay mã ứng
dụng, thêm thư viện, tải model hoặc bật tự khởi tạo homography.

Repo được đọc: [cepat-ai/football-ai](https://github.com/cepat-ai/football-ai),
fork của roboflow/sports. Khóa tại commit
`66a3f32ed6297fb3a06ec377448ef78e03b04db6` ngày24/07/2024.
Không gán những chức năng có thể có ở upstream mới hơn cho fork này.
Bản sao đọc trong .tmp/repo_audits/football-ai, được Git ignore.

## Những phần thực sự có trong mã

| Phần | Mã nguồn đã đọc | Giá trị cho dự án |
| --- | --- | --- |
| Detect mốc sân | examples/soccer/main.py, run_pitch_detection/run_radar; notebook train_pitch_keypoint_detector.ipynb | YOLO pose dự đoán mốc theo khung, làm đầu vào cho homography khi camera lia |
| Detector vai trò | main.py và train_player_detector.ipynb | Phân lớp bóng, thủ môn, cầu thủ sân, trọng tài trước phân nhóm đội |
| TeamClassifier | sports/common/team.py | SigLIP embeddings → UMAP3D → K-means2, thay cách trích đặc trưng ảnh cho bước phân nhóm |
| ViewTransformer | sports/common/view.py | OpenCV findHomography/perspectiveTransform; dự án mình đã có phép chiếu và nhiều kiểm tra chất lượng hơn |
| Radar | plot_radar và sports/annotators/soccer.py | Vẽ người trên sân; frontend mình đã có chức năng tương đương, giá trị mới chủ yếu nằm ở tọa độ đầu vào |

Các chế độ chương trình: PITCH_DETECTION, PLAYER_DETECTION,
PLAYER_TRACKING, TEAM_CLASSIFICATION, RADAR. Không thấy module suy sơ
đồ, phân tích thay đổi chiến thuật, khuyến nghị HLV, xG, heatmap hoặc
đánh giá quãng đường/tốc độ trong các file tracked của commit này.
Không nên coi video demo là bằng chứng có sẵn các chức năng đó.

## Ưu tiên1: mốc sân để giảm thao tác tay

run_radar lấy keypoints mỗi khung và ghép với32 đỉnh của cấu hình sân,
sau đó chiếu điểm chân của người lên sân. Phương pháp này không cần
thấy đủ11 cầu thủ: điều kiện nằm ở mốc sân phù hợp, không ở số cầu thủ.
Đây là hướng nghiên cứu hợp với nút thắt hiệu chỉnh clip mới của mình,
nhưng chưa phải giải pháp đã kiểm chứng cho góc quay cận/che khuất.

Các sửa đổi bắt buộc nếu làm prototype:

1. Tạo bảng tương ứng index mốc → ý nghĩa hình học → tọa độ105×68m,
   gốc trái dưới. Không sắp xếp index theo chuỗi nhãn hiển thị.
2. Không chép tọa độ mặc định hoặc chỉ nhân tỉ lệ120→105: cấu hình repo
   dùng12000×7000cm, vùng cấm dài2015cm/rộng4100cm. Cần dựng lại mốc
   theo sân dự án, vùng cấm16,5×40,32m, vùng cầu môn5,5×18,32m và bán
   kính vòng tròn9,15m. Scale đồng loạt sẽ làm sai các kích thước cố định.
3. Chọn mốc bằng confidence/visibility và phân bố không gian, tối thiểu
   bốn điểm không suy biến. plot_radar hiện chỉ lọc x/y>1, không dùng
   confidence để quyết định độ tin cậy của phép chiếu.
4. Thay việc fit homography không có kiểm tra dư bằng cơ chế robust,
   kiểm lỗi tái chiếu, đường chân trời và độ ổn định qua khung. Giữ
   LandmarkGuard/CameraMotion và ngừng xuất tọa độ khi không đủ mốc.
5. Trước mắt dùng keypoint làm neo/cập nhật theo lịch rồi bám camera
   bằng module hiện có, đo tốc độ/VRAM để chọn tần suất; không giả định
   phải chạy hai detector đầy đủ ở mọi khung trên RTX3050.
6. Xuất JSON đúng TrackingRow cho backend/frontend, không trả ảnh radar
   vẽ sẵn thay hợp đồng dữ liệu. Không nối ID/vận động qua đoạn mất mốc.

ROADMAP hiện để tự khởi tạo homography hoàn toàn tự động ngoài phạm vi.
Nếu chọn mục này, cần ghi nhận mở rộng phạm vi trước khi bật; bản đánh
giá này chưa thay ROADMAP hoặc xem đây là chức năng đã được nghiệm thu.

## Ưu tiên2: phân biệt vai trò trước phân nhóm đội

Source định nghĩa ball=0, goalkeeper=1, player=2, referee=3, rồi chỉ
lấy player để huấn luyện/phân nhóm đội. Ý tưởng rất phù hợp lỗi đã thấy
trong dự án:4/9 mẫu trọng tài bị gán B và542 lượt đã phải loại qua rà
nội bộ. Một detector vai trò đủ tốt có thể giảm nhu cầu gán ID thủ công.

Pipeline upload hiện chọn lớp theo tên person của yolo11n.pt. Không
thay trực tiếp file weights bằng model4 lớp: phải kiểm model.names,
map lớp/vai trò, áp lọc trong biên và quyết định rõ loại nào vào chỉ số
cầu thủ sân. Chưa sửa TrackingRow để thêm trường vai trò; có thể dùng
metadata nội bộ như các box/sidecar đang có nếu thiết kế được chấp thuận.

Không lấy nguyên resolve_goalkeepers_team_id: nó gán thủ môn vào đội
có tâm người gần hơn trong tọa độ ảnh. Với camera lia/thiếu người hoặc
đối thủ áp sát vùng cấm, khoảng cách đó không đủ chứng minh đội của
thủ môn. Thiếu một nhóm còn tạo tâm rỗng/NaN; code không có trạng thái
chưa rõ cho phép gán này. Tách nhận diện vai trò khỏi suy đội, giữ
unknown khi thiếu bằng chứng, không tự thêm thủ môn không nhìn thấy.

## Ưu tiên3: thử đặc trưng SigLIP, chưa thay mặc định

TeamClassifier tải google/siglip-base-patch16-224, lấy trung bình token
embedding, UMAP rồi K-means. Có thể thử cho màu áo khó/ánh sáng thay đổi,
nhưng chưa có benchmark chứng minh tốt hơn jersey_feature hiện tại.
Không tự giải quyết trọng tài lẫn nhóm nếu đầu vào vẫn là mọi lớp person;
repo dựa vào detector vai trò để loại trọng tài/thủ môn trước bước này.

Phụ thuộc mới: transformers, umap-learn, sentencepiece/protobuf theo
setup.py; model pretrained tải từ ngoài. Hiện AGENTS chỉ cho thêm thư
viện khi được kiến trúc sư cho phép, nên chưa cài. Cũng cần kiểm tương
thích với môi trường ghim ultralytics8.3.221/supervision0.26.1 của mình.
Không suy ra lỗi chắc chắn chỉ từ tuổi code; phải chạy thử bản cô lập.

Thiết kế khi thử: giới hạn số crop/bộ nhớ, trích đặc trưng theo batch
nhỏ và xếp lịch GPU, seed phân cụm/giảm chiều, khóa mapping A/B giữa
lần chạy, thêm cơ chế unknown cho mẫu xa/mơ hồ. Repo gom mọi crop lấy
mỗi60 khung vào một list, batch mặc định32, UMAP/K-means không ghim
random_state; không nên bê nguyên luồng này vào xử lý video dài.

## Trọng số, khả năng tái tạo và giấy phép

- Các file được main.py yêu cầu là football-player-detection-v9.pt và
  football-pitch-detection-v10.pt; không có weights tracked trong repo.
  setup.sh chỉ tạo thư mục data, không tải model.
- Notebook huấn luyện player dùng YOLOv8x,1280px, Roboflow datasetv10;
  notebook pitch dùng YOLOv8x-pose,640px, datasetv12. Không thể coi các
  notebook này là công thức nano/small phù hợp6GB đã được kiểm chứng,
  hoặc coi tên v9/v10 của file là phiên bản kiến trúc YOLO.
- Source phụ thuộc không ghim phiên bản. Không thấy test tracked; các
  số validation lưu trong notebook không phải kết quả trên clip mình.
- main nhận target_video_path nhưng luồng cuối chỉ cv2.imshow, chưa
  dùng tham số đó để ghi file. Dự án mình đã có upload/job/video kết
  quả/JSON nên không cần thay kiến trúc bằng CLI demo của repo.
- [LICENSE](https://github.com/cepat-ai/football-ai/blob/66a3f32ed6297fb3a06ec377448ef78e03b04db6/LICENSE)
  ghi MIT, copyright Roboflow2024; nếu port mã phải giữ thông báo theo
  license. Điều này không tự xác nhận quyền dùng dataset/trọng số ngoài
  repo; phải kiểm thông tin của đúng bản model/dataset trước khi tải/dùng.

## Thử nghiệm đề xuất, có tiêu chí nhận hay loại

1. Chốt phiên bản/nguồn/quyền sử dụng weights và thứ tự32 mốc/lớp vai
   trò. Chuẩn bị adapter nghiên cứu, chưa nối vào upload mặc định.
2. Mốc sân: dùng cùng clip15 và mốc kiểm riêng để so với bản hiệu chỉnh
   tay hiện hành: độ bao phủ tọa độ, phân bố lỗi mốc, số lần mất/trôi,
   độ rung theo thời gian, hành vi khi cắt cảnh/mốc cùng thẳng hàng;
   đo thêm thời gian/khung và VRAM. Các mốc agent cũ chỉ là kiểm nội bộ,
   cần nhãn độc lập trước khi báo độ chính xác chuyên môn.
3. Vai trò: so detector hiện tại với bản4 lớp trên cùng các ảnh có nhãn;
   đo precision/recall từng lớp và số trọng tài/thủ môn lẫn vào chỉ số
   đội, không chỉ báo mAP tổng. Mẫu180 người hiện có là development,
   không tái sử dụng như test độc lập sau khi tinh chỉnh trên nó.
4. Đặc trưng áo: so cùng crop, cùng split và cùng ánh xạ A/B với cách
   hiện tại; báo cả tỉ lệ chưa rõ, sai nhóm, đổi nhóm theo ID và chi phí.
5. Chỉ công bố kết quả tốt hơn trên dữ liệu kiểm riêng, giữ fallback
   chọn mốc tay và bản đang chạy. Mốc dự đoán sai phải làm thiếu kết
   quả, không tạo heatmap/quãng đường/gợi ý chiến thuật giả.

## Kiểm tra đã làm ở phiên đánh giá

Đọc README, LICENSE, setup.py, toàn bộ main.py, common/team.py,
common/view.py, configs/soccer.py, phần vẽ sân và code cell của hai
notebook. Đối chiếu upload_analysis.py, hợp đồng sân và tiến độ dự án.
AST parse các file Python để kiểm cú pháp, liệt kê file tracked để
kiểm weights/tests; không thực thi mã repo, chạy setup/notebook, cài
dependency, tải weights, train hoặc benchmark. Audit cục bộ tại
.tmp/repo_audits/football-ai-static-audit.json. Ứng dụng không thay đổi.

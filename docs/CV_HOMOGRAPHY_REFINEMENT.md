# Rà soát hiệu chỉnh ban đầu — 22/10/2026

## Kết quả

Đã phóng lớn frame 600, rà các giao điểm vạch và chạy lại 300 bước camera.
Chỉ sửa vị trí bốn điểm chưa giảm sai số rõ rệt trên dữ liệu phát triển.
Bổ sung hai mốc tay của vòng tròn giữa sân làm điểm ràng buộc giúp giảm
sai số trên hai frame mới, nhưng không cải thiện đều ở mọi vị trí. Chưa
nghiệm thu tốc độ/quãng đường và chưa chuyển sang bước 5.

Không đổi `CameraMotion` hoặc ngưỡng mất dấu, không đổi hợp đồng dữ liệu,
không thêm thư viện. Chế độ hiệu chỉnh bốn điểm vẫn giữ hành vi cũ; thêm
lựa chọn hiệu chỉnh với điểm phụ trong cấu hình CLI.

## Nguồn và giả định

Nguồn và khoảng thử giống lượt trước: bản cắt SHA256
`86f6f04ce05ac464269dfa4d831bef0c12c3654acdd2fa3c1b6379f864597b2e`,
1280 × 720/60 FPS, frame 600–900 (giây 20–25 video gốc), 301 ảnh.
Người dùng không biết link gốc/tên trận/sân. Vì vậy chưa xác minh được kích
thước sân cụ thể; tiếp tục **giả định** sân 105 × 68 m. Không tự suy đoán
danh tính sân qua hình ảnh khán đài. Các sai số theo mét phụ thuộc giả định
này và nhãn ảnh do agent quan sát, chưa được người gán nhãn độc lập xác nhận.

Kích thước vùng cấm, bán kính vòng tròn và cung vùng cấm theo
[IFAB Law 1](https://theifab.com/laws/latest/the-field-of-play/). Mốc mới là
giao cung vùng cấm với đường trước vùng cấm: x = 16,5;
y = 34 ± sqrt(9,15² − 5,5²), tức khoảng 41,3125 và 26,6875 m.

## Rà điểm và khóa cấu hình

Phóng lớn 3 lần các vùng giao vạch ở frame 600. Chọn thủ công các dải vạch
lân cận, lấy pixel sáng V > 185, S < 140 trong HSV OpenCV, fit đường thẳng
Welsch bằng OpenCV rồi lấy giao hai đường. Dải vạch và phương trình fit
được lưu trong fixture, không tự nhận diện mốc sân toàn ảnh. Bộ lọc trắng
chặt hơn ban đầu không lấy được vạch vùng cấm bị ám màu cỏ; đã điều chỉnh
trên frame phát triển trước khi xem các frame kiểm tra mới.

| Mốc | Pixel cũ | Giao điểm rà lại |
|---|---|---|
| Góc sân trái phía xa | (111, 191) | (110,162; 193,099) |
| Góc trước vùng cấm phía xa | (300, 234) | (300,739; 232,847) |
| Giữa sân × biên xa | (1016, 213) | (1017,013; 216,474) |
| Giữa sân × biên gần | (1076, 636) | (1073,855; 634,703) |

Số lẻ là đầu ra fit số học, không có nghĩa ảnh đã được gán nhãn chính xác
đến phần nghìn pixel. Chỉ dùng bốn giao điểm này vẫn có lỗi phát triển
khoảng 1,09/1,18 m ở hai mốc vòng tròn frame 600. Không tuyên bố chỉ click
chính xác hơn là đã giải quyết được vấn đề.

Chọn thêm hai điểm vòng tròn (1027,295), (1040,389) từ nhãn cũ làm ràng buộc
hiệu chỉnh tại frame 600. **Chúng đã chuyển thành dữ liệu hiệu chỉnh**, không
còn là tập kiểm tra. Các nhãn cũ frame 600/750/900 thuộc dữ liệu phát triển.
Fit ma trận sân → ảnh trên sáu mốc, tối thiểu sai số pixel, lấy nghịch đảo
để chiếu tọa độ ảnh về sân. Không sửa điểm/mô hình/ngưỡng sau khi xem đánh
giá mới. Fixture lưu cấu hình đã khóa trước khi gán nhãn frame 675/825.

Lượt chạy mới đọc lại frame nguồn và tính lại optical flow/RANSAC với mask
sân mới; dùng **bbox person cache từ YOLO thật của lượt trước**, không chạy
YOLO lần nữa. Cache có cùng frame/hash và cấu hình YOLO11n, confidence 0,1,
image size 1280, CUDA. Không phải một lượt đo tốc độ toàn pipeline/GPU mới.

## Đánh giá trên frame mới

Hai frame 675 và 825 được chọn/gán nhãn sau khi khóa cấu hình. Không phải
clip/trận độc lập, vẫn có tương quan giữa các frame gần nhau.

- 8 kiểm tra theo thời gian: giao đường giữa sân với vòng tròn và hai biên,
  4 điểm/frame. Loại mốc đã dùng fit, nhưng ở frame chưa dùng trước đó.
- 3 điểm hình học mới: giao cung vùng cấm với đường trước vùng cấm, một điểm
  xa ở frame 675, hai điểm ở frame 825. Điểm gần frame 675 bị cầu thủ che,
  loại khỏi nhãn trước khi tính sai số.
- So sánh cũ/mới trên **cùng các điểm mới**, không so trực tiếp số 1,20 m
  của bộ kiểm tra cũ với 0,38 m của bộ mới.

| Nhóm | Số điểm | Trung bình cũ → mới | Lớn nhất cũ → mới |
|---|---:|---:|---:|
| Mốc theo thời gian, frame mới | 8 | 0,81 → 0,38 m | 1,44 → 0,96 m |
| Mốc hình học mới ở cung vùng cấm | 3 | 0,69 → 0,50 m | 0,88 → 0,87 m |

Từng mẫu có trong `evaluation.json` cục bộ. Giao biên phía xa tại frame
675/825 có sai số **tăng** lần lượt 0,61 → 0,96 m và 0,51 → 0,81 m;
một số vị trí chiếu vượt biên sân. Pipeline tọa độ vẫn bỏ ngoài sân, không
clamp để làm đẹp kết quả. Ở cung gần frame 825, lỗi còn 0,87 m, gần như
không cải thiện. Không dùng trung bình tốt hơn để kết luận mọi vùng tốt hơn.

Chuỗi camera: 1 `manual_anchor`, 300 `tracked`, không lost; đọc lại đủ 301
frame diagnostic. Nhãn ảnh/thực địa còn chưa xác minh và tập mẫu nhỏ; sai
số tọa độ giảm không tự chứng minh sai số tốc độ/quãng đường đã đạt yêu cầu.

## Artifact, kiểm tra và tiếp tục

Fixture được commit riêng, giữ fixture cũ:
`docs/fixtures/vid1_11f23eea_homography_refined.json`.
Artifact cục bộ tại `data/processed/clip_11f23eea/homography_refined_600/`:
`calibration_refined.json`, `camera_quality.jsonl`, `evaluation.json`,
`diagnostic.mp4`, `check_675.jpg`, `check_825.jpg`, ảnh phóng lớn và ảnh mốc.
Helper khảo sát ở `.tmp/refine_anchor.py`, `.tmp/run_refined_camera.py`,
`.tmp/evaluate_refined_camera.py`, không phải công cụ đóng gói cho fresh clone.

Chạy lại CLI bằng fixture mới (video đầu ra và thư mục phải mới):

```powershell
$env:YOLO_CONFIG_DIR = "$PWD\data\processed"
$env:MPLCONFIGDIR = "$PWD\.tmp\matplotlib"
.\.venv\Scripts\python.exe -m backend.cv.track_video data/processed/clip_11f23eea/vid1_11f23eea_clean.mp4 data/processed/clip_11f23eea/refined_full.mp4 --weights data/raw/yolo11n.pt --device 0 --image-size 1280 --calibration docs/fixtures/vid1_11f23eea_homography_refined.json --pitch-output data/processed/clip_11f23eea/refined_full --compensate-camera
```

Lệnh trên sẽ đọc toàn bản cắt, chỉ chiếu frame 600–900. Lượt khảo sát này
chạy đúng 301 frame camera bằng cache bbox; chưa chạy CLI toàn bản cắt.

Kiểm thử mới: dữ liệu phối cảnh có nhiễu click, đối chiếu điểm độc lập biết
trước; kiểm tra mốc phụ sai/thiếu/trùng, loader và pixel ngoài ảnh. Toàn bộ
73 passed, 1 network test deselected; còn cảnh báo Starlette cũ. Đã kiểm tra
CLI `--help`. Cửa sổ click vẫn cần người dùng vận hành cho nguồn video mới;
lượt này dùng tọa độ quan sát và fit đường trong helper khảo sát.

Bước tiếp theo phù hợp là kiểm tra thêm đoạn lia/zoom khác và ranh giới
mất hiệu chỉnh với mốc mới, giữ các mẫu hiện tại làm phát triển nếu chỉnh
tiếp. Đối chiếu chất lượng vị trí chân/ID trước khi đo chỉ số cầu thủ.

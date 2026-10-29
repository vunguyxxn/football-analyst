# Mở rộng hiệu chỉnh sân clip mẫu — 29/10/2026

## Kết quả hiện hành

Video Project 15.mp4, SHA256 f51735a042b493eba3cced891209fe1b6beb20ca80e20c340c7ede51900495d0,
job c140f8aefb4e4678b51fe6f633e1fc56. Không chạy lại YOLO/ByteTrack;
chiếu lại khung người đã lọc biên bằng hiệu chỉnh theo camera. Sân vẫn
giả định 105×68 m. Không đổi DATA_CONTRACT hoặc thêm thư viện.

| Chỉ số | Bản trước | Bản v4 đã công bố |
| --- | ---: | ---: |
| Khoảng camera có hiệu chỉnh và kiểm tra | 19,93 giây | 42,20 giây |
| Khung có vị trí người hợp lệ | 592 | 1.198 |
| Tổng thời gian các khung có vị trí người | 19,73 giây | 39,93 giây |
| Lượt vị trí người | 11.591 | 23.128 |

Các khoảng thực sự được xuất tọa độ:

- 0,033–10,000 giây;
- 10,033–15,033 giây;
- 20,033–25,000 giây;
- 30,033–40,000 giây;
- 40,033–50,000 giây;
- 50,033–52,367 giây.

Khoảng hiệu chỉnh có thể chứa khung không có người hợp lệ do thiếu biên,
lọc ngoài sân hoặc bộ làm mượt từ chối. Các số này là độ bao phủ, không
phải accuracy. Chỉ số chiến thuật vẫn yêu cầu >=4 người cùng nhóm trong
>=5 giây và >=50% cửa sổ: đoạn0–10s đã có kết quả A/B, nhưng đoạn10–15s
chỉ còn3,5s đủ người;20–25s và50–52s cũng chưa đủ thời lượng. Không hạ
điều kiện để lấp kết quả. Tổng heatmap/vận động vẫn tính các quan sát
hợp lệ ở những đoạn này, không nối quãng đường qua mốc mới/mất dấu.

## Mốc và kiểm tra

Fixture v3 là bản thử: thêm neo tại0,300,600,750,1500; giữ nguyên neo
900/1200 của v2. Neo0/750/1500 dùng góc/giao vạch chọn từ ảnh gốc;
neo300/600 dùng vòng tròn giữa sân và giao đường giữa sân với hai biên
do agent định vị tay. Dùng mô-đun circle_calibration đã có, không khởi
tạo homography tự động cho video bất kỳ. Rà thêm ảnh crop để sửa nhãn
điểm kiểm tra pixel ở neo1500 trước lượt chạy chuỗi; không gọi là đánh
giá độc lập. Nhận định ban đầu về cắt cảnh từ contact sheet chưa được
xác minh và không dùng làm nhãn cắt cảnh.

Kiểm tra theo lịch tối đa150 khung, ngưỡng1m; kiểm pixel neo tay10px,
giữ nguyên. Check599/601 thêm góc vùng cấm địa và giao cung tròn nằm
ngoài đường giữa sân, không đưa vào fit vòng tròn. Điều này quan trọng:
các điểm trên một đường thẳng có thể vẫn khớp khi tỉ lệ dọc x đã sai.

Hai lỗi phát triển đã ghi nhận, không sửa nhãn/nới ngưỡng để nhận:

- Check599 ở khoảng19,967s: sai lệch lớn nhất1,0459m tại góc cấm địa.
  Các điểm giữa sân chỉ lệch0,25–0,36m nên bản chỉ kiểm giữa sân từng
  bỏ lọt. v4 rút cửa sổ neo300 về sau check450 đạt: kết thúc frame451.
  Giữ checkpoint599 trong excluded_checkpoints và audit để truy xuất;
  không giữ phần dự đoán15,033–20s chưa có kiểm tra đóng đạt.
- Check751 ở25,033s lệch1,1066m; giữ neo thất bại để hiển thị cửa sổ
  thiếu dữ liệu25–30s, không xuất vị trí nào trong cửa sổ đó. Sau khi
  mất mốc, check899 không chạy; không ghi nhận nó là đạt.

Bản v4 có15 checkpoint đạt; sai lệch nội bộ lớn nhất0,8239m tại những
điểm đạt. Không suy rộng thành sai số tọa độ cầu thủ <=1m, không xem
đây là đo thực địa độc lập. Cùng agent chọn mốc, xem lỗi và chọn phạm
vi sau thử nghiệm; cần nhãn/đo độc lập để nghiệm thu chất lượng.

## Công bố có kiểm tra và khôi phục

project_uploaded_job ghi SHA256 fixture mốc và lịch kiểm tra, từ chối
khi file thay đổi trong quá trình chiếu. publish_pitch_estimate chỉ
chấp nhận nguồn/job/fixture khớp, hệ sân đúng, số dòng/khung đúng,
tọa độ/thời gian hợp lệ, không trùng ID/frame. Mỗi khoảng công bố phải
có checkpoint đạt tại khung đầu và cuối, đủ lịch, không vượt khoảng
cách tối đa hoặc chứa lỗi; không cho kéo qua hai neo khác nhau.

Kiểm tra toàn bộ trước khi thay bản đang hiển thị. Chuẩn bị cặp report/
tracking trong thư mục tạm cục bộ, đổi tên thư mục cũ thành backup,
đưa bản mới vào; nếu bước cuối lỗi thì khôi phục bản cũ. Candidate
nguyên trạng vẫn giữ. API pitch-tracking kiểm tra SHA256 tracking khớp
publication trước khi trả dữ liệu. Không ghép report mới với rows cũ.

Lệnh tái tạo, chạy từ gốc repo; dùng thư mục output chưa tồn tại:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.project_uploaded_job data/processed/video_jobs/c140f8aefb4e4678b51fe6f633e1fc56 docs/fixtures/clip_f51735_manual_pitch_v4.json data/processed/pitch_expansion_new --landmark-checks docs/fixtures/clip_f51735_landmark_checks_v4.json
.\.venv\Scripts\python.exe -m backend.cv.publish_pitch_estimate data/processed/video_jobs/c140f8aefb4e4678b51fe6f633e1fc56 data/processed/pitch_expansion_new docs/fixtures/clip_f51735_manual_pitch_v4.json docs/fixtures/clip_f51735_landmark_checks_v4.json
.\.venv\Scripts\python.exe -m pytest tests/test_pitch_publication.py tests/test_pitch_estimate_api.py -v --basetemp .tmp/pytest_pitch_publication
```

Candidate đã chạy: data/processed/calibration_expansion_v1/projection_v4/.
Backup cũ: job/pitch-estimate-backup-ae61aa98595247c88d9b1037c07ee8b3/.
Audit gọn có hash/độ bao phủ/các lỗi phát triển tại
docs/fixtures/clip_f51735_expansion_audit_v1.json. Các fixture v3 giữ
để tái tạo lỗi, không phải bản công bố. Giao diện chỉ nạp v4 đã cài.

## Kiểm tra

13 test mới cho kiểm nguồn, fixture thay đổi, kiểm đóng thiếu/lỗi,
khoảng kiểm quá xa, dòng ngoài khoảng/trùng/sai tổng, backup/rollback,
binding hash ở API, tính hợp lệ fixture và thay đổi đầu vào khi đang
xử lý. Không tạo test so mAP/accuracy từ chính các mốc đã chọn.

# Ghép dữ liệu v14 và khóa lấy mẫu trước huấn luyện

Ngày 05/11/2026. Chỉ chuẩn bị dữ liệu; **chưa train, chưa inference hoặc
đổi model ứng dụng**. Ghép v11 với release v12/v13 vào thư mục riêng
`data/processed/role_merged_dataset_v14/dataset`, không ghi đè nguồn.

## Số liệu từ nhãn thực tế

| Split | Lượt ảnh | Đơn vị pixel–label | Ảnh/khung nguồn | Player | Goalkeeper | Referee |
|---|---:|---:|---:|---:|---:|---:|
| Train | 418 | 324 | 260 | 5006 | 242 | 652 |
| Val | 128 | 128 | 128 | 2557 | 92 | 292 |
| Known test | 35 | 35 | 35 | 695 | 12 | 76 |

Cột nhãn là tổng theo lượt lấy mẫu. Trên324 đơn vị train pixel–label:
4556 player,206 goalkeeper,576 referee. Không gọi các ROI chồng nhau là
những người khác nhau. Train có9 đơn vị nền âm/15 lượt; gồm6 đơn vị/
12 lượt cũ và3 đơn vị/3 lượt mới. Val/test không có vùng âm rỗng nhãn.
Có21 family train, là nhóm bối cảnh/nguồn với độ hạt khác nhau, không
phải21 trận chính thức đã xác minh.

Phần thêm mới:9 ROI,8 ảnh gốc,7 nhóm bối cảnh;6 vùng sân/3 vùng âm,
85 player/6 goalkeeper/10 referee. Các số này giữ nguyên release v12/v13.

## Cách lấy mẫu đã khóa

- Giữ toàn bộ409 lượt train v11, kể cả số lặp cũ. Không sửa lớp, geometry
  hoặc tăng repeats để cân bằng lớp. Chỉ thêm metadata `sampling_parent`.
- Mỗi ROI mới đúng1 lượt. Không lặp2 lần cho các ảnh mới để bù ảnh29.
- Ảnh29 v12: vùng sân1 + vùng nền âm1 =2 lượt cùng một parent. Cả hai
  được lưu và thống kê chung ảnh gốc, không coi là hai mẫu độc lập.
  Cap2 áp dụng cho ROI mới trong cùng parent, chỉ cho cặp âm/dương đã rà.
- Bảy parent mới còn lại mỗi parent1 lượt. Ảnh79/186 cùng WOB–RBL có2
  parent nhưng1 nhóm bối cảnh, tổng2 lượt. Không tính thành hai trận.
- Ledger khóa từng image/hash/label/hash/parent/family và số lượt tổng
  theo parent/nhóm. Parent ảnh nhận dạng bằng SHA256 nguồn; video dùng
  SHA256 video + frame. Không lấy tên crop hoặc prefix làm ảnh gốc.
- Đây là giữ baseline rồi thêm ROI một lần, chưa phải lấy mẫu đồng đều
  toàn bộ parent. Ngân sách parent cũ không đều: có parent19 lượt do
  full frame/crop/lặp cũ; bảng ledger nêu rõ, không phát sinh tăng mới.
  Epoch shuffle/augmentation của một lần train tương lai giữ cấu hình cũ.

Fixture khóa: `docs/fixtures/role_parent_sampling_v14.json` và
`docs/fixtures/role_sources_training_protocol_v14.json`. Protocol kế thừa
COCO11s fresh AdamW20epoch640/batch4/FP32/lr0.0003/seed20261102, không
multi-scale; đây chỉ là cấu hình cho bước train sau, chưa thực thi.
So đủ3 lớp ở640/1280 với v6/v11; confidence0.25, NMS0.7, matchingIoU0.5,
max_det300, APconf0.001, không cross-role dedup. Gate cũ tại640 đối chiếu
v6 giữ nguyên; chọn checkpoint/khóa val trước khi xem known test.
Phiên này không tạo training plan, run hoặc kết quả so mô hình.

## Kiểm tra dữ liệu và tái tạo

Runner xác thực hash manifest/protocol/packet/group/license/weights tham
chiếu, mọi ảnh/nhãn cũ và mới; dựng lại nhãn mỗi ROI từ ledger nguồn đã
rà và đối chiếu geometry/pixel. Kiểm lớp0/1/2, hữu hạn, tọa độ chuẩn hóa,
nhãn rỗng chỉ ở ROI âm mới. Phân bố được đọc từ TXT, không dựa vào
`class_counts` thiếu ở một số record legacy.

Screen lại482 SHA ảnh tham chiếu duy nhất: mọi split v11 và releasev8/v9,
kể cả128057 chỉ dùng đối chiếu dữ liệu. So SHA file/pixel và dHash<=4
kết hợp MAE grayscale<=3 với parent/ROI mới; kiểm giữa các parent mới,
cho phép ROI29 chung parent đã khai báo. Không có hit. Heuristic này
không chứng minh độc lập trận; giữ kết quả rà bối cảnh v12/v13.

128val/35test giữ nguyên đường dẫn và SHA256 ảnh/nhãn. Chặn giao parent,
family/source/pixel giữa split, chặn match128057 trong bộ ghép và sai
ledger/số lượt/số split. Kiểm lại v11 và release nguồn sau khi copy.
Không sao chép val/test sang train, không chạy detector để chọn nhãn.

```powershell
.\.venv\Scripts\python.exe -m backend.cv.prepare_role_merge_v14
.\.venv\Scripts\python.exe -m backend.cv.prepare_role_merge_v14 --output .tmp/role_merge_v14_replay/dataset
.\.venv\Scripts\python.exe -m pytest -q tests/test_prepare_role_merge_v14.py --basetemp .tmp/pytest_merge_v14_target
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_merge_v14_full_final
```

Đích phải là thư mục dataset mới, chưa có summary trong thư mục cha.
Các lệnh mẫu đã chạy; tái chạy cần chọn `--output` mới. Replay cho
manifest byte-identical và summary giống hệt. Artifact có data.yaml,
manifest, PNG/TXT, summary và attribution; không commit ảnh/nhãn thô.

Manifest SHA256:
`36ccf26608d992315715b6fd3b58d37e71d1b9fecd0ec10603834b5e4049933f`.
Protocol SHA256:
`1f25d9d504c4c56b3160cb1b560dfec16e145223cb8b092084a73decf37e54ab`.
Ledger SHA256:
`3169d98fb59a8ff74d455d71e4db789e224ea97da2e88ac45018fb10192a18c2`.
Kết quả ở `docs/fixtures/role_dataset_merge_summary_v14.json` và
`role_dataset_merge_replay_v14.json`.

Sáu test mới kiểm cap parent âm/dương, không tăng repeats, cấu hình đối
chiếu, ledger thiếu/thừa/sai parent/nhãn, leakage/heldout và nhãn không
hợp lệ. Toàn bộ614 passed/1 network deselected/4 warning cũ.

## Giới hạn và bước tiếp

Nhãn do agent rà, chưa nghiệm thu độc lập; nguồn mới vẫn nhỏ và nhóm
bối cảnh chưa phải danh tính trận đã xác minh. Không có bằng chứng cải
thiện mô hình vì chưa train/chấm. Giữ nguyên bất cân bằng baseline giúp
đối chiếu nhưng không giải quyết mọi ảnh hưởng từ crop/lặp cũ.

Bước sau, khi được giao train: xác thực lại protocol/ledger/manifest,
tạo plan khóa hash trước chạy small, rồi so đủ ba lớp ở640/1280 theo
phép chấm đã khóa. Chưa tự tăng epoch, sửa ngưỡng hoặc triển khai model.

# Bước 2: YOLO + ByteTrack

Chạy từ gốc repository bằng Python trong `.venv`. Bước này phát hiện lớp
`person`, gồm cầu thủ, trọng tài và có thể cả người ngoài sân. Phân loại đội và
loại trọng tài thuộc bước 3. ID tracking không phải định danh cầu thủ.

## Môi trường

RTX 3050 6GB; dùng PyTorch CUDA 12.8. Giá trị CUDA trên `nvidia-smi` là khả năng
của driver, khác với CUDA runtime đi kèm bản PyTorch.

```powershell
.\.venv\Scripts\python.exe -m pip install torch==2.8.0+cu128 torchvision==0.23.0+cu128 --index-url https://download.pytorch.org/whl/cu128 --extra-index-url https://pypi.org/simple
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-cv.txt
.\.venv\Scripts\python.exe -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

Đặt weights COCO `yolo11n.pt` tại `data/raw/yolo11n.pt` và clip tại
`data/raw/clip.mp4`. Weights có thể tải từ bản phát hành chính thức của
[Ultralytics](https://github.com/ultralytics/assets/releases).

## Chạy

```powershell
$env:YOLO_CONFIG_DIR = (Resolve-Path data/processed).Path
$env:MPLCONFIGDIR = Join-Path $env:YOLO_CONFIG_DIR '.matplotlib'
.\.venv\Scripts\python.exe -m backend.cv.track_video data/raw/clip.mp4 data/processed/clip_tracked.mp4 --weights data/raw/yolo11n.pt --device 0 --chunk-seconds 10
```

Chương trình đọc và ghi từng frame trong từng đoạn, không giữ danh sách frame
trong RAM. Tracker giữ nguyên trạng thái khi sang đoạn tiếp theo. Video đầu ra
là MP4 không âm thanh, cùng kích thước và FPS nguồn, có khung và ID.
Kết quả tóm tắt JSON in ra terminal; API FastAPI không thay đổi.
Không ghi đè file đã tồn tại. Nếu xử lý lỗi giữa chừng, video đã ghi có thể chỉ
chứa một phần clip; lệnh trả mã lỗi và không in kết quả thành công.

Nếu chưa cài được bản CUDA, có thể kiểm tra chức năng bằng bản PyTorch CPU
và truyền rõ `--device cpu`. Kết quả này không thay thế nghiệm thu GPU.
Khi chạy trong môi trường giới hạn thư mục ghi, đặt `YOLO_CONFIG_DIR` và
`MPLCONFIGDIR` vào thư mục bên trong repository trước khi chạy để các thư viện
lưu cấu hình/cache tại đó.

## Nghiệm thu

- Chạy test từ gốc repo: `pytest -v`.
- Chạy lệnh trên với clip bóng đá thật; kiểm tra JSON có số frame và số đoạn.
- Mở video đầu ra, kiểm tra khung bám người và ID, nhất là qua mốc đoạn 10 giây.
- Đối chiếu FPS, kích thước và số frame với video nguồn bằng OpenCV.
- Ghi nhận mất ID khi che khuất/chuyển cảnh; chưa tuyên bố độ chính xác tracking
  nếu chưa có dữ liệu gán nhãn để đo.

## Tài liệu API

- [Ultralytics predict](https://docs.ultralytics.com/modes/predict/)
- [Supervision ByteTrack](https://supervision.roboflow.com/0.26.1/trackers/)
- [PyTorch CUDA wheels](https://docs.pytorch.org/get-started/previous-versions/)

# Lộ trình

## Vai trò và thời hạn

- Nhóm 2 sinh viên: Nguyễn Tuấn Vũ (trưởng nhóm), Võ Nhật Hào.
- GVHD: THS. Hà Thị Minh Phương.
- Đề tài: hệ thống AI phân tích bóng đá hỗ trợ HLV (CV + dữ liệu sự kiện).
- Hạn nộp kết quả: 01/12/2026.
- Thời gian bảo vệ: 07/12/2026–03/01/2027.

## Đã xong

- Bước 0: khung dự án.
- Bước 1: StatsBomb loader + pass network.
- Bước 1.5: frontend shell + Pitch + trang Phân tích trận.
- Bước 1.6: tên ngắn cầu thủ.

## Còn lại

Mỗi bước nghiệm thu bằng test/lệnh và có commit riêng.

- **Bước 2:** YOLO + ByteTrack trên clip, xuất video có khung và ID (cài PyTorch CUDA 12.x, RTX 3050 6GB, video xử lý theo đoạn).
- **Bước 3:** Phân loại đội theo màu áo (K-means), loại trọng tài; đo độ chính xác trên mẫu gán nhãn tay.
- **Bước 4:** Homography 4 điểm chọn tay, tọa độ sân 105 × 68 m, quãng đường, tốc độ, heatmap (cầu thủ không chạy quá khoảng 40 km/h).
  Phạm vi bổ sung được người dùng xác nhận ngày 22/10/2026: bù chuyển động
  camera giữa các mốc hiệu chỉnh tay, kiểm tra chất lượng và ngừng xuất tọa
  độ khi mất dấu; chọn lại mốc để tiếp tục. Không yêu cầu camera cố định.
- **Bước 5:** Nhận diện sơ đồ đội hình, chỉ số cầu thủ (so khớp đội hình StatsBomb).
- **Bước 5b:** Fine-tune YOLO nano/small trên dữ liệu bóng đá, so sánh mAP trước/sau.
- **Bước 6:** Mô hình xG (XGBoost), AUC và Brier so với xG của StatsBomb.
- **Bước 7:** Module gợi ý HLV: ML + SHAP, mỗi gợi ý truy được chỉ số căn cứ (LLM diễn giải chỉ làm nếu dư thời gian).
- **Bước 8a/8b/8c:** Frontend: trang video + sân 2D mini đồng bộ, hồ sơ cầu thủ, báo cáo HLV, hoàn thiện loading/lỗi/responsive.
- **Bước 9:** Đánh giá tổng thể, số liệu cho báo cáo (>= 20 trang), slide tiếng Anh.

## Không làm

- Phát hiện bóng chính xác.
- Tự nhận diện mốc sân/khởi tạo homography hoàn toàn tự động. Cho phép cập
  nhật homography theo chuyển động camera sau hiệu chỉnh tay như bước 4.
- Nhận diện sự kiện từ video.
- Dự đoán kết quả trận.

## Phương án dự phòng

Nếu tracking video kém, dùng Metrica tracking data cho B, C và báo cáo kèm phân tích nguyên nhân.

## Nguyên tắc

- Chức năng đúng trước, làm đẹp sau.
- Mỗi prompt một việc.
- Không đổi hợp đồng dữ liệu khi chưa được phép.
- Commit trước khi đổi agent.

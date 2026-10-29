# Phân tích chiến thuật từ phần video quan sát được

## Phạm vi

Theo yêu cầu 29/10/2026, ưu tiên heatmap, hình thái đội và các phương án
chiến thuật, dừng nghiên cứu bóng/chuyền/sút ở luồng video chính. Không
đòi hỏi camera thấy đủ 11 người, không ghép cầu thủ ở các thời điểm khác
nhau thành đội hình đầy đủ. Không đổi các schema dùng chung.

`GET /api/video-jobs/{id}/tactics` trả DTO video nội bộ. API kiểm tra
job/hash nguồn/hệ tọa độ qua pitch-estimate, đọc TrackingRow giới hạn
20 MB/200.000 dòng; kiểm thời gian, trùng ID/frame, giới hạn sân và đoạn
hiệu chỉnh. Tính lại mỗi lần, kèm SHA256 các đầu vào để truy xuất.
Thiếu hiệu chỉnh trả not_available, thiếu bằng chứng trả null và không
đưa gợi ý. Không phụ thuộc dữ liệu bóng hoặc gọi lại YOLO.

## Chỉ số quan sát

- Chia theo từng cửa sổ hiệu chỉnh và nhóm áo A/B, không dùng unknown/
  trọng tài; chỉ dùng thời điểm có 4–11 đối tượng cùng nhóm.
- Cần ít nhất 5 giây hợp lệ, bao phủ >=50% cửa sổ. Heatmap 21×14 cộng
  1/fps giây cho từng vị trí thật. Tổng là giây-người quan sát, không phải
  kiểm soát bóng; màu chuẩn hóa riêng, vùng tối có thể ngoài camera.
- Tính bề ngang, chiều dọc, người hỗ trợ gần nhất, khoảng x liền kề lớn
  nhất, tâm cụm trên từng thời điểm; lấy trung vị sau đó. Không tính
  cự ly giữa hai người ở hai thời điểm khác nhau hoặc coi ID là danh tính.
- Tỷ lệ lượt vị trí trong ba dải y bằng nhau là mô tả vùng quan sát;
  không suy ra cánh trái/phải theo hướng tấn công hoặc mật độ toàn đội.

## Các giả thuyết sơ đồ khi thiếu cầu thủ

Module riêng partial_formation, không hạ điều kiện của mô-đun đầy đủ
11 người đã có. Cần 6–10 người cùng nhóm, trải ít nhất 12 m mỗi trục;
giả sử những người này là cầu thủ sân. Thủ môn lẫn nhóm là nguồn sai
số chưa giải quyết; 11 người chưa rõ vai trò không tự bỏ một người.

Thử sáu mẫu 4-3-3, 4-4-2, 4-2-3-1, 4-1-4-1, 5-3-2, 3-5-2, cả hai
hướng x. Ghép một-một hình học bằng Hungarian hình chữ nhật, thử chiều
dài/rộng/dịch chuyển, rồi tinh chỉnh tỉ lệ và tâm theo các ô đã ghép.
Giữ kích thước khối giả định dài 24–75 m/rộng 28–64 m khi tinh chỉnh,
không cho ô mẫu vượt sân. Đây là tìm kiếm hữu hạn/cục bộ, không bảo đảm
nghiệm tối ưu toàn cục hoặc đại diện mọi pha chuyển trạng thái.

Lấy 3 thời điểm trải đều trong phần đủ người và thêm thời điểm minh họa
nếu khác (tối đa 4). Xếp mẫu bằng trung vị sai lệch RMSE mét qua các
thời điểm; tỷ lệ đứng đầu đo nhất quán của thứ hạng, KHÔNG là xác suất
đúng. Chỉ gắn tentative_partial_shape nếu RMSE <=6 m, hơn mẫu thứ hai
>=0,75 m, đứng đầu >=2/3 và có >=3 thời điểm khớp. Còn lại ambiguous
hoặc poor_template_fit; luôn giữ tối đa ba khả năng để đối chiếu. Các
ngưỡng là chính sách thử nghiệm, chưa hiệu chỉnh bằng nhãn HLV độc lập.

UI tách chấm màu/ID thật và vòng nét đứt ? ở các ô mẫu chưa thấy. Các
ô giả định không bao gồm một thủ môn bịa thêm, không đưa vào heatmap,
quãng đường hoặc số người. Mỗi giả thuyết gắn đúng vị trí thật/thời gian
của ảnh tham chiếu, không nối nhầm với ảnh đại diện của cửa sổ khác.

## Gợi ý chiến thuật có điều kiện

Các quy tắc chọn chủ đề rà soát: tập trung >=60% lượt vị trí vào một
dải y hoặc bề ngang <32 m; khoảng x liền kề >=16 m ở >=30% thời điểm;
bề ngang >45 m hoặc chiều dọc >40 m. Không chạm ngưỡng thì khuyến nghị
quan sát thêm, không kết luận hệ thống tối ưu. Đây là ngưỡng kỹ thuật,
không phải chuẩn FIFA hay kết quả huấn luyện ML.

Mỗi thẻ có số đo làm căn cứ, điều kiện HLV xác nhận có/không bóng,
hành động và rủi ro. Gợi ý tạo chiều rộng/điểm hỗ trợ chỉ áp dụng khi
có bóng và thực sự có người nhận/khoảng trống; co khối chỉ áp dụng khi
phòng ngự ổn định. Không suy ra khoảng trống ngoài camera. Bố trí
4-3-3/4-2-3-1/4-4-2 đi kèm là minh họa bài tập, không phải nhận diện
hoặc khuyến nghị đổi sơ đồ đã được chứng minh hiệu quả.

Tham khảo nguyên tắc chuyên môn (không lấy các ngưỡng kỹ thuật ở trên):

- [FIFA: Switch of play](https://www.fifatrainingcentre.com/en/game/game-analysis/in-possession/switch-of-play.php): chiều rộng, người nhận và hỗ trợ khi đổi hướng triển khai.
- [FIFA: Team organisation out of possession](https://www.fifatrainingcentre.com/en/game/game-analysis/out-of-possession/team-organisation--out-of-possession-.php): khối đội và các tuyến di chuyển cùng nhau khi không bóng.

## Kiểm tra và kết quả clip mẫu

Cập nhật sau bước mở rộng: bản hiện hành đã có tọa độ ở sáu khoảng
trong clip, tổng42,2s hiệu chỉnh/39,93s có vị trí người. Đoạn0–10s đã
có thêm kết quả chiến thuật A/B; một số đoạn ngắn vẫn thiếu dữ liệu
theo điều kiện5s. Xem VIDEO_CALIBRATION_EXPANSION.md. Các số30–50s bên
dưới là bản tham chiếu ban đầu, không phải toàn bộ phạm vi hiện hành.

Lệnh từ gốc repo: `.\.venv\Scripts\python.exe -m pytest tests/test_video_tactics.py -v --basetemp .tmp/pytest_tactics`.
Kiểm ghép tối ưu bằng vét cạn bài nhỏ, thiếu người, hướng đảo, ảnh tham
chiếu, không tạo quan sát giả, đúng tổng heatmap/cự ly theo thời điểm,
không nối đoạn/nhóm, dữ liệu thiếu/sai, hash nguồn và đầu vào thay đổi.

Video Project 15.mp4, job c140f8aefb4e4678b51fe6f633e1fc56, chỉ có
tọa độ ở khoảng 30–50 giây; vẫn là hiệu chỉnh tay chưa đo sai số độc lập.
Nhóm A có trung vị 8 người, nhóm B 10 người. 30–40s: A ngang39,4 m/
dọc28,1 m/hỗ trợ gần7,9 m; B ngang34,4/dọc26,5/hỗ trợ8,4 m. Nhóm A
có75,6% lượt vị trí trong dải y thấp, gợi ý kiểm tra chiều rộng có điều
kiện. Không kết luận đây là lệch cánh của toàn đội.

Nhóm B 30–40s: 5-3-2 và 4-4-2 khớp gần nhau (RMSE trung vị5,42 và
5,46 m), giữ mơ hồ. Ba cửa sổ/nhóm còn lại chưa đạt mức khớp thử nghiệm.
Chưa có sơ đồ nào được xác nhận; không nới ngưỡng để làm clip mẫu trông
thuyết phục hơn. Cần nhãn sơ đồ/pha chơi và sai số tọa độ độc lập để
đánh giá chuyên môn, đặc biệt khi đội dồn biên/chuyển trạng thái.

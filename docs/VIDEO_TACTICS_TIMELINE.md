# So sánh không gian theo thời gian — 31/10/2026

## Phạm vi

API tactics thêm DTO nội bộ timeline, UI hiển thị các đoạn theo thứ tự,
trạng thái đủ/thiếu dữ liệu, khoảng chưa có hiệu chỉnh và bảng so sánh.
Không đổi TrackingRow/DATA_CONTRACT, không thêm thư viện hoặc chạy lại
detector. Tái sử dụng các vị trí đã kiểm nguồn và lọc vai trò nội bộ.

Chỉ so hai cửa sổ kế nhau của cùng nhóm, cả hai đủ dữ liệu, khoảng
cách không quá0,2s. Không bỏ qua một đoạn thiếu rồi nối hai đoạn xa
nhau. Mỗi ID phải có mặt ở >=70% thời điểm đủ người trong từng cửa sổ;
lấy giao hai tập. Cần >=4 ID chung. Tiếp tục chỉ giữ thời điểm toàn bộ
nhóm ID này cùng có mặt, >=5s và >=50% mỗi cửa sổ. Không đổi ID hoặc
ghép nhiều thời điểm thành đủ11 người, không chọn bỏ bớt ID để làm đẹp
chỉ số khi thiếu hỗ trợ. Nếu chưa đạt thì không có delta/nhận xét số.

Đếm/tính cự ly trên từng thời điểm với cùng cụm ID, sau đó lấy trung vị
riêng từng đoạn: bề ngang, chiều dọc, khoảng người gần nhất trong cụm,
tâm cụm theo x. Delta là sau trừ trước. Không coi đó là quãng đường hay
tốc độ từng cầu thủ. Các cầu thủ ngoài cụm vẫn có thể đang hỗ trợ; cụm
ID chung không đại diện toàn đội và ID vẫn có thể bị đổi nhầm.

Chỉ diễn giải tâm cụm về hướng tấn công/sân nhà nếu hai cửa sổ cùng
hướng suy luận đã rà; khi không biết hoặc hướng đổi thì forward_m=null.
Với hướng x giảm, bằng chứng forward dùng105-x để delta vẫn đúng theo
hướng. Tọa độ heatmap và tâm x gốc không bị lật. Không suy ra đổi sơ đồ,
kiểm soát bóng hoặc nguyên nhân dịch chuyển từ chính delta này.

## Nhận xét và kiểm tra cho HLV

Các ngưỡng mô tả cố định: thay đổi ngang/dọc >=3m, người gần nhất
>=2m, tâm cụm theo hướng >=5m. Đây là chính sách thử nghiệm, không là
kiểm định thống kê/chuẩn FIFA hoặc mô hình tối ưu chiến thuật. Tất cả
delta vẫn hiện trong bảng; không chạm ngưỡng không chứng minh chiến
thuật ổn định/tối ưu. Mỗi nhận xét kèm số trước/sau và điều kiện HLV
đối chiếu pha có/không bóng, điểm hỗ trợ/bọc lót trên video.

UI cho chọn cửa sổ, so hai đoạn trên cùng cụm, xem lý do các cặp còn
lại bị loại, và tua trước/sau đến thời điểm thật mà toàn cụm cùng hiện.
Không vẽ đường xu hướng liền mạch qua khoảng mất dữ liệu. Số của cụm
so sánh được tách rõ với số toàn nhóm áo của từng đoạn phía dưới.

## Clip mẫu

Video Project15.mp4/job c140f8aefb4e4678b51fe6f633e1fc56: chỉ cặp
30–40 →40–50s đủ điều kiện cho từng nhóm. Các cặp khác có ít nhất một
đoạn thiếu hỗ trợ và không sinh delta.

- Nhóm A: cùng4 ID212/220/225/254, hiện đồng thời5,9s và6,933s.
  Bề ngang cụm giảm4,91m, người gần nhất trong cụm giảm3,54m; tâm x
  giảm10,57m (về sân nhà theo hướng suy luận A). Không kết luận cả đội
  lùi khối hoặc đây là chiến thuật có chủ đích.
- Nhóm B: cùng8 ID1/2/32/41/112/143/237/251, hiện đồng thời8,333s và
  5,533s. Bề ngang giảm1,63m, người gần nhất tăng0,78m; tâm x giảm
  10,27m (về hướng tấn công suy luận B). Camera, sai số hiệu chỉnh và
  thay đổi trạng thái bóng có thể ảnh hưởng; không gọi là đội đổi lối chơi.

## Kiểm tra

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_video_timeline.py tests/test_video_tactics.py tests/test_video_context.py -v --basetemp .tmp/pytest_video_timeline
```

9 test mới kiểm số của cùng cụm trước/sau, bỏ ảnh hưởng người ngoài
cụm, ID mới không ghép dù ở vị trí tương tự, hỗ trợ từng ID không thay
thế hiện đồng thời, không nối qua đoạn thiếu/khoảng trống, hướng chưa
biết/đổi/x giảm, không suy chiến thuật tối ưu khi delta0, tích hợp với
report từ TrackingRow đã kiểm tra. Các kiểm thử tổng hợp chỉ nghiệm
thu tính toán/điều kiện, không là đánh giá chuyên môn độc lập.

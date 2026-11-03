# Kiểm chứng phân vai trò và mốc demo có căn cứ

Ngày03/11/2026: chưa đạt yêu cầu hoàn thiện toàn bộ luồng tự động trên
video bất kỳ. Đã kiểm tra định lượng phân vai trò trên toàn ảnh và
đường API trả heatmap/báo cáo của một job sẵn có, để xác định giới hạn
trước khi sửa hiệu chỉnh sân.

## Phân vai trò trên3ảnh nguyên khung

Snapshot `fixtures/full_frame_role_diagnostic_v4.json`: conf0,25,imgsz640,
ghép vị trí IoU0,5, cùng60nhãn được rà ở gói full_frame_roles_v4.

| Kết quả | V1 | V3 |
|---|---:|---:|
| Player nhận đúng /52 |45|47|
| Keeper nhận đúng /4 |0|0|
| Referee nhận đúng /4 |2|1|
| Player bị gọi referee |3|0|
| FP player theo nhãn |11|17|

Không chọn v3 chỉ vì hết nhầm player→referee: nhận đúng referee giảm
và keeper chưa nhận đúng. gFCS/k13 đã cung cấp crop train v3 nên đây
là chẩn đoán phát triển, không phải test độc lập.3ảnh chưa đủ dữ liệu
để kết luận chất lượng phân vai trò. Chưa train v4 hoặc đổi runtime.
Gói toàn cảnh thật hiện vẫn là pilot3ảnh; công việc bổ sung nguồn đa
dạng có cầu thủ vàng nhỏ chưa hoàn tất.

## Mốc demo hiện có

Job `fc0cd4212aaa436a8614dacd4b74241f`, nguồn SHA256
`f51735a042b493eba3cced891209fe1b6beb20ca80e20c340c7ede51900495d0`:
52,37giây video,25,27giây có hiệu chỉnh ước lượng;13.978dòng vị trí,
4cửa sổ observed_cluster,5gợi ý. Có12cửa sổ thiếu hỗ trợ; không yêu
cầu heatmap cho các cửa sổ này, nhưng không cho phép phát gợi ý thiếu
căn cứ. Script kiểm tọa độ hữu hạn/trong sân, heatmap không âm/hữu hạn
ở cửa sổ đủ hỗ trợ, cùng hash nguồn giữa báo cáo sân và chiến thuật,
và từng giá trị evidence bằng chỉ số của cửa sổ tương ứng.

```powershell
.\.venv\Scripts\python.exe -m backend.cv.verify_demo_flow
```

Snapshot `fixtures/demo_flow_readback_v1.json`: api_consistency_passed=true.
Đây là đọc lại job bằng FastAPI TestClient, chưa chạy lại upload mới
hoặc nghiệm thu browser. Không gọi hiệu chỉnh này là chính xác độc lập,
không coi hình thái nhìn thấy là sơ đồ đủ11người hoặc khuyến nghị HLV
đã được chuyên gia xác nhận.

Khi hai server đang chạy, mở
`http://127.0.0.1:5173/video?job=fc0cd4212aaa436a8614dacd4b74241f`.
Demo phải nêu rõ khoảng thời gian có tọa độ, heatmap là phần được quan
sát và quãng đường chỉ tính trên chuỗi hợp lệ. Không dùng đoạn không
hiệu chỉnh để suy mét hoặc bù cầu thủ khuất hình.

## Việc còn phải làm theo thứ tự

1. Tuyển thêm toàn cảnh thật có cầu thủ vàng nhỏ; rà toàn bộ target,
   loại media chưa xác minh khỏi dataset mới và kiểm soát lặp ROI/full.
2. Khóa protocol ghép/sampling rồi train v4 từ checkpoint sạch; giữ
   bộ kiểm cũ, bổ sung tập kiểm độc lập khi có nguồn đủ rõ.
3. Rà mốc sân theo thời gian trên clip demo và clip khó, đo sai số ở
   mốc không dùng để fit; cải thiện coverage khi camera lia bằng bằng
   chứng hình học, không nới gate để có heatmap.
4. Chạy lại upload mới và kiểm tra browser đến báo cáo; đối chiếu
   heatmap/quãng đường và evidence. Khi đó mới chốt nghiệm thu luồng.

Lần này chưa sửa thuật toán hiệu chỉnh sân hoặc frontend; bộ đọc kiểm
API tạo cơ sở để kiểm tra hồi quy cho các thay đổi tiếp theo.

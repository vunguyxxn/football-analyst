# Rà nhãn nghi vấn và coverage train theo parent v14

Ngày 05/11/2026. Chỉ kiểm kê/review ngoại tuyến, không train hoặc inference mới. Dataset/GT, repeats, scoring, weights và model ứng dụng giữ nguyên. Không chạy known test/match128057; không chuyển ảnh val/test sang train. Nhãn **chưa được người kiểm độc lập nghiệm thu**. Agent kiểm lại không phải nghiệm thu độc lập.

## Bằng chứng và phạm vi

Kiểm lại frozen training plan qua `load_plan`: hash protocol, manifest, sampling ledger, nguồn, snapshot ảnh/nhãn và weights tham chiếu khớp. Không tính lại metric hoặc chọn lại ngưỡng/checkpoint. Audit val1280 trước đã replay đủ ba lớp; phiên này dùng lại bằng chứng và kết quả đó.

Plan review được ghi trước khi mở bộ ảnh review: [plan](fixtures/role_coverage_review_plan_v14.json). Chọn tất cả13 parent bổ sung v11–v13; hash-rank thêm4 red_stadiums,2 euro_red_white và1 mỗi nhóm SoccerTrack train. Trên các parent này chọn tối đa4 cụm player/parent theo hash, không theo score mô hình. Rà tất cả206 keeper unit-box,34 referee tối kế thừa và19 referee mới/chưa gắn metadata cũ:327 object crop tổng cộng, gồm68 player. Xem toàn cảnh18 referee tối biên xa; kiểm coverage trên21 parent/27 unit, không phải toàn bộ260 parent. Các tập crop và parent có phạm vi khác nhau.

[Packet](fixtures/role_coverage_review_v14.json) giữ từng hash ảnh/nhãn, label index **zero-based**, geometry, màu/tư thế/vị trí, đường dẫn ảnh chứng minh và trạng thái pending. [Summary](fixtures/role_coverage_review_summary_v14.json) khóa hash inventory/plan/packet. 523 màu referee khác kế thừa v10 khi pixel/role/index/geometry khớp, chưa rà lại trong phiên này; không diễn giải vị trí chưa rà thành không có dữ liệu.

Artifact cục bộ: `data/processed/role_coverage_review_v14/`: inventory.json, train-objects.csv (mọi nhãn, box loaded/parent, repeats và kích thước), label-proposals.csv,327 crop,21 ảnh parent và18 context referee tối biên xa. Ảnh/crop không commit. Chỉ số `xyxy` ở case keeper là prediction audit để tìm crop; `old_xyxy` là box GT, không trộn hai trường này.

## Năm case nhãn

Mọi dòng dưới đây là **đề xuất agent**, applied=false, benchmark_excluded=false, independent=pending. Chưa sửa GT, cách ly hoặc loại case khỏi scoring.

| Case | Ảnh nguồn val (tên đầy đủ trong packet/CSV) | GT index | Cũ → đề xuất | Lý do |
|---|---|---:|---|---|
| keeper-14 | [4b770a_1_7_png.rf.0344c0dc64e2361671483c067c0bc549.png](../data/processed/role_sources_training_v14/dataset/images/val/4b770a_1_7_png.rf.0344c0dc64e2361671483c067c0bc549.png) | 7 | player → chưa đủ bằng chứng | Người xám bị cắt sát mép phải; kit/vị trí chỉ gợi ý, thiếu hình thể và vai trò. |
| keeper-20 | [4b770a_5_6_png.rf.cc113a3e1f4bff7e16f34545b080d956.png](../data/processed/role_sources_training_v14/dataset/images/val/4b770a_5_6_png.rf.cc113a3e1f4bff7e16f34545b080d956.png) | 6 | player → goalkeeper | Kit xám, bàn tay giống găng và vị trí khu phạt đền khác kit đỏ/vàng. Chỉ đề xuất đổi token lớp, giữ geometry GT. |
| keeper-57 | [538438_7_5_png.rf.cfd814ca02baed6da1b069c08cf9442a.png](../data/processed/role_sources_training_v14/dataset/images/val/538438_7_5_png.rf.cfd814ca02baed6da1b069c08cf9442a.png) | 0 | player → chưa đủ bằng chứng | Cắt mép phải nặng; không đủ bằng chứng đổi vai trò. |
| keeper-66 | [798b45_3_2_png.rf.d951824d7c962e8b26104e0d381119b5.png](../data/processed/role_sources_training_v14/dataset/images/val/798b45_3_2_png.rf.d951824d7c962e8b26104e0d381119b5.png) | không có | không GT → thêm player (nháp) | Người áo đỏ giống cầu thủ sân, không GT chồng. Box tay nháp [812,216,837,270], cần người độc lập chỉnh/duyệt. |
| referee-120 | [538438_3_10_png.rf.1130754d94a304df8848ec4803bc7f8b.png](../data/processed/role_sources_training_v14/dataset/images/val/538438_3_10_png.rf.1130754d94a304df8848ec4803bc7f8b.png) | 6 | referee → giữ tạm | Chi tiết kit đen/patch trắng, quần ngắn/tất dài thiên về official hơn staff áo khoác bên cạnh. Không thấy cờ hoặc xác minh danh tính độc lập. |

Hai case cắt mép giữ nguyên nhãn hiện hành trong benchmark, không coi là đã xác nhận player. Case referee-120 có bằng chứng thị giác mới nghiêng về official nhưng chưa xác nhận vai trò. Box thêm player là bản nháp thủ công, không lấy prediction làm GT. Packet/CSV ghi nguyên dòng YOLO cũ/đề xuất, nguồn tuyệt đối, SHA, box GT và ảnh kiểm chứng native phóng nearest-neighbor; ảnh gốc và context audit cũ vẫn cần khi người độc lập duyệt. Không có đề xuất cách ly được thực thi.

## Kiểm kê toàn train

| Lớp | Nhãn trên324 unit | Cụm không gian theo parent | Nhãn theo418 lượt |
|---|---:|---:|---:|
| player | 4556 | 4556 | 5006 |
| goalkeeper | 206 | 206 | 242 |
| referee | 576 | 566 | 652 |

260 ảnh/khung nguồn,324 đơn vị pixel–nhãn,418 lượt lấy mẫu;9 unit âm/15 lượt âm. Cụm cùng role/parent ở IoU>=0,7 là proxy chống đếm ROI lặp, không phải số người duy nhất. 10 nhãn referee chồng giữa ROI gộp thành cụm; không tự coi là lỗi nhãn. Kiểm tất cả unit không tìm thấy cặp box cùng unit IoU>0,9 ở bất kỳ lớp nào; điều này không chứng minh coverage/geometry hoàn hảo. Parent có nhiều frame cùng trận hoặc cùng family vẫn có tương quan. Family là metadata bối cảnh với độ hạt khác nhau, không phải21 trận độc lập.

| Family | Parent | Unit | Lượt | Nhãn unit P/G/R | Nhãn lượt P/G/R |
|---|---:|---:|---:|---|---|
| broadcast_BAR_MLL | 1 | 1 | 1 | 15/1/2 | 15/1/2 |
| broadcast_BAY_BVB_allianz | 2 | 2 | 2 | 30/1/3 | 30/1/3 |
| broadcast_CEL_VIL | 1 | 1 | 1 | 16/1/2 | 16/1/2 |
| broadcast_ESP_BAR_home | 1 | 1 | 1 | 18/1/2 | 18/1/2 |
| broadcast_FCU_VFB_home | 1 | 1 | 1 | 0/0/0 | 0/0/0 |
| broadcast_Kobe_Hiroshima | 1 | 1 | 1 | 14/1/2 | 14/1/2 |
| broadcast_Okayama_Machida | 1 | 1 | 1 | 0/0/0 | 0/0/0 |
| broadcast_RBL_FCH | 1 | 1 | 1 | 15/1/1 | 15/1/1 |
| broadcast_WOB_RBL_home | 2 | 2 | 2 | 23/2/3 | 23/2/3 |
| esp_bel_women | 1 | 1 | 4 | 15/0/1 | 60/0/4 |
| euro2016_GER_FRA_broadcast | 1 | 1 | 4 | 18/1/1 | 72/4/4 |
| euro_red_white | 21 | 72 | 78 | 151/6/44 | 151/6/44 |
| german_FCS_EBS_blue_yellow_ground | 1 | 1 | 4 | 14/1/1 | 56/4/4 |
| las_palmas_leganes | 2 | 2 | 8 | 20/2/1 | 80/8/4 |
| libertadores_red_stadium_white_black_stripes | 1 | 1 | 1 | 19/1/2 | 19/1/2 |
| libertadores_white_blue_neongreen | 1 | 2 | 2 | 11/1/1 | 11/1/1 |
| libertadores_yellow_navy | 1 | 1 | 4 | 14/0/2 | 56/0/8 |
| rai_replay_blue_white_broadcast | 1 | 1 | 4 | 20/2/2 | 80/8/8 |
| red_stadiums | 210 | 222 | 262 | 4097/178/502 | 4106/178/542 |
| soccertrack-match-117093 | 4 | 4 | 16 | 26/1/2 | 104/4/8 |
| soccertrack-match-118575 | 5 | 5 | 20 | 20/5/2 | 80/20/8 |

`red_stadiums` chiếm210/260 parent,4097/4556 player,178/206 keeper và502/576 referee unit-box; dữ liệu có nhưng tập trung bối cảnh. Tổng lượt theo parent có219 parent1lượt,1 parent2,5 parent3,22 parent4,1 parent5,7 parent6,4 parent7,1 parent19; nhiều lượt/ROI không tăng parent độc lập.

Kích thước là chiều cao box sau letterbox, `h × imgsz / max(width,height)`. Loaded dùng kích thước ROI thực tế đưa vào pipeline; source dùng toàn ảnh/khung gốc. Không tính augmentation/mosaic ngẫu nhiên; không hiểu phóng crop thành khả năng phát hiện toàn cảnh. Bins: <24 / [24,48) / >=48 px; bảng đếm nhãn unit, chưa nhân repeats.

| Role | Loaded640 | Source640 | Loaded1280 | Source1280 |
|---|---|---|---|---|
| player | 3844/657/55 | 3869/672/15 | 335/3509/712 | 341/3528/687 |
| goalkeeper | 194/11/1 | 195/11/0 | 8/186/12 | 8/187/11 |
| referee | 421/104/51 | 453/121/2 | 126/295/155 | 129/324/123 |

22 player unit-box/14 parent và32 referee unit-box/23 parent có source640<24 nhưng loaded640>=48: phóng crop làm thay đổi phân bố kích thước nhìn thấy. Keeper không có trường hợp qua hai mốc này. Chi tiết kích thước từng box và số lượt nằm trong CSV/summary.

## Hai nhóm cần ưu tiên

Keeper: rà206 crop cho24 thấp/cúi,160 tư thế đứng,22 mơ hồ/cắt. “Đứng” gồm di chuyển/tư thế sẵn sàng, không chứng minh đứng yên.150 nhãn đứng nhỏ source640<24 thuộc143 parent,159 lượt;138 nhãn thuộc red_stadiums. Trong nhóm này xanh/cyan11 nhãn/11 parent/11 lượt,10 red_stadiums và1 libertadores; light-neutral10 cùng red_stadiums; dark1,red-orange1,red-orange-pink43,yellow-green-gold84. Vì vậy không thể nói train thiếu hoàn toàn keeper nhỏ đứng, nhưng coverage keeper xanh/sáng đa bối cảnh còn mỏng. Màu là phân nhóm thị giác thô, không nhận dạng chính xác màu áo từ pixel nhỏ.

Referee tối:45 unit-box/26 parent/68 lượt;18 biên xa,21 giữa sân,6 biên gần.18 biên xa thuộc18 parent/18 lượt nhưng12 cùng family red_stadiums;11/12 còn chung prefix121364. Full context cho thấy nhóm cũ rất giống bối cảnh/kit, không được coi là12 trận độc lập.6 nhãn mới thuộc4 family CEL–VIL(1),BAY–BVB(2),WOB–RBL(2),Kobe–Hiroshima(1); hai frame cùng nhóm trận vẫn tương quan.16/18 dưới24px tại640; tại1280 có11<24,5[24,48),2>=48. Train có dark-far nhưng độ đa dạng và cỡ nhìn thấy hạn chế, không phải thiếu toàn bộ nhóm.

Player:68 cụm được chọn trên18 parent có player,80 lượt;25 source640<24,41[24,48),2>=48. Có30 trắng,10 đỏ,8 vàng,5 navy,4 xanh lá và các kit khác (chi tiết fixture). Màu/trang phục/đứng gần gôn có giao với keeper, nhưng đây là GT player chọn theo hash, không phải68 lỗi mô hình hoặc kiểm toàn bộ4556 nhãn. Cần phân biệt dựa ngữ cảnh/đội/kit/găng/động tác, không suy keeper từ màu hay vị trí đơn lẻ.

Coverage: chỉ21 parent/27 unit được kiểm toàn cảnh/ROI union;239 parent chưa rà coverage trong phiên. Không thấy lỗi mới chắc chắn ở mức ảnh đã xem, không xác nhận nhãn đầy đủ toàn train. Hai parent âm FCU–VFB/Okayama–Machida chỉ nạp ROI rỗng; người ngoài ROI trên ảnh gốc không phải thiếu nhãn. Ảnh29 v12 có cả ROI sân và ROI âm cùng parent; chúng không độc lập. Parent euro_red_white chọn ở đây chỉ nạp3 hoặc4 crop nhỏ, không nạp phần còn lại toàn frame. Staff/khán giả/ball crew không trở thành referee chỉ vì áo tối; kiểm cờ, kit, vị trí/hoạt động và quan hệ khu kỹ thuật. Nếu không đủ rõ phải giữ cờ chưa chắc, không xóa nhãn im lặng.

## Đối chiếu lỗi val và thứ tự xử lý

Audit val1280 ghi76/110 keeper FP trên cầu thủ sân;89 mới/21 còn/28 hết là ghép box không gian, không phải người độc lập. Các kit đỏ/vàng/trắng trong mẫu train cho thấy giao diện màu với keeper tồn tại, chưa đo tần suất nhầm của cả train. Referee mất67/nhận thêm39;50 mất ở biên xa,48 có score đúng<0,25. Train dark-far chủ yếu nhỏ và ít nhóm bối cảnh, phù hợp một hướng cần kiểm thêm, **không xác minh nguyên nhân nhân quả**. Một seed, sampling/ROI và GT chưa độc lập là các giới hạn còn lại.

Player TP2459→2392,FP437→365;keeper TP50→68,FP49→110;referee TP143→115,FP230→186. Không ưu tiên giảm FP đơn độc hoặc đề xuất đẩy mọi kit dễ nhầm thành keeper: có thể mất player TP/keeper precision hoặc referee recall. Chưa thử thay data/sampling/ngưỡng/cấu hình.

| Ưu tiên | Khoảng trống bằng chứng | Hành động đề xuất cho phiên sau |
|---|---|---|
| P0 |5 case GT chỉ được agent kiểm lại | Người độc lập duyệt packet với native/context, chấp nhận/bác từng role và geometry; lưu reviewer/quyết định trước mọi bản GT mới. |
| P1 |Dark-far18 parent nhưng tập trung bối cảnh; upright-small keeper xanh/sáng ít nhóm | Sau P0, khóa một plan kiểm coverage theo parent/trận trên dữ liệu đang có, đối chiếu player cùng kit và actor official/staff; chưa tăng repeats hoặc thêm nguồn. |
| P2 |239 parent chưa kiểm coverage; crop phóng làm lệch cỡ loaded/source | Rà có thiết kế và ghi phạm vi, ưu tiên scene đầy đủ/ROI union; chỉ quyết định sửa dữ liệu trong bản phát hành riêng sau nghiệm thu. |

**Bước tiếp theo cụ thể:** giao5 case cho người kiểm độc lập cùng ảnh gốc/context và cột GT/proposal; giữ dataset và scoring hiện tại cho đến khi có biên bản quyết định. Không cần train thêm để thực hiện bước này.

## Tái tạo và kiểm thử

`python -m backend.cv.review_role_coverage_v14 summarize` xác minh lại hashes, đầy đủ sample và evidence, parent/ROI union, nhãn cũ val, rồi xuất CSV/summary bằng dữ liệu đã lưu; không gọi detector. Chạy lại cho summary byte/hash giống nhau. `inventory` chỉ dùng khi tạo bộ cục bộ mới và từ chối ghi đè output/plan hiện hữu: dùng snapshot v14, metadata nguồn v11–v13, inventory/review v10 đã khóa hash. Hàm `export_evidence` tái dựng327 crop và21 parent từ inventory/plan có sẵn;18 context là source_frame với target parent_xyxy,5 crop native tham chiếu xyxy trong packet trên ảnh val gốc. Nhận xét thị giác là fixture thủ công cần người kiểm, không được script tự nghiệm thu. Exact manual evidence hiện có được pin SHA và replay kiểm file, không có fallback tải hoặc tái inference.

Kiểm thử:12 test mới cho sampling quyết định trước review, kích thước crop/source, repeats không thành parent, completeness/hash/geometry binding, parent ROI và chặn tuyên bố nghiệm thu/áp dụng nhãn. Kết quả toàn suite được ghi tại PROGRESS.

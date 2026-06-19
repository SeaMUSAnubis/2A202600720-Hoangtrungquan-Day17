# Memory Systems cho AI Agents - Tổng Hợp Checklist & Lời Giải Của Học Viên

Dưới đây là toàn bộ các nội dung em đã nắm vững, kèm theo **chính những câu trả lời xuất sắc của em** trong suốt quá trình học.

---

## PHẦN 1: KIẾN THỨC NỀN TẢNG (Bản Cũ)

### 1. Hiểu Vấn Đề (The Problem)
- [x] Tại sao không thể nhồi nhét toàn bộ lịch sử trò chuyện cũ vào Prompt của LLM? 
  > **Câu trả lời:** "Việc bê nguyên thế gây tốn rất nhiều token, nhiều khi còn khiến LLMs không nhớ rõ bản yêu cầu của người dùng. Nên thay vì log hết, mình chỉ cần tóm tắt lại rồi cần cái gì thì lôi cái đó ra đọc."
- [x] Baseline Agent (trí nhớ ngắn hạn) và Advanced Agent (trí nhớ dài hạn) khác nhau ở điểm cốt lõi nào?
  > **Câu trả lời:** "Baseline là trí nhớ ngắn hạn nên trong cuộc hội thoại ngắn nó sẽ chỉ cần nhớ những ngữ cảnh tại phiên trò chuyện. Trong khi Advanced lại loại bỏ toàn bộ ngữ cảnh lưu dư thừa để ưu tiên load thông tin quan trọng về người dùng."

### 2. Giải Pháp và Thiết Kế (The Solution & Design Decisions)
- [x] **Persistent Memory (`User.md`)**: Tại sao lại lưu thông tin cá nhân ra một file riêng?
  > **Câu trả lời:** "User.md là nơi chứa thông tin người dùng như tên tuổi, sở thích nghề nghiệp, tính cách... để từ đó đưa ra những câu trả lời hoặc giải pháp mà thiên về tính cách của họ."
- [x] **Compact Memory**: Tại sao phải nén lịch sử chat thành một bản Tóm tắt (Summary)?
  > **Câu trả lời:** "Nó sẽ nén những thông tin của từng phiên trò chuyện, lấy ra những thông tin cần thiết cho phiên trò chuyện tiếp để từ đó có thể tạo trải nghiệm tốt hơn cho người dùng."

### 3. Bức Tranh Tổng Thể (Broader Context)
- [x] Phân biệt rõ sự khác nhau giữa Agent tokens only và Prompt tokens processed.
  > **Câu trả lời:** "Agent tokens only là token agent sinh ra trong quá trình agent dùng (tạo ra văn bản, gọi tool). Còn prompt tokens là prompt của người dùng tốn ít chi phí, nó chỉ là ngữ cảnh cho mô hình."

---

## PHẦN 2: CÁC TÍNH NĂNG MỞ RỘNG (Bản Mới - Bonus)

### 1. Hiểu Vấn Đề (The Problem)
- [x] Vấn đề gì sẽ xảy ra nếu ta chỉ lưu thông tin dưới dạng chuỗi văn bản (raw string) mà không có cấu trúc?
  > **Câu trả lời:** "Hệ thống sẽ ghi nhầm 'Nhật Bản' thành nơi ở của em, từ đó đưa ra những gợi ý sai lệch hoàn toàn trong tương lai, và ta không có cách nào biết thông tin này đáng tin hay không."
- [x] Khi nào AI có thể lưu sai sự thật vào `User.md`? Làm sao biết thông tin đáng tin cậy để lưu?
  > **Câu trả lời:** "Confidence đóng vai trò kiểm tra thử thông tin đó có chính xác không, từ đó không lưu lung tung." (Ví dụ: "Tôi làm nội trợ" thiếu keyword nên chỉ đạt 0.5).
- [x] Chuyện gì xảy ra nếu người dùng đính chính thông tin nhưng hệ thống chỉ biết "ghi đè" mù quáng?
  > **Câu trả lời:** "File User.md sẽ đồng thời chứa cả thông tin cũ (VD: Đà Nẵng) và mới (Không ở Đà Nẵng), khiến LLM bị mâu thuẫn khi đọc hồ sơ."

### 2. Giải Pháp và Thiết Kế (The Solution & Design Decisions)
- [x] Cấu trúc JSON `{'value': ..., 'confidence': ..., 'operation': ...}` giải quyết vấn đề trích xuất như thế nào?
  > **Lời giải:** Tách bạch rõ Ràng Giá trị (value), Độ tự tin (confidence) và Hành động (upsert/delete) để hệ thống Python có thể ra quyết định chính xác trước khi ghi file.
- [x] Cơ chế xác định `operation = 'delete'` vs `'upsert'` hoạt động ra sao?
  > **Lời giải:** Bắt các từ khóa mang tính phủ định (VD: "Tôi không phải tên là...") để kích hoạt lệnh xóa (delete) sự thật cũ thay vì ghi đè mù quáng.

### 3. Bức Tranh Tổng Thể (Broader Context)
- [x] Nếu mở rộng hệ thống lên quy mô hàng triệu người dùng, rủi ro lớn nhất về mặt thiết kế file .md là gì?
  > **Câu trả lời của em:** "Hệ thống sẽ bị quá tải (bottleneck/latency) vì phải liên tục đọc/ghi đồng thời vào hàng triệu file .md nằm trên ổ cứng, do đó ta cần dùng các cơ sở dữ liệu chuyên dụng (như PostgreSQL, MongoDB hoặc Vector Database)."

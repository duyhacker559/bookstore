# Cải thiện AI Chat (Mục 1) bằng Hành vi Người Dùng (User Behavior)

## Goal
Nâng cấp tính năng tìm kiếm sản phẩm trong Chat AI (ví dụ: gõ "Laptop" ra Laptop) để có thể **cá nhân hóa dựa trên hành vi của người dùng (User Behavior)**. 
Thay vì chỉ đơn thuần tìm các sản phẩm có chữ "Laptop" giống nhau cho tất cả mọi người, hệ thống sẽ ưu tiên hiển thị những chiếc Laptop mà người dùng đã từng xem/mua, hoặc những chiếc Laptop tương đồng với sở thích mua sắm trước đây của họ trong Graph Database.

## Phân tích hiện trạng
Hiện tại `rag_pipeline.py` sử dụng:
1. `vector_hits`: Tìm kiếm theo độ tương đồng văn bản (FAISS) cho từ khóa "Laptop".
2. `graph_hits`: Tìm kiếm lịch sử hành vi của người dùng (từ `Neo4jService.query_recommendation`). **Tuy nhiên**, hàm này đang bỏ qua hoàn toàn từ khóa "Laptop" mà chỉ lấy các sản phẩm người dùng hay tương tác.
3. Khi kết hợp (`combine_hybrid_score`), các sản phẩm từ lịch sử (ví dụ: Sách) sẽ bị lẫn vào danh sách tìm kiếm "Laptop" của người dùng. Hoặc ngược lại, các Laptop tìm được bằng Vector không được cộng điểm ưu tiên một cách chính xác dựa trên lịch sử tương tác.

## Proposed Changes

### 1. Cập nhật `ai-service/neo4j_service.py`
Thêm hàm mới `query_personalized_message(self, user_id: int, message: str, top_k: int = 5)` vào `Neo4jService` để kết hợp **cả text search và user behavior** trực tiếp trên đồ thị.

- **Cypher Query mới**:
  ```cypher
  WITH toLower($message) AS message
  MATCH (p:Product)
  WITH p, reduce(score = 0.0, token IN split(message, ' ') | score + CASE WHEN token <> '' AND toLower(p.title) CONTAINS token THEN 1.0 ELSE 0.0 END) AS text_score
  WHERE text_score > 0
  OPTIONAL MATCH (u:User {user_id: $user_id})-[r:VIEW|BUY]->(p)
  OPTIONAL MATCH (u:User {user_id: $user_id})-[r2:VIEW|BUY]->(p2:Product)-[s:SIMILAR]->(p)
  WITH p.product_id AS product_id,
       text_score,
       sum(CASE type(r) WHEN 'BUY' THEN 1.0 WHEN 'VIEW' THEN 0.4 ELSE 0.0 END) AS direct_score,
       sum((CASE type(r2) WHEN 'BUY' THEN 1.0 WHEN 'VIEW' THEN 0.4 ELSE 0.0 END) * coalesce(s.weight, 0)) AS similar_score
  RETURN product_id, (text_score + direct_score + similar_score) AS score
  ORDER BY score DESC
  LIMIT $top_k
  ```
- **Fallback Logic**: Kết hợp `text_score` từ text matching với điểm `direct_score` và `similar_score` từ `_fallback_user_edges`.

### 2. Cập nhật `ai-service/rag_pipeline.py`
Sử dụng hàm mới khi `user_id` và `query` đều có sẵn.

- Trong hàm `retrieve(self, query: str, user_id: Optional[int] = None, top_k: int = 5)`:
  ```python
  vector_hits = self.vector_store.search(query, top_k=top_k)
  if user_id is not None and query.strip():
      # Dùng hàm mới: vừa search text, vừa ưu tiên behavior
      graph_hits = self.graph_service.query_personalized_message(user_id, query, top_k=top_k)
  elif user_id is not None:
      graph_hits = self.graph_service.query_recommendation(user_id, top_k=top_k)
  else:
      graph_hits = self.graph_service.query_from_message(query, top_k=top_k)
  ```
- Cập nhật logic filter trong `generate_response` để đảm bảo nếu người dùng tìm "Laptop", thì chỉ những sản phẩm có điểm vector hoặc text hợp lệ mới được giữ lại, loại bỏ các sản phẩm rác bị lọt vào do điểm behavior quá cao nhưng điểm RAG = 0.

## Verification Plan
1. Viết mã và cập nhật hai file `neo4j_service.py` và `rag_pipeline.py`.
2. Kiểm tra trên UI Chat AI khi gõ "Laptop", xem AI có trả về Laptops thay vì các sách cũ trong lịch sử hay không.
3. Nếu người dùng có lịch sử mua "Laptop Dell", gõ "Laptop" sẽ ưu tiên "Laptop Dell" lên trên "Laptop Asus".

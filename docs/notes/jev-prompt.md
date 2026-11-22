# Câu prompt Jev đã gỡ, lưu để dùng sau

Ngày 2026-11-22 gỡ khỏi `QUESTIONS["category"]["instructions"]` trong `backend/src/h4wk/analysis/jev.py`, ngay sau câu "Decide whether `text` itself attacks any of the `protected_targets`.":

```text
The Party, State or regime counts as attacked even when not named.
```

Câu này bắt Jev luôn coi Đảng, Nhà nước, chế độ là đối tượng bị nhắm tới kể cả khi không được nêu tên và không có trong danh sách đối tượng. Gỡ để công cụ chỉ xét các đối tượng người dùng tự khai báo trong `config/entities.toml`.

Muốn dùng lại thì nên đưa thành tuỳ chọn cấu hình thay vì viết cứng, ví dụ một trường của đối tượng kiểu "coi là bị nhắm tới kể cả khi không nêu tên".

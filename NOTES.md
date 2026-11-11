# Ghi chú phân tích · Day 04

Họ và tên: Bùi Quang Hiếu
MSSV: 2A202603639

## 1. Case được chọn

- ID case: **A5** — yêu cầu danh sách **đầy đủ** incident GitHub Actions trong năm 2025.
- Câu trả lời của agent lần 1: “Không có sự cố nào trong năm 2025”, rồi kể các incident năm 2026. Đây là kết luận vượt quá dữ liệu.
- Điểm ở lần chạy 1: **40/100** (judge); `status=completed` chỉ có nghĩa loop dừng, không chứng minh nội dung đúng.

## 2. Bằng chứng trong trace

Đoạn rút từ `eval_before.json`, case A5 (tool trả 23 kết quả khớp trong 50 incident gần nhất nhưng chỉ hiển thị 5; agent đã đọc thêm 4 incident năm 2026):

```json
{"event":"tool","step":1,"name":"get_status","arguments":{"provider":"github","component":"Actions"},"result":{"matching_incidents_in_last_50":23,"note":"Chỉ tìm theo chuỗi trong 50 incident gần nhất; không tìm thấy không chứng minh không có sự cố."}}
{"event":"model","step":6,"finish":"stop"}
```

Tool result thực tế có thêm `captured_at`, overall, components, incident IDs và URL nguồn; đoạn trên chỉ trích trường liên quan. Agent suy luận “không có” từ dữ liệu giới hạn 50 incident, thay vì nói không thể xác minh danh sách đầy đủ cho 2025. Judge cũng nêu thiếu giới hạn 50 incident trong kết luận.

## 3. Thay đổi đã thực hiện

- Sửa `agent.py`: hoàn thiện loop model → tool → observation với đúng `tool_call_id`, xử lý lỗi/trace/budget; thêm evidence gate yêu cầu ít nhất một URL đã đọc thành công từ `get_incident_details`. Khi câu hỏi đòi danh sách đầy đủ mà câu trả lời khẳng định “không có sự cố” dù status tool chỉ tìm 50 incident, ghi `validation_search_limit` và yêu cầu model sửa trong budget.
- Vì sao: A5 cho thấy kết luận phủ định vượt quá phạm vi dữ liệu; kiểm tra nguồn URL là contract riêng của Bài 4. Test offline `tests/test_validation.py` và `tests/test_agent_edges.py` kiểm tra hai nhánh này.
- Ở `eval_after.json`, A5 ghi `validation_search_limit` tại step 3 và 4; câu trả lời cuối đã nói “Không thể xác nhận ... danh sách đầy đủ ... bao gồm cả năm 2025”. Nó vẫn lan man về incident 2026 và được judge chấm 50/100, chưa phải lời giải hoàn chỉnh.

## 4. So sánh hai lần chạy

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---|---|
| Điểm tổng | 82.27/100 (22/22 scored) | 79.32/100 (22/22 scored) |
| Điểm case đã chọn (A5) | 40/100 | 50/100 |
| Số model calls (cả 22 case) | 53 | 54 |
| Token agent (`total_tokens`) | 47,655 | 51,896 |
| Token judge (`total_tokens`) | 42,006 | 41,052 |
| Chi phí | Không có số liệu chi phí trong report | Không có số liệu chi phí trong report |

- Hai report dùng cùng `provider=openai`, `model=gpt-4o-mini`, judge cùng model, `max_steps=8`, dataset `core`, snapshot cố định. Điểm tổng **giảm 2.95**, không thể kết luận cải tiến chung nhờ A5 tăng điểm.
- Lỗi đã giải quyết ở A5: không còn khẳng định chắc chắn không có sự cố năm 2025 trong câu trả lời cuối; trace cho thấy hai lần nhắc sửa.
- Lỗi còn lại hoặc mới xuất hiện: A5 vẫn trình bày quá nhiều incident 2026, judge chỉ chấm 50. Các case A7/H7 giảm điểm so với lần 1; judge phản ánh sai lệch thời gian, thiếu ranh giới bằng chứng ở một số case khác. Cần đọc từng trace trước khi quy nguyên nhân cho code vì model/judge có tính biến động.

### Bonus tùy chọn

`eval_bonus.json` chấm đủ 10/10 case: 78.5/100, quy đổi tham khảo **11.78/15**. Agent dùng schema và system prompt của `BonusTools`; trả 429/INVALID_ARGUMENTS thành observation, giới hạn tối đa hai lần thử thật cho cùng tool/provider khi liên tục 429, bỏ 160 `distractors` khỏi context model nhưng giữ trace, và nhận `next_offset` để model quyết định đọc trang sau. B2 đạt 100 và B5 đạt 100; B3 60, B4 70, B6 50, B10 50 cho thấy xử lý retry/tổng hợp nhiều nguồn/context còn hạn chế. Một request bonus case B3 chạy riêng trước full run được 70; điểm khác trong full run là 60, minh họa biến động model/judge. Không coi HTTP 429 là dịch vụ gặp sự cố.

## 5. Giới hạn

Judge LLM là ước lượng, mặc định cùng `gpt-4o-mini` với agent nên có thể thiên lệch; một lần chạy mỗi phiên bản không chứng minh ổn định, và thay đổi điểm có thể do ngẫu nhiên. Snapshot chính ngày 09/11/2026 và bổ sung ngày 10/11/2026 không phải trạng thái hiện tại; status search chỉ xét 50 incident gần nhất và trả tối đa 5 (bonus tối đa 8), incident details bài chính có thể cắt body/update. Gate nguồn kiểm tra URL có mặt, **không chứng minh từng claim đúng**. Với bonus, model tự chọn có xem `next_offset` hay không; không được khẳng định đã đọc hết timeline nếu còn trang. Các trace/report có thể chứa dữ liệu trả về từ API; cần kiểm tra và xóa thông tin nhạy cảm trước khi public.

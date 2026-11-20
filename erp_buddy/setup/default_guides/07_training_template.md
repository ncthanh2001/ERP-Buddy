---
roles: ERP Buddy Guide Manager
keywords: word, pdf, upload, file, tài liệu, tải file, train, training, teach, add knowledge, guide template, new guide, sample questions, keywords, answer mode, verbatim, guide test, huấn luyện, dạy chatbox, dạy trợ lý, đào tạo chatbox, thêm kiến thức, bổ sung kiến thức, cập nhật kiến thức, mẫu hướng dẫn, viết hướng dẫn, câu hỏi mẫu, từ khoá
questions: làm sao để dạy chatbox | chatbox có học từ file word pdf không | tôi muốn training cho chatbox | cách bổ sung kiến thức cho trợ lý | mẫu viết bài hướng dẫn cho chatbox | làm sao để chatbox trả lời đúng một câu hỏi | chatbox trả lời sai thì sửa thế nào | how do I teach the assistant | template for a new guide
---
# How to teach ERP Buddy (training template)

ERP Buddy learns from **ERP Buddy Guides**. Each guide covers one topic. Saving a guide takes effect immediately; there is nothing to retrain or restart.

## What training supports today
- **Supported:** short guides written or pasted by hand, one topic each, with keywords, sample questions and an optional approved answer.
- **Not supported yet:** learning from Word or PDF files, other uploaded documents, websites, or very long content in one go. Split such material into short guides, one per topic, and paste in the key steps.

## Steps
1. **Pick one topic** that users ask about, phrased as a task: "Create a sales order", "Receive stock into a warehouse".
2. **Create the guide**: [New ERP Buddy Guide](/app/erp-buddy-guide/new). The Content box starts with the template below.
3. **Keywords**: the words users actually type, in every language, comma-separated. Include abbreviations and slang (SO, PO, xuất bill) and avoid words that also belong to other topics.
4. **Sample Questions**: 5 to 10 real ways users ask, one per row. This is the strongest signal for picking the right guide.
5. **Answer Mode**:
   - *Reference*: the assistant reads the content and answers in its own words. Good for most topics.
   - *Verbatim*: users always get the **Approved Answer** word for word. Use it for policies, prices, legal or anything that must never vary.
6. **Visible to Roles**: leave empty for everyone, or pick the roles that may see this guide.
7. **Test it**: add questions in [ERP Buddy Guide Test](/app/erp-buddy-guide-test) with this guide as the expected guide, then press **Run All Tests**. When a question fails, add it to the guide's Sample Questions and run again.
8. **Keep it current**: untick **Enabled** on outdated guides instead of deleting them. Every change is kept in the guide's version history.

You can also ask ERP Buddy in the chat to draft a guide from your notes; you review and confirm it on the card before it is saved.

## Template for the Content box
```markdown
# <Task, e.g. Create a sales order>

**Used for:** <when and why someone does this>
**Before you start:** <records that must exist first, e.g. Customer, Item>

## Steps
1. Open [<Screen name>](/app/<screen-url>/new).
2. Fill in **<Field>**: <what to enter>.
3. Add the rows in **<Table>**: <columns to fill>.
4. **Save**, check the totals, then **Submit**.

## Notes
- <Common mistakes and how to avoid them>
- <Company rules, approvals, limits>

## Related
- Next step: <the document created after this one>
- Report: <report to check the result>
```

## Template for an Approved Answer (Verbatim mode)
```markdown
**<Topic>**
1. <Step one>
2. <Step two>
3. <Step three>

Need more help? Contact <team or person>.
```

## Checklist before saving
- [ ] One topic per guide, and the title says what the user wants to do
- [ ] Keywords in every language users write in, with abbreviations
- [ ] At least 5 Sample Questions taken from real user questions
- [ ] Steps are numbered and link to the right screens
- [ ] Answer Mode chosen; Approved Answer filled in for Verbatim
- [ ] A Guide Test case added and passing

# Samples

本目录用于本地样本数据和生成结果。

- `textbooks/`: 赛方提供的 7 本教材 PDF，仅本地使用，不提交 Git。
- `generated/`: 解析结果、实验知识库、临时报告等生成物，不提交 Git。
- `fixtures/`: 可以提交的小型测试样本，后续用于自动化测试。

## Fixture Policy

- Markdown/TXT 功能必须优先使用 `fixtures/` 下的小样本走 red/green TDD。
- PDF 官方教材样本已经在 `textbooks/`，但因为体积过大不提交 Git。
- MVP 解析走纯文字路线。图片和图表 fixture 可以存在，但首版只验证“跳过或记录 metadata”，不验证图片理解。

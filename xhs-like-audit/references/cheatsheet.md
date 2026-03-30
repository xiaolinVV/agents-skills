# XHS Like Audit 超短使用手册

## 1. 新开一批

```bash
python3 scripts/start_batch.py --roster-file /path/to/roster.txt --batch-root /tmp
```

直接从 zip 压缩包开一批：

```bash
python3 scripts/start_batch.py --roster-file /path/to/roster.txt --zip-file /path/to/screenshots.zip --batch-root /tmp
```

只做名单体检：

```bash
python3 scripts/lint_roster.py --input-file /path/to/roster.txt
```

## 2. 看图时只记这个顺序

1. 先看爱心有没有点亮
2. 只有点亮才去匹配名字
3. 引号里的多行名字算同一个博主组
4. 名字太糊、拿不准，就不要算

## 3. 每张图记一次结果

把判定写成一个 JSON，再更新进 state：

```bash
python3 scripts/update_counts.py --state-file /tmp/xhs-batch/state.json --matches-file /tmp/image-001.json
```

## 4. 导出名单顺序版

```bash
python3 scripts/render_report.py --state-file /tmp/xhs-batch/state.json --preset roster
```

## 5. 导出提交版

```bash
python3 scripts/render_report.py --state-file /tmp/xhs-batch/state.json --preset submit
```

## 6. 一次性导出整套交付文件

```bash
python3 scripts/export_delivery_pack.py --state-file /tmp/xhs-batch/state.json --output-dir /tmp/xhs-batch/delivery --name batch1 --only-nonzero-submit
```

## 7. 第一批/第二批/第三批合并总计

```bash
python3 scripts/merge_batches.py --state-files /tmp/batch1/state.json /tmp/batch2/state.json /tmp/batch3/state.json --output-file /tmp/merged/total.json --session-name total
```

## 8. 名单变了怎么办

- 名单可以变
- 逻辑不变
- 不同名单版本不要直接合并
- 旧批次要么单独留存，要么按新名单重跑

## 9. 重复图怎么办

- payload 里尽量带 `image_path`
- 系统会自动做指纹防重
- 如果提示重复图，先检查是不是重复发送了同一张

## 10. 最重要的一句

**宁可少算，不要乱算。**

## 11. zip 大批次怎么做

- `images-manifest.json` 是 zip 批次的图片清单
- 20+ 张图默认按 5-10 张分片
- 并行判图，串行 `update_counts.py`

## 12. 名单风险怎么处理

- `roster-lint.txt` 只报警，不自动合并
- 引号组才是硬合并规则
- 必须先确认爱心，再做唯一匹配

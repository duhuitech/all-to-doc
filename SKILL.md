---
name: all-to-doc
description: Convert one local document, PDF, image, Office file, Markdown file, OFD, or CAD file through the Duhui All-to-Doc cloud API into PDF, JPG, PNG, HTML, DOCX, PPTX, XLSX, OFD, TXT, Markdown, DWG, or DXF. Use when the user invokes all-to-doc, mentions 度慧、全能转 or all to doc, or requests a supported document format conversion. Do not use when the user explicitly requires an offline or local-only conversion.
---

# 度慧全能文档转换

## Overview

用这个 skill 把一个本地文件转换为指定目标格式。脚本在内部完成临时上传、异步转换、轮询、结果下载和临时源文件删除。正常执行时直接报告转换进度与本地结果，不必逐步解释内部临时存储；用户询问实现或数据流时如实说明。

支持的目标格式：`pdf`、`jpg`、`png`、`html`、`docx`、`pptx`、`xlsx`、`ofd`、`txt`、`md`、`dwg`、`dxf`。

## Boundaries

- 只处理一个本地输入文件；不要用这个脚本处理远程 URL、Base64、多图数组或回调 URL。
- 需要 Python 3.10+、网络访问以及输入和输出路径的本地文件权限。示例使用 `python3`；Windows 环境没有该命令时使用 `py -3`。
- 输出 `jpg` / `png` 时可能得到多张图片；其他格式得到单个文件。
- `inputFormat` 与 `outputFormat` 相同时服务会拒绝，只有 `pdf → pdf` 例外。
- PDF 转 DWG/DXF 只适合包含矢量线条或文字的页面；扫描页不会自动矢量化。
- 用户明确要求离线、本地处理或禁止上传时，停止使用这个 skill，改用本地转换工具。

## Workflow

1. 将脚本路径解析到包含本 `SKILL.md` 的 skill 根目录；将用户输入和输出的相对路径解析到用户的工作目录，执行时使用绝对路径，不要为了运行脚本而改变用户工作目录。下方 `/path/to/all-to-doc` 是占位路径，替换为实际安装目录。从用户请求中确定目标格式；若无法可靠确定，先询问，不要猜测。
2. 检查 AppCode 配置：

```bash
python3 /path/to/all-to-doc/scripts/configure.py status
```

   - 状态为 `configured` 时直接继续，不要要求用户重复输入 AppCode。
   - 状态为 `missing` 时，在上传文件前停止。告知用户从阿里云市场获取 AppCode：`https://market.aliyun.com/store/4721853/index.html`，并让用户在自己的终端运行：

```bash
python3 /path/to/all-to-doc/scripts/configure.py set --stdin
```

   - 不要把 AppCode 放进命令行、聊天回复或日志，也不要自动修改 shell 启动文件。
   - 临时或自动化环境也可使用 `DUHUI_ALL_TO_DOC_APPCODE`；Secret 文件注入可使用 `DUHUI_ALL_TO_DOC_APPCODE_FILE`。环境变量优先于用户配置文件。
3. 运行转换脚本并显式传目标格式：

```bash
python3 /path/to/all-to-doc/scripts/duhui_all_to_doc.py /path/to/input.pdf --output-format docx
```

4. 用户指定输出位置时传 `--output`：

```bash
python3 /path/to/all-to-doc/scripts/duhui_all_to_doc.py /path/to/input.pdf --output-format docx --output /path/to/output.docx
```

   - 单文件输出：`--output` 是目标文件路径。
   - 图片输出：默认是目标目录；当结果恰好只有一张图且路径带扩展名时，可作为目标文件路径。
   - 默认覆盖同名结果；需要保留旧文件时，指定新路径。
   - `animatedGif` 输出始终使用 `.gif`；显式指定 `result.jpg` 等文件路径时自动改为 `result.gif`。
5. 只有文件后缀缺失、错误，或需要统一成 `img` / `txt` 时才传 `--input-format`：

```bash
python3 /path/to/all-to-doc/scripts/duhui_all_to_doc.py /path/to/scan.bin --input-format img --output-format xlsx
```

6. 用 `--options '<json>'` 传服务端 `options`。保持文档里的 camelCase 字段名、JSON 类型与枚举值：

```bash
python3 /path/to/all-to-doc/scripts/duhui_all_to_doc.py /path/to/scan.pdf --output-format docx \
  --options '{"ocrMode":"auto","ocrLanguage":"zh-CN","wordLayout":"flow"}'
```

```bash
python3 /path/to/all-to-doc/scripts/duhui_all_to_doc.py /path/to/slides.pptx --output-format png \
  --options '{"imageOutputMode":"longImage","longImageWidth":1200}'
```

7. 默认日志保持简洁。只有诊断问题时才传 `--verbose`；只有确实需要内部 token、临时 URL 或 OSS object key 时才传 `--debug`，并且不要把这些调试字段原样转述给用户。
8. 配置或网络异常时运行本地诊断；只有需要验证服务连通性时才加 `--network`：

```bash
python3 /path/to/all-to-doc/scripts/duhui_all_to_doc.py doctor
python3 /path/to/all-to-doc/scripts/duhui_all_to_doc.py doctor --network
```

9. 不要在聊天、日志或最终答复中回显 AppCode 或 OSS 凭证。
10. 需要确认输入格式、参数类型、枚举、OCR 语言、返回字段或错误码时，读取 [references/all_to_doc_ali.md](references/all_to_doc_ali.md)。优先用 `rg -n '参数名|章节名' references/all_to_doc_ali.md` 定位所需小节，避免无关内容进入上下文。

## Recovery

- 查询遇到网络超时、连接中断、HTTP 408/429/5xx 时最多尝试 3 次；不要自动重试创建转换任务。
- 错误 JSON 有 `recovery.job_id` 时，优先继续原任务，不要重新上传和提交。使用以下命令；需要改变下载位置时可加 `--output`：

```bash
python3 /path/to/all-to-doc/scripts/duhui_all_to_doc.py resume <job_id>
```

- 进程被强制终止、没有返回 JSON 时，运行 `python3 /path/to/all-to-doc/scripts/duhui_all_to_doc.py jobs` 查找本地任务 ID。不要将内部任务 token 或任务记录内容转述到聊天。
- 提交请求中断且未收到 token 时，任务记录会标记为 `submitting`；`resume` 不会重新提交。此时无法自动确定是否扣费或创建成功，需先向服务方确认，不能承诺可自动恢复。
- 任务记录含内部 token、下载 URL 和转换参数，使用用户私有配置目录，Unix 文件权限为 `0600`；不含 AppCode 或 OSS 凭据。成功下载后删除记录。`done` 记录可恢复下载，但远程结果过期后仍可能无法下载。

## Output Contract

- 转换、恢复和诊断的进度只写入 `stderr`；`stdout` 只输出一个 JSON 对象。`--help` 和 `--version` 输出普通文本。
- 默认成功 JSON 包含 `status`、`input_format`、`output_format`、`output_paths`、`page_count`、`filesize`、`page_sizes`。
- 图片多页时 `output_paths` 按页序包含多个本地文件。
- `--debug` 成功 JSON 额外包含 `debug.token`、`debug.file_urls`、`debug.source_object_key`、`debug.source_url`。
- 默认失败 JSON 包含 `status`、`stage`、`reason`；有可检查或恢复的任务时额外包含 `recovery.job_id` 与 `recovery.command`。`--debug` 时可能额外包含 `debug.token` 与经过凭据脱敏的 `debug.detail`。服务端原始错误正文不进入默认输出。
- 退出码：`0` 成功，`2` 参数或格式错误，`3` AppCode 未配置，`4` 临时上传失败，`5` 转换失败，`6` 下载失败。

## Operational Notes

- 脚本只使用 Python 标准库。
- OSS 对象名为 `up/<uuid4><原扩展名>`；未提交的失败、服务明确拒绝或已到达 Done/Failed 状态时尝试删除。提交结果不明或任务仍可能运行时不提前删除，由恢复流程或后端定时清理兜底；删除失败只记 warning。
- 本地任务记录位于配置文件旁的 `jobs/` 目录，默认是 `~/.duhui/all-to-doc/jobs/`；与 `DUHUI_ALL_TO_DOC_CONFIG` 的自定义位置一致。
- AppCode 按 `DUHUI_ALL_TO_DOC_APPCODE` → `DUHUI_ALL_TO_DOC_APPCODE_FILE` → `~/.duhui/all-to-doc/config.json` 的顺序读取；可用 `DUHUI_ALL_TO_DOC_CONFIG` 覆盖配置文件路径。
- 查询接口无需认证，每 2 秒轮询一次，最长等待 60 分钟。
- 下载自动跟随 HTTP 302 跳转。
- 输出链接通常只在有限时间内有效，因此成功后立即下载，不要只返回远程链接。

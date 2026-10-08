# 度慧全能转 / Duhui All-to-Doc

通过阿里云市场度慧全能转接口，把单个本地文件转换为 PDF、图片、Word、PowerPoint、Excel、HTML、OFD、文本、Markdown 或 CAD 文件的轻量 Skill。

A lightweight skill for converting a single local file to PDF, images, Word, PowerPoint, Excel, HTML, OFD, text, Markdown, or CAD through the Duhui API on Alibaba Cloud Marketplace.

## 能力范围 / What This Skill Does

- 支持 Office、WPS、PDF、OFD、图片、电子书、HTML、Markdown、CAD 等本地输入文件。
- 使用 `convert_async` 云端异步接口，自动完成临时上传、任务查询、结果下载和临时源文件清理。
- 通过 `--options` 传入 OCR、布局、压缩、长图、动图、水印等转换参数。
- 网络故障后可通过本地任务记录恢复查询和下载，无需重复提交已经创建的任务。

- Accepts local Office, WPS, PDF, OFD, image, e-book, HTML, Markdown, CAD, and other supported files.
- Uses the cloud `convert_async` API and handles temporary upload, polling, download, and source cleanup.
- Supports OCR, layout, compression, long images, animated GIFs, watermarks, and other options.
- Resumes existing tasks and downloads after network failures without resubmitting the conversion.

### 支持的输出格式 / Supported Output Formats

| 类型 / Category | `--output-format` | 说明 / Notes |
| --- | --- | --- |
| PDF | `pdf` | 文档、图片转 PDF；支持 PDF→PDF / Document and image conversion; PDF→PDF is supported |
| 图片 / Images | `jpg`, `png` | 每页一图、长图；动图模式输出 GIF / Per-page images, long images, or GIF animation |
| Microsoft Office | `docx`, `pptx`, `xlsx` | Word、PowerPoint、Excel |
| HTML | `html` | 完整文档或嵌入式 HTML / Full document or embedded HTML |
| OFD | `ofd` | 开放版式文档 / Open Fixed-layout Document |
| 文本 / Text | `txt`, `md` | 纯文本或 Markdown / Plain text or Markdown |
| CAD | `dwg`, `dxf` | 仅支持单页矢量 PDF 输入 / A single vector PDF page only |

### 支持的输入文件 / Supported Input Files

| 类型 / Category | 常见扩展名 / Typical Extensions |
| --- | --- |
| PDF | `pdf` |
| Microsoft Office | `doc`, `docx`, `ppt`, `pptx`, `xls`, `xlsx`, `pot`, `pps`, `ppsx`, `csv` |
| WPS | `wps`, `wpt`, `dps`, `dpt`, `et`, `ett` |
| Apple iWork | `pages`, `key`, `numbers` |
| OFD | `ofd` |
| 电子刊物 / E-publications | `caj`, `nh`, `kdh` |
| 电子书 / E-books | `epub`, `chm`, `mobi`, `azw`, `azw3`, `fb2`, `cbr`, `cbz`, `djvu` |
| Markdown / SVG | `md`, `svg` |
| CAD | `dwg`, `dxf`, `dwt`, `dws`, `dwf`, `dwfx`, `dgn`, `plt` 等 / and others |
| 3D 模型 / 3D models | `obj`, `stl`, `gltf`, `glb`, `fbx`, `ifc`, `step` 等；仅静态预览 / and others; static previews only |
| Figma / Sketch | `fig`, `sketch` |
| 网页文件 / Web files | `html`, `htm`, `mht`, `eml` |
| 图片 / Images | `png`, `jpg`, `jpeg`, `gif`, `tif`, `tiff`, `bmp`, `webp`, `ai` 等 / and others |
| 文本和代码 / Text and code | `txt`, `rtf`, `java`, `js`, `c`, `cpp`, `css`, `xml`, `log` 等 / and others |

完整格式列表和参数说明见 [API 文档](references/all_to_doc_ali.md)。

See the [API reference](references/all_to_doc_ali.md) for the complete format list and parameter details.

## 兼容性 / Compatibility

Skill 使用通用的 `SKILL.md` 和 Python 标准库脚本。支持 Agent Skills 的工具可加载 Skill；其他能够运行命令的 AI Agent 或自动化流程也可直接调用脚本。

The skill uses `SKILL.md` and Python standard-library scripts. Tools supporting Agent Skills can load it; other command-capable agents and automation workflows can invoke the scripts directly.

## 安装方式 / Installation

### 方式一：使用 `skills` CLI / Option 1: Use the `skills` CLI

需要 Node.js / Requires Node.js:

```bash
npx skills add https://github.com/duhuitech/all-to-doc --skill all-to-doc
```

按提示选择目标 Agent。更多安装选项见 [skills CLI](https://github.com/vercel-labs/skills)。

Select your target agent when prompted. See the [skills CLI](https://github.com/vercel-labs/skills) for additional installation options.

### 方式二：在 Agent 中安装 / Option 2: Install in Your Agent

将仓库地址交给支持安装 Skill 的 Agent：

Give this repository URL to an agent that supports skill installation:

```text
https://github.com/duhuitech/all-to-doc
```

也可以克隆仓库后直接调用脚本：

Alternatively, clone the repository and run the scripts directly:

```bash
git clone https://github.com/duhuitech/all-to-doc.git
cd all-to-doc
```

## 前置条件与 AppCode / Requirements and AppCode

- Python 3.10+、网络访问，以及本地输入/输出文件权限。
- 购买阿里云市场相应服务后获得的有效 AppCode。
- 每次处理一个本地文件。

- Python 3.10+, network access, and permission to read and write local files.
- A valid AppCode obtained after subscribing to the corresponding Alibaba Cloud Marketplace service.
- One local source file per conversion.

在 [度慧阿里云市场店铺](https://market.aliyun.com/store/4721853/index.html)选择“度慧全能转”服务，按商品说明获取 AppCode。转换费用和额度以云市场商品及账户为准。

Select the All-to-Doc service in the [Duhui Alibaba Cloud Marketplace store](https://market.aliyun.com/store/4721853/index.html) and obtain an AppCode. Conversion pricing and quotas depend on your subscription.

在 Skill 安装目录或克隆目录中运行以下命令，在终端提示中输入 AppCode：

Run this from the installed skill directory or cloned repository, then enter your AppCode at the terminal prompt:

```bash
python3 scripts/configure.py set --stdin
python3 scripts/configure.py status
```

AppCode 保存在 `~/.duhui/all-to-doc/config.json`，Unix 文件权限为 `0600`。不要把真实 AppCode 写进聊天、命令行参数或仓库。删除已保存配置可运行 `python3 scripts/configure.py clear`。

The AppCode is saved in `~/.duhui/all-to-doc/config.json` with Unix permissions `0600`. Keep the actual value out of chat, command-line arguments, and source control. Use `python3 scripts/configure.py clear` to remove the saved configuration.

自动化环境的读取优先级 / Credential resolution for automation:

1. `DUHUI_ALL_TO_DOC_APPCODE`：环境变量 / Environment variable.
2. `DUHUI_ALL_TO_DOC_APPCODE_FILE`：包含 AppCode 的文本文件路径 / Path to a text file containing the AppCode.
3. `~/.duhui/all-to-doc/config.json`：用户配置 / User configuration.

`DUHUI_ALL_TO_DOC_CONFIG` 可覆盖配置文件位置。Windows 没有 `python3` 时，可使用 `py -3`。

Use `DUHUI_ALL_TO_DOC_CONFIG` to override the configuration location. On Windows, use `py -3` if `python3` is unavailable.

## 使用方式 / Usage

在 Agent 中可直接提出请求，例如 / Example agent requests:

```text
用度慧全能转把 /path/to/report.pdf 转成 Word。
把 /path/to/slides.pptx 转成长图 PNG。
Use $all-to-doc to convert /path/to/table.png to Excel.
```

以下命令示例从 Skill 根目录运行；将 `/path/to/…` 替换为实际文件路径。Agent 调用时应使用脚本及用户文件的绝对路径。

Run these examples from the skill root and replace `/path/to/…` with your actual paths. Agents should invoke the scripts with absolute script, input, and output paths.

```bash
# Word → PDF
python3 scripts/duhui_all_to_doc.py /path/to/input.docx --output-format pdf

# PDF → Word, with Chinese OCR
python3 scripts/duhui_all_to_doc.py /path/to/scan.pdf --output-format docx \
  --options '{"ocrMode":"auto","ocrLanguage":"zh-CN","wordLayout":"flow"}'

# PowerPoint → long PNG image
python3 scripts/duhui_all_to_doc.py /path/to/slides.pptx --output-format png \
  --options '{"imageOutputMode":"longImage","longImageWidth":1200}'

# Explicit output location
python3 scripts/duhui_all_to_doc.py /path/to/input.pdf --output-format docx \
  --output /path/to/output.docx
```

单文件默认保存到输入文件同目录；多图输出保存到目录。**同名结果默认覆盖**，需要保留旧文件时请指定其他路径。进度写入 `stderr`，结果以 JSON 写入 `stdout`。

Single-file results default to the source directory; multiple images are saved in a directory. **Existing destination files are overwritten by default**; choose another output path to preserve them. Progress goes to `stderr`, and results are emitted as JSON on `stdout`.

## 支持参数 / Supported Options

使用 `--options` 传入 JSON 对象，字段名、类型和枚举采用全能转 API 的定义。以下是常用参数；完整说明见 [API 文档](references/all_to_doc_ali.md)。

Pass a JSON object through `--options`, using the All-to-Doc API's field names, types, and enums. Common options are listed below; see the [API reference](references/all_to_doc_ali.md) for details and format-specific applicability.

| 参数 / Option | 类型 / Type | 用途 / Purpose |
| --- | --- | --- |
| `ocrMode` | string | OCR 模式：`off`, `auto`, `force`，可用值取决于输入格式 / OCR mode; availability depends on input format |
| `ocrLanguage` | string | OCR 语言，如 `zh-CN`, `en` / OCR language |
| `wordLayout` | string | Word 布局：`flow`, `fixed` / Word layout |
| `excelSheetMode` | string | Excel 工作表策略：`auto`, `singleSheet`, `sheetPerPage` / Worksheet strategy |
| `pageRanges` | string | PDF 页码，如 `1,3,5-7` / PDF page selection |
| `compressionLevel` | string | PDF 压缩：`none`, `low`, `medium`, `high` / PDF compression |
| `pdfLinearized` | boolean | PDF 快速 Web 显示 / Fast Web View |
| `imageOutputMode` | string | `separateImages`, `longImage`, `animatedGif` |
| `longImageWidth` | integer | 长图宽度，最大 2000 像素 / Long-image width, up to 2000 pixels |
| `htmlOutputMode` | string | `fullDocument`, `embedded` |
| `watermarkText` | string | 水印文本 / Watermark text |

```bash
python3 scripts/duhui_all_to_doc.py /path/to/input.docx --output-format pdf \
  --options '{"compressionLevel":"medium","pdfLinearized":true}'
```

## 任务恢复与诊断 / Recovery and Diagnostics

查询遇到暂时性网络错误时最多尝试 3 次。错误 JSON 中出现 `recovery.job_id` 时，恢复原任务，而不是重新提交转换：

Polling retries transient network failures up to three attempts. If an error includes `recovery.job_id`, resume that task instead of submitting a new conversion:

```bash
python3 scripts/duhui_all_to_doc.py jobs
python3 scripts/duhui_all_to_doc.py resume YOUR_JOB_ID
python3 scripts/duhui_all_to_doc.py doctor
python3 scripts/duhui_all_to_doc.py doctor --network
```

任务记录存放在用户配置旁的 `jobs/` 目录，成功下载后删除。提交请求中断且尚未收到 token 时，无法自动确认任务是否创建成功，需先向服务方核实；`resume` 不会重新提交。远程下载结果过期后，恢复下载也可能失败。

Recovery records are stored in `jobs/` beside the user configuration and removed after successful downloads. If submission is interrupted before a task token arrives, verify the outcome with the service before resubmitting. `resume` never creates a new task. Downloads can also expire.

`--verbose` 显示详细进度；`--debug` 会包含内部任务 token 和临时 URL，分享日志前请检查这些字段。

Use `--verbose` for detailed progress. `--debug` includes internal task tokens and temporary URLs; review those fields before sharing logs.

## 使用边界 / Limitations

- 文件由度慧云服务处理，需要临时上传；明确要求离线或禁止上传时不使用本 Skill。
- 只支持单个本地文件，不接受远程 URL、Base64、多图数组或 `callbackUrl`。
- 本地输入文件大小上限为 1500 MiB；实际转换还受服务规则约束。
- 相同格式互转不支持，`pdf → pdf` 除外。
- PDF 转 DWG/DXF 仅支持单页矢量 PDF；扫描页不会自动矢量化。
- 3D 文件只生成静态预览；动图模式固定输出 `.gif`。

- Files are processed in the Duhui cloud and require temporary upload. Do not use this skill for offline-only or no-upload requests.
- Accepts one local file; remote URLs, Base64, image arrays, and `callbackUrl` are outside this skill's workflow.
- The local input limit is 1500 MiB; service-specific conversion rules also apply.
- Same-format conversion is rejected, except `pdf → pdf`.
- PDF-to-DWG/DXF requires a single vector PDF page; scanned pages are not automatically vectorized.
- 3D files produce static previews, and animated-image output always uses `.gif`.

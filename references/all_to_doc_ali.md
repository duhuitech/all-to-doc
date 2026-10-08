# 度慧全能转（阿里云市场）

## 文档导航

- [概述与使用流程](#概述)
- [文档格式转换接口](#convert)
- [查询结果接口与返回字段](#query)
- [options 完整参数](#options)
- [OCR 语言](#langcode)
- [回调 URL](#callback)
- [下载结果与 302 跳转](#download302)
- [阿里云 OSS 内网说明](#alioss)
- [错误码](#error)
- [阿里云签名方式](#sig)

**在线试用：**

[https://try.dhconvert.com/](https://try.dhconvert.com/)

**小程序搜索：**

*文档转换终结者*
<img src="https://www.duhuitech.com/images/qr_wxmini_new_try.jpg" alt="文档转换终结者小程序二维码" width="140" />

---

## 概述

80+种格式互转，70+个自定义参数！能进行各种常见格式之间的互相转换，不仅是word等office文件和pdf互转。拥有强大的OCR支持，对扫描件、拍照件可识别成可编辑 Word/Excel、可改可搜PDF，拍照表格可进 Excel，网址可导出正式文件等。提供了丰富的自定义参数，支持水印、压缩，加解密、页面大小范围等等。按次计费、不按页数。

### 使用流程

1. 调用[**文档格式转换**](#convert)接口，提交输入文件和转换参数。
2. 接口立即返回 `token`，表示任务已创建成功。
3. 后续通过以下任一方式获取结果：
   调用[**查询结果**](#query)接口轮询任务状态；或在 `options` 中传入 `callbackUrl`，等待系统回调，详细见[**回调URL**](#callback)。

**调用[**文档格式转换**](#convert) API 需要签名，详细见文档附录：[阿里签名](#sig)。**

---

阿里云支持从OSS内网直接下载文件，节约流量，见：[**阿里云独有部分**](#alioss)


<div style="page-break-before: always"></div>


<a name="convert"></a>
## 文档格式转换

```
https://all2doc.market.alicloudapi.com/convert_async
```

**HTTP方式：** POST

**Header中的Content-Type**传入**application/json**

**Body是JSON格式**

**必须签名才能调用成功，签名见[阿里签名](#sig)规则**:

<https://help.aliyun.com/zh/api-gateway/traditional-api-gateway/use-cases/call-apis>

### 支持的输出格式

| **类型**       | **扩展名（outputFormat 取值）** | **备注** |
| -------------- | --------------------- | -------- |
| PDF            | pdf                   |   |
| 图片           | jpg, png              | 通过 `options.imageOutputMode` 选择每页一图、长图或动图；动图固定输出 GIF，与 `outputFormat` 无关 |
| HTML           | html                  | 默认适合阅读；需要适合编辑（如放入网页编辑器）时，通过 `options.htmlOutputMode` 设置 |
| 微软 Office    | docx, pptx, xlsx      |  |
| 开放版式文档   | ofd                   |          |
| 文本文件       | txt                   |          |
| Markdown       | md                    |          |
| CAD 图纸       | dwg, dxf              | 仅支持 PDF 一页输入 |

### 支持的输入格式



| **类型**       | **扩展名（inputFormat 取值）**                                          | **备注** |
| -------------- | ----------------------------------------------------------------------- | -------- |
| PDF文件        | pdf                                                                     |          |
| 微软Office文档 | doc, docx, ppt, pptx, xls, xlsx, pot, pps, ppsx, csv                    |          |
| WPS文档        | wps, wpt, dps, dpt, et, ett                                             |          |
| 苹果iWork文档  | pages, key, numbers                                                     |          |
| 开放版式文档   | ofd                                                                     |          |
| 电子刊物       | caj, nh, kdh                                                            |          |
| 电子书         | epub, chm, mobi, azw, azw3, fb2, cbr, cbz, djvu                         |          |
| Markdown       | md                                                                      |          |
| SVG            | svg                                                                     |          |
| CAD文档        | dwg, dxf, dwt, dws, dwf, dwfx, dxb, dgn, plt, cf2, cgm                                                      |          |
| 3D模型         | obj, 3ds, stl, gltf, glb, fbx, dae, ifc, step, stp, iges, igs, fcstd, brep, ply | **静态预览**（平面示意图，按 6 个视角展示：等轴测 / 前 / 右 / 顶 / 后 / 左，便于快速查看模型外观；**非**可旋转的交互式 3D） |
| Figma和Sketch  | fig, sketch                                                             |          |
| 网页文件       | html, htm, mht, eml                                                     |          |
| 图片文件       | png, jpg, jpeg, gif, tif, tiff, bmp, webp, ai 等                        | 可统一传 **img** |
| 文本文件       | txt, rtf, java, js, c, cpp, jsp, css, xml, properties, log 等           | 可统一传 **txt** |
| 网址网页       | url                                                                     | 输入必须是单个 HTTP/HTTPS URL |


### 请求参数

| **参数**     | **类型**   | **备注** | **默认值** |
| ------------ | ---------- | -------- | ---------- |
| input        | string 或 string数组 | 输入文件。字符串：单个 URL（最大 1500M）或 Base64（最大 8M）；数组：多张图片（URL / Base64 可混合） | 必须发送 |
| outputFormat | string     | 目标格式，见上方输出格式表 | 必须发送 |
| inputFormat  | string     | 源文件类型。可省略，由系统自动识别；网页抓取必须显式传 `url` | 自动识别 |
| options      | dictionary | 可选转换参数，不传则用系统默认值；完整参数见附录 [**options 参数**](#options) | 无 |

多数场景只需传 `input` 与 `outputFormat` 即可完成转换。需要精细控制时，可在 `options` 中传入可选参数，例如：

- **Office / PDF / 图片 / 网页 / EPUB / CAD**：页码范围、OCR、密码、审阅标记、Excel 页边距与工作表、PPT 讲义布局、图片纠偏与背景、网页视口与边距、CAD 图层与品质等
- **输出控制**：文件名、回调 URL、PDF 压缩/加密/线性化、图片每页一图/长图/动图、HTML 大纲与嵌入模式、Word/Excel/Txt 布局策略、水印等


### 请求示例

- 例1: Word 转 PDF

> ```
> {"input": "http://xxx.docx", "outputFormat": "pdf"}
> ```

- 例2: Word 转 PNG（每页一张图）

> ```
> {"input": "http://xxx.docx", "outputFormat": "png"}
> ```

- 例3: PDF 转长图

> ```
> {"input": "http://xxx.pdf", "outputFormat": "png", "options": {"imageOutputMode": "longImage", "longImageWidth": 1200}}
> ```

- 例4: PPT 转动图

> ```
> {"input": "http://xxx.pptx", "outputFormat": "jpg", "options": {"imageOutputMode": "animatedGif", "animationFrameDurationSeconds": 2}}
> ```

- 例5: PDF 转 Word，并指定 OCR

> ```
> {
>   "input": "http://xxx.pdf",
>   "inputFormat": "pdf",
>   "outputFormat": "docx",
>   "options": {"ocrMode": "auto", "ocrLanguage": "zh-CN"}
> }
> ```

- 例6: 多张图片转 Word（URL 与 Base64 可混合）

> ```
> {
>   "input": ["http://xxx.png", "base64图片1", "base64图片2"],
>   "outputFormat": "docx"
> }
> ```

- 例7: Base64 文档转 HTML，指定结果文件名

> ```
> {
>   "input": "base64字符串",
>   "inputFormat": "docx",
>   "outputFormat": "html",
>   "options": {"outputFileName": "result"}
> }
> ```

- 例8: 网页 URL 转 Word

> ```
> {
>   "input": "https://www.xxx.com/xxx",
>   "inputFormat": "url",
>   "outputFormat": "docx"
> }
> ```

- 例9: 网页 URL 转 Word，并设置回调

> ```
> {
>   "input": "https://www.example.com/article/123",
>   "inputFormat": "url",
>   "outputFormat": "docx",
>   "options": {
>     "callbackUrl": "https://api.example.com/callback"
>   }
> }
> ```

- 例10: PDF 第 2 页转 DWG

> ```
> {
>   "input": "http://xxx.pdf",
>   "outputFormat": "dwg",
>   "options": {"pageRanges": "2"}
> }
> ```

### 返回数据结构

| **名称** | **类型**   | **是否必须返回** | **备注**       |
| -------- | ---------- | ---------------- | -------------- |
| code     | number     | 是               | 10000:请求成功 |
| msg      | string     | 是               |                |
| result   | Dictionary | 否               | 成功后返回     |

result:

| **名称** | **类型** | **是否必须返回** | **备注**                   |
| -------- | -------- | ---------------- | -------------------------- |
| token    | string   | 是               | 用于[查询结果](#query)接口 |

**返回示例(成功状态)：**

```
{
    "code":10000,
    "msg":"",
    "result":{"token":"xxx"}
}
```

**返回示例(失败状态)：**

```
{
    "code":40001,
    "msg":"ParmNotRight"
}
```

### 转换能力说明

- 输入与输出格式可任意组合，但`inputFormat` 与 `outputFormat` 相同时会直接报错（例如 docx→docx 不合法）。特例：`pdf→pdf` 合法。
- Office 新旧格式可互转（`doc→docx`、`ppt→pptx`、`xls→xlsx`）保留原生 Office 结构。
- `input` 为数组时只支持图片，不能传文档数组。最大支持50张图。
- `inputFormat=url` 时，`input` 必须是单个 HTTP/HTTPS URL 字符串，不能是数组、Base64 或 ftp。
- PDF 转 DWG/DXF 仅适用于包含线条或文字等矢量内容的 PDF。扫描件和纯图片页不会自动矢量化。OCR、纠偏、背景清理等图片识别参数不生效。扫描页会明确返回失败，而不是生成仅引用临时图片的 CAD 文件。

<div style="page-break-before: always"></div>


<a name="query"></a>
## 查询结果

**调用方式（任选其一，返回结果相同）：**

<span style="color:red;">注意：方法2会扣购买次数，方法2主要用于 MCP；代码集成请优先使用方法1。</span>

**方法1**：GET（无需签名）

```
https://api.duhuitech.com/q?token=xxx
```

**方法2**：POST，`Content-Type: application/json`（**需要签名**，见[阿里签名](#sig)）

```
https://all2doc.market.alicloudapi.com/query
```

Body：

```
{"token": "xxx"}
```

**请求参数：**

| **参数** | **类型** | **备注**                | **是否必须发送** |
| -------- | -------- | ----------------------- | ---------------- |
| token    | string   | 调用转换接口拿到的 token | 是               |

由于转换需要时间，文件越大页数越多，转换越久，故需要**轮询**查询接口来获得结果。查询频率可以是1s一次，也可以更长一些。
**查询后先看status，如果是Done或Failed，则转换结束，停止轮询。如果是Doing或Pending，则继续轮询。**

**返回数据结构：**

| **名称** | **类型**   | **是否必须返回** | **备注**       |
| -------- | ---------- | ---------------- | -------------- |
| code     | number     | 是               | 10000:请求成功 |
| msg      | string     | 是               |                |
| token    | string     | 是               | 请求的token    |
| result   | Dictionary | 否               | 成功后返回     |

result:

<table>
<colgroup>
<col style="width: 10%" />
<col style="width: 15%" />
<col style="width: 10%" />
<col style="width: 25%" />
<col style="width: 40%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>名称</strong></th>
<th><strong>含义</strong></th>
<th><strong>类型</strong></th>
<th><strong>是否必须返回</strong></th>
<th><strong>备注</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>status</td>
<td>状态</td>
<td>string</td>
<td>是</td>
<td>Pending：还未开始<br>
Doing：正在转换<br>
Done：转换成功<br>
Failed：转换失败<br></td>
</tr>
<tr class="even">
<td>progress</td>
<td>进度</td>
<td>number</td>
<td>否（status为Doing/Pending时返回）</td>
<td>范围：0.00 - 1.00，比如0.88表示88%</td>
</tr>
<tr class="odd">
<td>fileurl</td>
<td>输出文件地址</td>
<td>string</td>
<td>否（status为Done，且非文档转图片时返回）</td>
<td>PDF、HTML、Office、文本等单文件输出均返回该字段</td>
</tr>
<tr class="even">
<td>fileurls</td>
<td>输出图片地址数组</td>
<td>string数组</td>
<td>否（status为Done，且文档转图片时返回）</td>
<td><strong>文档转图片始终返回 fileurls，即使只有一页</strong>；不会返回 fileurl</td>
</tr>
<tr class="odd">
<td>count</td>
<td>页数 / 图片数</td>
<td>integer</td>
<td>否（status为Done时返回）</td>
<td>单文件输出为页数；文档转图片为图片张数</td>
</tr>
<tr class="even">
<td>filesize</td>
<td>文件大小</td>
<td>integer</td>
<td>否（status为Done时返回）</td>
<td>输出文件大小</td>
</tr>
<tr class="odd">
<td>pagesizes</td>
<td>每页尺寸</td>
<td>array</td>
<td>否</td>
<td>部分转 PDF 且请求了页面尺寸信息时返回</td>
</tr>
<tr class="even">
<td>reason</td>
<td>失败原因</td>
<td>string</td>
<td>否（status为Failed时可能返回）</td>
<td>转换失败的原因</td>
</tr>
</tbody>
</table>

**结果读取规则：**

1. 先看 `status`。
2. 若 `status=Done`：
   - `outputFormat` 为 `jpg` / `png`（文档转图片）：读取 `fileurls`（数组；长图和动图也各返回一个 URL）。
   - 其他输出格式：读取 `fileurl`（单个字符串）。
3. 若 `status=Failed`：读取 `reason`。
4. 若 `status=Doing` 或 `Pending`：可读取 `progress`，继续轮询。

**返回示例(进行中)：**

```
{
	"code":10000,
	"msg":"",
	"token":"xxx",
	"result":
	{
		"progress":0.02,
		"status":"Doing"
	}
}
```

**返回示例(成功，单文件，如 PDF/Word/HTML)：**

```
{
	"code":10000,
	"msg":"",
	"token":"xxx",
	"result":
	{
		"status":"Done",
		"fileurl":"https://file.duhuitech.com/o/xxx/xxx.pdf",
		"count":10,
		"filesize":17747
	}
}
```

**返回示例(成功，文档转图片，多页)：**

```
{
	"code":10000,
	"msg":"",
	"token":"xxx",
	"result":
	{
		"status":"Done",
		"fileurls":[
			"https://file.duhuitech.com/o/xxx/1.png",
			"https://file.duhuitech.com/o/xxx/2.png",
			"https://file.duhuitech.com/o/xxx/3.png"
		],
		"count":3,
		"filesize":1649699
	}
}
```

**返回示例(成功，文档转图片，仅一页也返回数组)：**

```
{
	"code":10000,
	"msg":"",
	"token":"xxx",
	"result":
	{
		"status":"Done",
		"fileurls":[
			"https://file.duhuitech.com/o/xxx/1.jpg"
		],
		"count":1,
		"filesize":20480
	}
}
```

**返回示例(失败状态)：**

```
{
	"code":40000,
	"msg":"No such token"
}
```

或：

```
{
	"code":10000,
	"msg":"",
	"token":"xxx",
	"result":
	{
		"status":"Failed",
		"reason":"convert failed"
	}
}
```


<div style="page-break-before: always"></div>


<a name="options"></a>
## 参数列表 options

注意事项：整数参数使用标准 JSON 数字，布尔使用 JSON `true` / `false`，枚举使用语义字符串（如 `source` / `landscape` / `portrait`）。未知字段、类型错误、枚举或范围错误会返回参数错误。

#### 输入 Office 文件相关（inputFormat 为 Word / PPT / Excel / WPS 等）

| **参数** | **类型** | **备注** | **默认值** |
| -------- | -------- | -------- | ---------- |
| wordShowMarkup | boolean | 如果是 Word 文件，是否显示审阅标记 | false |
| powerPointLayout | string | 如果是 PPT 文件，导出样式：<br>`slides` 幻灯片<br>`oneSlideHandout` 每页一个幻灯片<br>`twoSlideHandout` 每页两个幻灯片<br>`threeSlideHandout` 每页三个幻灯片<br>`fourSlideHandout` 每页四个幻灯片<br>`sixSlideHandout` 每页六个幻灯片<br>`nineSlideHandout` 每页九个幻灯片 | slides |
| powerPointHandoutOrder | string | 如果是 PPT 讲义模式，排列顺序：<br>`horizontal` 水平<br>`vertical` 垂直 | horizontal |
| powerPointHandoutOrientation | string | 如果是 PPT 讲义模式，页面方向：<br>`source` 不改变<br>`landscape` 横向<br>`portrait` 纵向 | source |
| excelCenterOnPage | boolean | 如果是 Excel 文件，内容是否横竖居中 | false |
| excelMargin | integer | 如果是 Excel 文件，四边边距，单位 points（磅），不能为负数 | 使用文件默认 |
| excelSheetIndex | integer | 如果是 Excel 文件，指定转换的 Sheet 序号；第一页为 `1`，省略表示全部 | 全部 |
| excelShowGridlines | boolean | 如果是 Excel 文件，是否显示网格线 | true |
| excelContentRange | string | 如果是 Excel 文件，内容范围：<br>`default` 默认<br>`printArea` 使用打印区域<br>`usedRange` 只显示有内容的区域 | default |
| pageSize | string | 如果是 Excel 等文件，设定页面大小：<br>`source` 跟随源文档（无则按系统默认）<br>`a3` A3<br>`a4` A4<br>`a5` A5<br>`b4` B4<br>`b5` B5<br>`letter` Letter<br>`legal` Legal<br>`tabloid` Tabloid<br>`ledger` Ledger | source |
| pageOrientation | string | 如果是 Word、Excel、TXT、HTML、Markdown、网址，设定页面方向：<br>`source` 不变<br>`landscape` 横向<br>`portrait` 竖向 | source |
| sourcePassword | string | 源文件密码，支持有密码的 Word、PPT、Excel 文件类型 | 无 |

#### 输入 PDF 相关（inputFormat=pdf）

| **参数** | **类型** | **备注** | **默认值** |
| -------- | -------- | -------- | ---------- |
| pageRanges | string | 要转换的 PDF 页码。输出 DWG/DXF 时只能传一个正整数；其它输出可传列表或范围，例如：`1,3,5-7` | DWG/DXF：第 1 页；其它输出：全部页 |
| ocrMode | string | **PDF 转为 Word/PPT/Excel/Txt/OFD/Markdown 时：** OCR 模式：<br>`off` 不做 OCR<br>`auto` 自动 OCR<br>`force` 强力 OCR（针对加密、编码不正确导致的乱码、叠字、未 OCR 文字等问题）<br><br>**PDF 转 PDF 时：**<br>`off` 不识别<br>`auto` 识别扫描版文字，使输出 PDF 中文字可选可搜索 | PDF→文档：自动 OCR；<br><br>PDF→PDF：off |
| ocrLanguage | string | OCR 识别语言，使用 BCP 47 标签，例如 `zh-CN`、`en`。取值见附录 [OCR 语言（ocrLanguage）](#langcode) | zh-CN |
| sourcePassword | string | PDF 文件密码，无密码可不传 | 无 |
| vectorizeText | boolean | PDF 转 PDF 且开启 OCR 时：是否用矢量文字替换图片内文字，使放大后仍清晰 | false |

#### 输入图片相关（inputFormat 为 jpg/png/img 等，或 input 为图片数组）

| **参数** | **类型** | **备注** | **默认值** |
| -------- | -------- | -------- | ---------- |
| ocrLanguage | string | OCR 识别语言，BCP 47 标签。取值见附录 [OCR 语言（ocrLanguage）](#langcode) | zh-CN |
| ocrMode | string | `off` 不识别<br>`auto` 识别图中文字 | off |
| dewarp | boolean | 是否切边矫正。**打开后每次只允许传入一张图**（短边大于 20，长边小于 10000） | false |
| deskew | boolean | 是否倾斜矫正 | false |
| backgroundMode | string | **图片转为 Word/PPT/Excel/Txt/OFD/Markdown 时：**<br>`auto` 智能保留背景<br>`remove` 完全清除背景<br>`preserve` 完全保留背景 | auto |
| autoRotate | boolean | **图片转为 Word/PPT/Excel/Txt/OFD/Markdown 时：** 是否根据文字方向自动旋转。传 `false` 可加快速度（已确定文字方向时） | true |
| pageSize | string | **图片转为 Word/PPT/Excel/Txt/OFD/Markdown 时：** 页面大小：<br>`source` 维持原图比例<br>`a3` A3<br>`a4` A4<br>`a5` A5<br>`b4` B4<br>`b5` B5<br>`letter` Letter<br>`legal` Legal<br>`tabloid` Tabloid<br>`ledger` Ledger | source |
| detectBarcodes | boolean | **图片转为 Word/PPT/Excel/Txt/OFD/Markdown 时：** 是否识别条码和二维码，并避开码区以提高识别精度 | false |
| splitSpreadPages | boolean | 横向图若有左右两部分（常见于试卷）时分割为 2 页。 | false |
| grayscale | boolean | **图片转 PDF/HTML 时：** 是否输出灰度图 | false |
| vectorizeText | boolean | **图片转 PDF/HTML 且开启 OCR 时：** 是否用矢量文字替换图片内文字 | false |
| imagePageWidth | integer | **图片转 PDF/HTML 时：** 统一每页固定宽度（像素），最大 4096。设置后转 PDF 时会使 `pageSize` 失效 | 不限制 |
| tableDetection | string | **图片转 Word/PPT 时：** 表格识别：<br>`none` 不识别<br>`tables` 只识别表格<br>`tablesAndUnderlines` 识别表格和下划线 | none |

#### 输入网址 / 网页相关（inputFormat=url，或 html / md 等）

| **参数** | **类型** | **备注** | **默认值** |
| -------- | -------- | -------- | ---------- |
| webViewport | string | 视口模式：<br>`desktop` 桌面端网页<br>`mobile` 移动端网页 | desktop |
| webViewportWidth | integer | 桌面端显示时网页最大宽度，最大 1920 | 1440 |
| pageMargins | string | 页面边距，按顺序左 上 右 下，单位可为 `px` / `in` / `cm` / `mm`。例如：`1px 2px 3px 4px` | 网址/HTML：左右 0、上下 1cm<br>Markdown：四边 0.55in |
| webWaitSeconds | integer | 停留后再抓取页面，单位秒，范围 0–30 | 0 |
| webTimeoutSeconds | integer | 加载资源超时时间，单位秒，范围 1–120 | 40 |
| webSinglePage | boolean | 是否生成单页长文档。打开后 `pageMargins` 失效。主要用于输出 PDF | false |
| webTextOnly | boolean | 是否按文本模式抽取网页内容 | false |
| webExtractMainContent | boolean | 是否抽取正文阅读区域 | false |
| markdownTheme | string | 仅当输入为 Markdown 时，设置 Markdown 渲染主题。可选值：`monet`（莫奈）、`vangogh`（梵高）、`rembrandt`（伦勃朗）、`vermeer`（维米尔）、`picasso`（毕加索）、`kandinsky`（康定斯基）、`davinci`（达·芬奇） | 不传或传空时使用默认样式 |
| pageSize | string | 输出页面大小，仅在输出为 `pdf` / `docx` / `pptx` 时有效：<br>`source` 自动/A4<br>`a3` A3<br>`a4` A4<br>`a5` A5<br>`b4` B4<br>`b5` B5<br>`letter` Letter<br>`legal` Legal<br>`tabloid` Tabloid<br>`ledger` Ledger | source |
| pageOrientation | string | 输出页面方向：<br>`source` 不变<br>`landscape` 横向<br>`portrait` 竖向 | source |

#### 输入 EPUB 相关（inputFormat=epub 等）

| **参数** | **类型** | **备注** | **默认值** |
| -------- | -------- | -------- | ---------- |
| epubFontSizePt | integer | 输出字体大小，单位 pt（磅） | 自动 |
| epubLineHeightPercent | integer | 输出行高，单位百分比。例如 `120` 表示行高为字号的 120% | 自动 |
| epubPageSizeCm | string | 自定义页面大小，单位厘米，格式 `宽x高`，例如 `7.2x15.5`。设置后会覆盖 `pageSize` | 自动 |
| epubMarginsPt | string | 页面边距，单位 pt，格式：左 上 右 下，例如 `5 5 5 5` | 自动 |

#### 输入 CAD 文件相关（inputFormat 为 dwg / dxf 等）

| **参数** | **类型** | **备注** | **默认值** |
| -------- | -------- | -------- | ---------- |
| cadIncludeLayers | boolean | 是否生成 Layer 层 | false |
| cadUseDisplaySettings | boolean | 是否按 Display 显示设置导出 | false |
| cadQuality | integer | 输出品质，取值 1–5，越高越好 | 3 |
| cadRemoveEmptyPages | boolean | 是否删除空页 | false |

---

#### 通用输出

| **参数** | **类型** | **备注** | **默认值** |
| -------- | -------- | -------- | ---------- |
| outputFileName | string | 生成文件的文件名 | 随机 |
| callbackUrl | string | 回调 URL，转换结束后会回调该 URL，详细见 [**回调URL**](#callback) | 无 |

#### 输出 PDF 相关（outputFormat=pdf）

| **参数** | **类型** | **备注** | **默认值** |
| -------- | -------- | -------- | ---------- |
| pdfLinearized | boolean | 是否线性化（快速 Web 显示 / 流式显示） | false |
| compressionLevel | string | 压缩级别：<br>`none` 不压缩<br>`low` 低<br>`medium` 中<br>`high` 高 | none |
| pdfFlattenAnnotations | boolean | 是否扁平化（注释合并到 PDF） | false |
| pdfImageOnly | boolean | 是否生成纯图片 PDF | false |
| pageSize | string | 页面大小。源为 Word/Excel/TXT/HTML/Epub、图片时生效：<br>`source` 跟随源文档（无则 A4）；源为图片时：长图保持原图、非长图按 A4 策略<br>`a3` A3<br>`a4` A4<br>`a5` A5<br>`b4` B4<br>`b5` B5<br>`letter` Letter<br>`legal` Legal<br>`tabloid` Tabloid<br>`ledger` Ledger | source |
| pageOrientationAdjustment | string | 统一调整所有页方向：<br>`none` 不调整<br>`portraitClockwise` 竖屏（横屏页顺时针 90°）<br>`portraitCounterclockwise` 竖屏（横屏页逆时针 90°）<br>`landscapeClockwise` 横屏（竖屏页顺时针 90°）<br>`landscapeCounterclockwise` 横屏（竖屏页逆时针 90°） | none |
| pageSplitCount | integer | 将每一页按长边等分为多页，例如试卷分为左右两页。最小为 2 | 不拆分 |
| includePageSizeMetadata | boolean | 是否返回每一页的尺寸信息 | false |
| pdfUserPassword | string | 生成 PDF 的用户密码（打开文件时需要） | 无 |
| pdfOwnerPassword | string | 生成 PDF 的所有者密码（修改文件时需要） | 无 |
| pdfPermissions | string数组 | 有密码时的权限集合，可选值：<br>`print` 打印<br>`copy` 拷贝内容<br>`edit` 编辑 | 无权限 |

#### 输出图片相关（outputFormat=jpg / png）

图片格式由 `outputFormat` 决定。通过 `imageOutputMode` 选择每页一图、长图或动图；动图固定输出 GIF，`outputFormat` 不影响动图格式。

| **参数** | **类型** | **备注** | **默认值** |
| -------- | -------- | -------- | ---------- |
| imageOutputMode | string | 输出模式：<br>`separateImages` 每页一图<br>`longImage` 长图<br>`animatedGif` 动图（GIF） | separateImages |
| imageMaxDimension | integer | `separateImages` 时为每个图最大宽或高，最大 20000；`animatedGif` 时最大 2000 | 自动 |
| longImageWidth | integer | `longImage` 时长图宽度，最大 2000 | 自动 |
| animationFrameDurationSeconds | integer | `animatedGif` 时每帧持续秒数，最小 1 | 1 |
| pageOrientationAdjustment | string | 统一调整所有页方向，取值同输出 PDF 的 `pageOrientationAdjustment` | none |
| grayscale | boolean | 是否输出灰度图 | false |
| pageSplitCount | integer | 将每一页按长边等分为多页，最小为 2 | 不拆分 |
| pageRanges | string | 如果源文件是 PDF，指定转换页码，例如：`1,3,5-7` | 全部页 |

#### 输出 HTML 相关（outputFormat=html）

| **参数** | **类型** | **备注** | **默认值** |
| -------- | -------- | -------- | ---------- |
| includeOutline | boolean | 如果有大纲，是否生成大纲 | false |
| htmlOutputMode | string | HTML 输出模式：<br>`fullDocument` 完整文档<br>`embedded` 嵌入式 HTML（适合放入网页编辑器等场景，如 Word 转 HTML） | fullDocument |

#### 输出 Word/PPT/Excel/Txt/OFD/Markdown 相关（outputFormat 为 docx / pptx / xlsx / txt / ofd / md 等）

| **参数** | **类型** | **备注** | **默认值** |
| -------- | -------- | -------- | ---------- |
| wordIncludeImages | boolean | 转为 Word 时是否保留图片 | true |
| wordLayout | string | 转为 Word 时的布局：<br>`flow` 流式布局<br>`fixed` 绝对布局（位置更准，但不利于流式编辑） | flow |
| wordRemovePageBreaks | boolean | 转为 Word 时是否删除分页符 | false |
| excelSheetMode | string | 转为 Excel 时工作表策略：<br>`auto` 按系统默认（PDF 在特定页数内可合并，否则每页一表；图片默认每图一表）<br>`singleSheet` 合并为一个工作表<br>`sheetPerPage` 每页/每图一个工作表（非 PDF 输入时按系统规则回落） | auto |
| textPreserveLayout | boolean | 转为 Txt 时是否保持原有布局 | true |
| textOutputMode | string | 转为 Txt 时：<br>`singleFile` 所有页单个 txt<br>`filePerPage` 每页一个 txt 并打包为 zip | singleFile |

#### 输出水印相关

| **参数** | **类型** | **备注** | **默认值** |
| -------- | -------- | -------- | ---------- |
| watermarkText | string | 水印文字。输出 PDF 时最多 15 个字符；输出图片或 HTML 时最多 10 个字符 | 无 |
| watermarkFontSizePt | integer | 水印字号，单位 pt | 24 |
| watermarkColor | string | 水印颜色，`#RRGGBB` 格式，必须 7 位 | #000000 |
| watermarkOpacityPercent | integer | 水印不透明度，取值 1–100，越小越透明 | 20 |
| watermarkLayout | string | 水印布局：<br>`center` 文档中央一个水印<br>`tiled` 文档铺满水印 | center |

<a name="langcode"></a>
#### OCR 语言（ocrLanguage）

取值不区分大小写。

| 语言 | ocrLanguage | 语言 | ocrLanguage | 语言 | ocrLanguage |
| ---- | ----------- | ---- | ----------- | ---- | ----------- |
| 简体中文 | zh-CN / zh-Hans | 英文 | en | 法文 | fr |
| 德文 | de | 日文 | ja | 韩文 | ko |
| 繁体中文 | zh-TW / zh-Hant | 意大利文 | it | 西班牙文 | es |
| 葡萄牙文 | pt | 俄文 | ru | 丹麦文 | da |
| 荷兰文 | nl | 芬兰文 | fi | 挪威文 | no |
| 瑞典文 | sv | 土耳其文 | tr | | |


<div style="page-break-before: always"></div>


## 备注：

- 输入文件 URL 方式支持文件最大 *1500M*；Base64 方式最大 *8M*。
- 最大转换时长：*1小时*，超过时间未完成则自动失败。
- 转换完成后，下载链接有效时间：*1小时*。

上述最后2项有延长需求请联系客服：
<img src="http://www.duhuitech.com/images/qr_support.png" alt="客服二维码" width="140" />

---


<a name="callback"></a>
## 回调URL：

**用途：** 客户可以自行部署服务器，系统转换结束后会调用客户提供的回调URL，直接发送转换结果，从而无需再轮询[查询结果](#query)。

在转换请求的 `options` 中传入 `callbackUrl`。当设置了回调URL，转换结束后（无论成功失败），系统都会尝试调用该URL，具体如下：

以POST方式调用该URL，Header头中Content-Type: application/json

Body为JSON格式，内容和[查询结果](#query)的结果相同。例如单文件：

```
{
	"code":10000,
	"msg":"",
	"token":"xxx",
	"result":
	{
		"status":"Done",
		"fileurl":"https://file.duhuitech.com/o/xxx/xxx.docx",
		"filesize":17747,
		"count":1
	}
}
```

文档转图片时同样返回 `fileurls`：

```
{
	"code":10000,
	"msg":"",
	"token":"xxx",
	"result":
	{
		"status":"Done",
		"fileurls":[
			"https://file.duhuitech.com/o/xxx/1.png",
			"https://file.duhuitech.com/o/xxx/2.png"
		],
		"count":2,
		"filesize":120000
	}
}
```

服务端收到该POST后需在10秒内返回HTTP STATUS CODE
200，视为调用成功，否则系统认为回调失败，会再次尝试。规则如下：

系统共计最多会调用3次回调URL，如果第一次失败，则等待3秒后尝试第二次，如果第二次失败，则等待5秒后尝试第三次，如果第三次失败，则不再尝试。

回调URL超时时间10秒。

---


<a name="download302"></a>
## 关于下载转换后的文件需支持302跳转

接口返回的下载地址（如 `fileurl` / `fileurls`）会经 HTTP 302 跳转到实际文件。浏览器会自动跟随。

以下方式默认会跟随跳转，一般无需额外配置：

`wget`、Python `requests` / `urllib`、Node.js `axios` / `got` / `fetch`、Java `OkHttp` / `HttpURLConnection`、Go `net/http`、C# `HttpClient`、PHP `file_get_contents`、Objective-C / Swift `NSURLSession` / `URLSession`（含 Alamofire）

少数默认不跟随，需手动打开：

- `curl`：加 `-L`，如 `curl -L -o out.bin "下载地址"`
- Java `java.net.http.HttpClient`：设置 `.followRedirects(HttpClient.Redirect.NORMAL)`
- PHP `curl` 扩展：设置 `CURLOPT_FOLLOWLOCATION => true`

若只拿到 302 响应、本地没有文件内容，多半是未跟随跳转，按上面说明打开对应选项即可。

---


<a name="alioss"></a>
## 阿里云独有部分：

支持从阿里云OSS内网直接下载文件，目前支持的是上海地区的阿里云OSS内网：

`oss-cn-shanghai-internal.aliyuncs.com`

请求里的文件 URL 包含上述域名则自动支持。

---


<a name="error"></a>
## 错误码表：

返回的code如果是10000，代表成功，其余是失败

| JSON里返回的code | 错误信息       |
| ---------------- | -------------- |
| 40000            | 通用错误       |
| 40001            | 参数错误       |
| 40002            | 参数不符合规范 |


<div style="page-break-before: always"></div>


<a name="sig"></a>
## 附录：阿里签名方式

参考链接：

<https://help.aliyun.com/zh/api-gateway/traditional-api-gateway/use-cases/call-apis>

在调用API商品时，首先您需要了解采用哪种API认证方式，云市场API商品的认证方式主要有以下两种方式。两种方式可同时使用，您可以根据不同情况来选择。

- 简单身份认证（AppCode）

- 签名认证

### 简单身份认证（AppCode）

简单认证（AppCode）调用API，有两种方式，一种是将AppCode放在Header中进行调用，一种是将AppCode放在Query参数中进行调用。

方式一：将AppCode放在Header中

在请求Header中添加一个Authorization参数。

Authorization字段的值的格式为APPCODE ＋ 半角空格 ＋APPCODE值。格式如下：

Authorization:APPCODE AppCode值

示例：

`Authorization:APPCODE <YOUR_APPCODE>`

方式二：将AppCode放在Query中

在请求Query中添加AppCode参数（同时支持appcode , appCode , APPCODE ,
APPCode四种写法）。

AppCode参数的值为AppCode的值。

示例：

`http://www.aliyum.com?AppCode=<YOUR_APPCODE>`

参考链接：<https://help.aliyun.com/zh/api-gateway/traditional-api-gateway/user-guide/call-an-api-operation-by-using-an-appcode>

### 签名认证

比较复杂，推荐用阿里自己的SDK来调用，参考链接：<https://help.aliyun.com/zh/api-gateway/traditional-api-gateway/user-guide/use-digest-authentication-to-call-an-api>

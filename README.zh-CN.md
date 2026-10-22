# Nickspeare

带有来源追溯记录和浏览器创作界面的莎士比亚风格昵称生成器。

[English](README.md) · [在线演示](https://styayur.github.io/Nickspeare/) · [已发布 v1.0.0](https://github.com/styayur/Nickspeare/releases/tag/v1.0.0)

**阶段：Experimental。** Python 与浏览器流程已有自动检查；独立用户的安装、升级与持续使用验证仍待完成。当前源码声明版本为 1.1.0，最新正式发布为 v1.0.0。下列源码示例描述当前源码，不保证旧 wheel 具有相同能力。

![实际运行的浏览器创作界面：生成昵称、生成设置和语料覆盖范围](docs/screenshot.png)

## 功能

- 用莎士比亚文本中的词汇材料生成新昵称，查看人物关联、原文位置、构词选择和历史日期解释。
- 当前证据索引涵盖《亨利四世（上）》《亨利四世（下）》和《亨利五世》的 195 个词，保留来源哈希与 XML 标识。
- 比较排序后的融合词和字符 Markov 候选；带种子的记录可在同一引擎与版本内复现。
- 浏览器本地生成，不需要生成 API 或密钥。可检查四步构词过程、选择候选、分享重放设置并导出 JSON。

证据支持词汇材料的来源，不证明新昵称曾出现在原文中。评分与编辑选择见[方法说明](docs/METHODOLOGY.md)。

## 安装 / 快速开始

### 浏览器

打开[在线演示](https://styayur.github.io/Nickspeare/)，点击 **FORGE NAME**；复制昵称或导出记录前，可查看来源与构词步骤。要本地运行同一静态界面，克隆仓库后在根目录执行：

```sh
git clone https://github.com/styayur/Nickspeare.git
cd Nickspeare
python -m http.server 8765 --directory docs
```

打开 `http://localhost:8765`。Python 只提供文件服务，昵称生成发生在浏览器内。仓库已包含证据索引，日常生成无需下载完整语料。

浏览器仅在内存中保留当前结果，没有保存历史的存储。需要留存时请导出 JSON；重放链接会在 URL 中暴露规则、样式、后缀、种子、倾向值与所选候选编号，不是私有备份。导出的 JSON 是记录，不是可导入的项目文件；重放依赖浏览器引擎与版本。

### 从源码安装 Python 包

使用 Python 3.9 及以上，没有第三方运行时依赖；建议使用虚拟环境。

```sh
git clone https://github.com/styayur/Nickspeare.git
cd Nickspeare
python -m pip install -e .
python -m nickspeare generate -n 10 --seed 42
python -m nickspeare generate -n 5 --rule rogue_to_king --year-theme agincourt --royal-affinity 0.85 --json
python -m nickspeare generate -n 5 --rule markov_coin --suffix none --seed 42
```

Python 提供 `rogue_to_king`、`quote_splice`、`archaic_coinage`、`markov_coin` 和 `markov_epithet`，浏览器提供前四种。`--suffix none` 不附加年份，`number` 添加无历史含义的装饰数字，`both` 在历史与数字后缀之间选择。样式及其他参数见 `python -m nickspeare generate --help`。

```python
from nickspeare import NicknameGenerator

engine = NicknameGenerator(seed=42, royal_affinity=0.85)
name = engine.generate_one(rule="rogue_to_king", year_theme="agincourt")
print(name.variant)
print(name.as_dict()["provenance"])
```

如需固定的正式发布包，请下载 [v1.0.0](https://github.com/styayur/Nickspeare/releases/tag/v1.0.0) 附带的 wheel，再安装该本地文件。本说明不表示 PyPI 可用，也不表示 1.1.0 已发布。语料重建及可选的 R/RStudio 分析见[开发说明](docs/DEVELOPMENT.md)。

在下载目录运行，并使用与源码可编辑安装分开的虚拟环境：

```sh
python -m pip install ./nickspeare-1.0.0-py3-none-any.whl
```

## 测试 / CI / 平台支持

[![Verify](https://github.com/styayur/Nickspeare/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/styayur/Nickspeare/actions/workflows/ci.yml)

在仓库根目录使用 Python 3.9 及以上、Node.js 22（CI 版本；清单允许 Node 20 及以上）：

```sh
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
npm test
python -m build
```

浏览器集成检查需先运行 `python -m playwright install chromium`。按上节启动 `docs` 服务后，在另一个终端的仓库根目录运行 `python scripts/check_browser.py`。

[Verify 工作流](.github/workflows/ci.yml)在 Ubuntu 上检查 Python 3.9/3.12/3.14 与无头 Chromium，覆盖重放、导出、剪贴板、构词步骤、响应式布局和加载失败。[CodeForge regression](.github/workflows/codeforge-regression.yml)是独立开发门禁。这些检查不代表认证所有浏览器与操作系统；GitHub Pages 从 `main:/docs` 提供网页。

## 已知限制

- 昵称是新造词，不是莎士比亚原句或历史语音重建。人物分组属于编辑判断，低频词关联具有不确定性。
- Python 与浏览器的随机数生成器和变换规则不同；种子只在同一引擎与版本内复现，不能跨引擎对齐。
- 来源索引限于三部剧作、195 个词。补充训练语料不会自动扩充已提交的证据索引。
- R 是可选分析工具，其探索性输出不是正式证据索引。独立用户安装、升级与持续使用验收尚未完成。

## 路线图

当前源码已有昵称生成与逐项来源追溯。下一步是经过审核的语料扩充与更清晰的证据展示；更广泛的计算人文学比较仍属未来实验。参阅[语料验收流程](docs/corpus-extension.md)。不计划提供缺乏依据的生成或商业命名服务。

## 贡献

阅读 [CONTRIBUTING.md](CONTRIBUTING.md)和[开发说明](docs/DEVELOPMENT.md)。问题报告应包含引擎与版本、种子、规则、后缀和导出记录。可复现问题提交 [Issue](https://github.com/styayur/Nickspeare/issues)，漏洞按 [SECURITY.md](SECURITY.md) 报告。新增语料证据需要审核哈希和署名。

## 许可证

代码采用 [AGPL-3.0-or-later](LICENSE)。缓存的 Folger 版本及其衍生索引保留 **CC BY-NC 3.0** 署名与非商业限制，代码许可证不重新许可这些数据。版本署名、哈希和可选语料见[来源与权利](DATA_SOURCES.md)。感谢 Folger Shakespeare Library 及编辑和编码人员；Markov 方法参考也记录在该文档中。

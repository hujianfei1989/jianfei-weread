# jianfei-weread

把你的微信读书书架、划线、想法和阅读分析同步到本地，生成一个可以自己长期使用的阅读仪表盘。

这个项目适合你在这些场景里使用：

- 想把微信读书里的笔记长期备份到自己电脑
- 想按书、年份、作者、关键词复盘阅读记录
- 想把一本书的划线和想法做成幻灯片
- 想把金句生成漂亮图片，直接复制到微信、飞书或文档
- 想把自己的微信读书数据做成本地 HTML 页面，不依赖在线服务

整个流程只需要做 4 件事：

1. 下载这个项目
2. 安装一个本地阅读仪表盘
3. 填入你自己的 WeRead API key
4. 同步并打开页面

## 第一步：确认你准备好了

你需要：

- 一台可以运行 Python 的电脑，macOS / Linux / Windows WSL 都可以
- Python 3.10 或更高版本
- 一个微信读书 WeRead API key，格式通常是 `wrk-...`
- 可以访问微信读书接口的网络环境

检查 Python：

```bash
python3 --version
```

如果能看到类似 `Python 3.10.x`、`Python 3.11.x`、`Python 3.12.x`，就可以继续。

## 第二步：下载项目

```bash
git clone https://github.com/hujianfei1989/jianfei-weread.git
cd jianfei-weread
```

这个仓库本身是一个模板和 Skill，不会包含任何人的个人阅读数据。

## 第三步：安装到你的本地目录

建议把真正使用的阅读仪表盘安装到 `Documents` 下面：

```bash
python3 scripts/install.py \
  --target "$HOME/Documents/jianfei-weread" \
  --title "我的微信读书" \
  --keyword "专题"
```

安装完成后，会生成这个目录：

```text
$HOME/Documents/jianfei-weread
```

参数可以按你的用途调整：

- `--target`：本地仪表盘保存在哪里
- `--title`：页面左上角显示什么名字
- `--keyword`：专题页用什么关键词筛选书籍，比如作者名、品牌名、主题词

示例：

```bash
python3 scripts/install.py \
  --target "$HOME/Documents/my-weread" \
  --title "我的阅读库" \
  --keyword "时间管理"
```

## 第四步：添加你的微信读书账号

运行：

```bash
python3 scripts/accounts.py --target "$HOME/Documents/jianfei-weread" set default
```

终端会提示你输入 WeRead API key。输入后，它会保存在：

```text
$HOME/Documents/jianfei-weread/.weread-accounts.json
```

这个文件只在你的电脑上，不会被提交到 Git。

查看当前账号：

```bash
python3 scripts/accounts.py --target "$HOME/Documents/jianfei-weread" list
```

如果你有多个账号，也可以继续添加：

```bash
python3 scripts/accounts.py --target "$HOME/Documents/jianfei-weread" set work
python3 scripts/accounts.py --target "$HOME/Documents/jianfei-weread" switch work
```

## 第五步：同步微信读书数据

```bash
python3 scripts/sync.py --target "$HOME/Documents/jianfei-weread"
```

同步会拉取：

- 书架
- 书籍元数据
- 划线
- 想法
- 推荐书籍
- 幻灯片数据

同步完成后，本地目录里会出现：

```text
weread-export/
weread-obsidian.html
```

`weread-export/` 是你的私人阅读数据，不要发给别人，也不要提交到公开仓库。

## 第六步：打开页面

启动本地服务：

```bash
python3 scripts/serve.py --target "$HOME/Documents/jianfei-weread"
```

终端会输出类似：

```text
Dashboard: http://127.0.0.1:18767/weread-obsidian.html
```

复制这个地址到浏览器打开。

页面打开后，你可以看到：

- 书架页：所有同步下来的书
- 专题页：按 `--keyword` 筛出的书
- 分析页：按年份、月份、作者、书籍查看阅读情况
- 推荐页：基于已读书籍展示相似书
- 设置页：管理账号、主题、字体、黑名单、过滤条件

## 之后怎么更新数据

如果你看了新书，或者新增了划线和想法，有两种方式同步。

方式一：命令行同步：

```bash
python3 scripts/sync.py --target "$HOME/Documents/jianfei-weread"
```

方式二：页面里点击一键同步。

页面一键同步需要保持本地服务运行：

```bash
python3 scripts/serve.py --target "$HOME/Documents/jianfei-weread"
```

## 页面里可以怎么用

### 看书架

进入：

```text
#books
```

你可以搜索书名 / 作者，也可以按年份筛选。

### 看一本书的内容

点击一本书后，可以查看：

- 原文划线
- 绑定在划线下面的想法
- 章节结构
- 书籍元数据
- 推荐相似书

内容视图支持卡片和列表切换。

### 生成金句图片

在卡片右上角点击图片按钮，可以把这条划线生成一张金句图片。

如果这条划线下面绑定了想法，图片里也会一起排版。

### 打开幻灯片

在书籍详情页点击“完整幻灯片”，可以把一本书的内容按幻灯片方式展示，适合复盘和演示。

### 看分析报告

进入：

```text
#report
```

你可以按年份筛选，也可以点击月份、书籍和作者跳转到对应内容。

### 管理设置

进入：

```text
#settings
```

可以设置：

- 亮色 / 暗色 / 跟随系统
- 字体大小
- 多账号
- 黑名单书籍
- 少于多少条笔记的书不显示

## 隐私和安全

这个仓库不会收集或上传你的数据。

敏感信息只保存在你的本机：

```text
.weread-accounts.json
weread-export/
```

这些文件已经在 `.gitignore` 里排除：

```text
.weread-accounts.json
weread-export/
__pycache__/
*.pyc
*.key
*.token
```

不要把安装后的本地目录直接发给别人。要分享项目，请分享这个 GitHub 仓库，而不是你的 `Documents/jianfei-weread` 数据目录。

## 常见问题

### 我应该运行仓库里的 HTML，还是 Documents 里的 HTML？

日常使用请打开安装后的文件：

```text
$HOME/Documents/jianfei-weread/weread-obsidian.html
```

仓库里的 `assets/project-template/weread-obsidian.html` 是模板，不包含你的数据。

### 为什么页面一键同步没反应？

确认本地服务正在运行：

```bash
python3 scripts/serve.py --target "$HOME/Documents/jianfei-weread"
```

一键同步会调用：

```text
http://127.0.0.1:18766/sync
```

### 可以只离线打开 HTML 吗？

可以查看已经同步的数据，但账号管理和一键同步需要本地服务。

### API key 会被写进 HTML 吗？

不会。API key 只保存在 `.weread-accounts.json`。

### 可以给其他人用吗？

可以。其他人克隆这个仓库后，按上面的步骤填自己的 API key，同步自己的数据。

## 给 Agent / Codex 使用

这个仓库也是一个 Skill。你可以把整个目录放到自己的 skills 目录，例如：

```text
~/.agent/skills/jianfei-weread
```

之后可以直接对 Agent 说：

```text
帮我安装 jianfei-weread
帮我同步微信读书
帮我生成阅读分析
帮我检查微信读书页面
```

Agent 会根据 `SKILL.md` 里的流程执行。

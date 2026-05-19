# jianfei-weread

`jianfei-weread` 是一个把微信读书数据同步到本地的可复用 Skill / 本地仪表盘模板。

它会用你自己的 WeRead API key，把书架、书籍元数据、划线、想法、推荐书籍和幻灯片同步到本地，然后生成一个可以直接打开的 HTML 页面，用来复盘阅读、检索笔记、生成金句图片和做演示。

## 能做什么

- 同步微信读书书架、划线和想法
- 展示完整书架、按年份筛选阅读记录
- 查看每本书的原文划线和绑定想法
- 生成阅读分析报告
- 为每本书生成 HTML 幻灯片入口
- 生成可复制的金句图片
- 管理多个 WeRead API key 账号
- 设置亮色、暗色、跟随系统、字体大小
- 黑名单和最少笔记数过滤
- 按关键词生成专题书籍页
- 展示相似 / 推荐书籍

## 你需要准备什么

- macOS / Linux / Windows WSL 均可
- Python 3.10+
- 一个 WeRead API key，格式通常类似 `wrk-...`
- 能访问微信读书 API 的网络环境

API key 只会保存在你本机项目目录的 `.weread-accounts.json`，不会写进 HTML，也不会提交到 Git。

## 安装

克隆仓库：

```bash
git clone https://github.com/hujianfei1989/jianfei-weread.git
cd jianfei-weread
```

安装一个干净的本地项目：

```bash
python3 scripts/install.py \
  --target "$HOME/Documents/jianfei-weread" \
  --title "我的微信读书" \
  --keyword "专题"
```

参数说明：

- `--target`：生成的本地项目目录
- `--title`：页面标题
- `--keyword`：专题筛选关键词，比如作者名、品牌名、主题词

## 配置账号

添加默认账号：

```bash
python3 scripts/accounts.py --target "$HOME/Documents/jianfei-weread" set default
```

命令会提示你输入 WeRead API key。

查看账号：

```bash
python3 scripts/accounts.py --target "$HOME/Documents/jianfei-weread" list
```

切换账号：

```bash
python3 scripts/accounts.py --target "$HOME/Documents/jianfei-weread" switch default
```

## 同步数据

```bash
python3 scripts/sync.py --target "$HOME/Documents/jianfei-weread"
```

同步完成后，会在目标目录生成：

```text
weread-export/
weread-obsidian.html
```

`weread-export/` 是你的个人阅读数据，不要提交或分享。

## 打开页面

启动本地服务：

```bash
python3 scripts/serve.py --target "$HOME/Documents/jianfei-weread"
```

终端会输出类似：

```text
Dashboard: http://127.0.0.1:18767/weread-obsidian.html
```

打开这个地址即可使用页面。

如果你只是想离线查看，也可以直接打开：

```text
$HOME/Documents/jianfei-weread/weread-obsidian.html
```

但一键同步、账号管理等功能需要本地服务运行。

## 页面使用

常用入口：

- `#books`：书架
- `#report`：分析报告
- `#recommend`：推荐书籍
- `#settings`：设置和账号管理

在书籍详情页可以：

- 查看划线和想法
- 在卡片 / 列表视图之间切换
- 生成金句图片
- 打开完整幻灯片
- 跳转到微信读书继续阅读

## 隐私说明

这个仓库只包含模板和脚本，不包含任何个人阅读数据。

以下文件不应该提交到 Git：

```text
.weread-accounts.json
weread-export/
__pycache__/
*.pyc
*.key
*.token
```

项目自带 `.gitignore` 已经排除了这些内容。

## 作为 Skill 使用

这个仓库本身也是一个 Codex / Agent Skill。可以把整个目录放到你的 skills 目录中，例如：

```text
~/.agent/skills/jianfei-weread
```

之后当你让 agent “同步微信读书”“生成阅读分析”“安装 jianfei-weread”时，它可以按 `SKILL.md` 中的流程执行。

## 常见问题

### GitHub 页面提示 Add a README 是什么？

如果仓库没有 `README.md`，GitHub 会显示 `Add a README` 提示。现在本项目已经包含 README。

### 为什么同步按钮没反应？

确认本地服务正在运行：

```bash
python3 scripts/serve.py --target "$HOME/Documents/jianfei-weread"
```

页面的一键同步会调用：

```text
http://127.0.0.1:18766/sync
```

### API key 会上传吗？

不会。API key 只存在本地 `.weread-accounts.json`，该文件已被 `.gitignore` 排除。

### 可以给别人用吗？

可以。别人克隆仓库后，用自己的 API key 同步自己的数据即可。

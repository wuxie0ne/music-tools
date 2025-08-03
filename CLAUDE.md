# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中操作代码时提供指导。

## Response Language

**除非有特殊说明，请用中文回答。** (Unless otherwise specified, please respond in Chinese.)

## 命令

### 运行

项目已重构为支持 uv 工具安装的结构。

使用 uv 工具安装项目：

```
cd /home/alex/src/music-tools
uv sync
uv tool install
```

安装后，可通过以下命令运行：

- 交互模式：
```
music-tools
```

- 命令模式：
```
# 搜索歌曲并保存到 playlist.jsonl
music-tools search "王力宏"

# 下载 playlist.jsonl 中的所有歌曲
music-tools execute
```

### 运行测试

没有专用的测试文件或脚本。`netease_api.py` 文件包含一个 `__main__` 代码块，可用于测试 API 功能：

```
cd /home/alex/src/music-tools
python netease_api.py "好心分手"
```

### Linting

没有专用的 linting 配置（例如，没有 .flake8、.pylintrc 或 ruff.toml）。

## 架构

代码库由两个主要 Python 模块组成：

1. `main.py`：主要的应用程序入口点。负责：
   - 使用 `argparse` 解析命令行参数
   - 使用 `rich` 提供交互式搜索和选择歌曲的控制台界面
   - 两种命令模式：`search`（查找歌曲并保存到文件）和 `execute`（从文件下载歌曲）
   - 使用 `requests` 和 `rich` 下载歌曲并显示进度条
   - 使用 `mutagen` 为下载的 `.mp3` 和 `.flac` 文件添加元数据（标题、艺术家、专辑、封面、歌词）

2. `netease_api.py`：一个封装网易云音乐 API 的库模块。提供以下功能：
   - `search_music(keyword, page, limit)`：按关键词搜索歌曲
   - `get_music_details(song_id, quality)`：获取特定歌曲的下载信息（带重试逻辑）
   - `get_lyrics(song_id)`：获取特定歌曲的歌词（带重试逻辑）

这两个模块在 `main.py` 中被导入和使用：

- `main.py` 在第 19 行从 `netease_api.py` 导入 `search_music`、`get_music_details` 和 `get_lyrics`

应用程序遵循一个两步工作流来处理批量任务：

1. 使用 `search` 命令查找歌曲并生成 `playlist.jsonl` 文件
2. 使用 `execute` 命令下载播放列表文件中列出的所有歌曲

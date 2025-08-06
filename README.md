# Music Tools - 终端音乐中心

这是一个功能丰富的终端音乐应用，基于 Python 和 [Textual](https://textual.textualize.io/) 构建。它将您的终端变成一个集本地音乐管理、在线音乐发现和播放于一体的音乐中心。

![Screenshot Placeholder](https://via.placeholder.com/800x400.png?text=在此处替换为应用截图)

*（建议：运行应用并截图替换上面的占位符）*

## 主要功能

- **现代化的终端 UI**：基于 Textual 构建，提供流畅、美观、响应式的用户界面。
- **本地音乐库**:
    - 自动扫描并加载您 `~/Music` 目录下的本地音乐文件 (`.mp3`, `.flac`)。
    - 使用 `mutagen` 读取并显示歌曲的元数据（标题、艺术家、专辑）。
- **在线音乐发现**:
    - 集成网易云音乐 API，可在线搜索歌曲。
    - 直接从搜索结果中试听或下载歌曲。
- **集成播放器**:
    - 使用 `ffplay` (需预先安装 FFmpeg) 作为后端，播放在线和本地歌曲。
    - 在界面底部提供实时播放进度条。
- **多种播放模式**:
    - 支持顺序播放、单曲循环和随机播放三种模式，并实时显示当前模式。
- **实时歌词显示**:
    - 在播放在线歌曲时，自动获取并逐行显示歌词。
- **下载管理**:
    - 从在线搜索结果中下载歌曲到您的 `~/Music` 目录。
    - 自动将封面、歌词等元数据嵌入下载的音乐文件中。
- **安全删除**:
    - 提供将本地音乐文件移动到回收站 (`~/.local/share/music-tools/trash`) 的功能，防止误删。

## 安装与运行

### 1. 前置依赖

- **Python 3.8+**
- **uv**: 推荐使用 `uv` 进行快速的依赖管理。如果尚未安装，请参考 [uv 安装指南](https://github.com/astral-sh/uv)。
- **FFmpeg**: 播放功能依赖 `ffplay`。请确保您已经安装了 FFmpeg。
    - 在 macOS 上: `brew install ffmpeg`
    - 在 Debian/Ubuntu 上: `sudo apt update && sudo apt install ffmpeg`
    - 在 Windows 上: 可通过 [winget](https://winstall.app/apps/Gyan.FFmpeg) 或 [Scoop](https://scoop.sh/) 安装。

### 2. 安装项目

克隆本仓库，然后使用 `uv` 安装依赖。

```bash
git clone https://github.com/your-username/music-tools.git
cd music-tools

# 安装项目依赖
uv sync

# (可选) 如果您需要运行测试或进行开发
uv pip install -e ".[test]"
```

### 3. 运行应用

直接运行以下命令启动 TUI 应用：

```bash
music-tools
```

## 使用说明

应用启动后，您可以使用鼠标或键盘进行导航。

### 主要快捷键

| 按键     | 功能                                             |
| -------- | ------------------------------------------------ |
| `q`      | 退出应用                                         |
| `/`      | 切换到 **本地搜索** 模式并聚焦输入框             |
| `?`      | 切换到 **在线搜索** 模式并聚焦输入框             |
| `escape` | 清空搜索框，并切换回本地音乐库视图               |
| `enter`  | 播放选中的歌曲                                   |
| `space`  | 暂停 / 继续播放                                |
| `l` / `→`| 快进 5 秒                                      |
| `h` / `←`| 快退 5 秒                                      |
| `n`      | 下一首                                           |
| `p`      | 上一首                                           |
| `c`      | 切换显示/隐藏歌词                              |
| `f1`     | 显示此帮助菜单                                   |
| `m`      | 切换播放模式 (顺序 -> 单曲循环 -> 随机)          |
| `d`      | **在线模式下**: 下载选中歌曲<br>**本地模式下**: 切换亮/暗主题 |
| `x`      | **本地模式下**: 将选中的歌曲移动到回收站         |
| `j` / `↓`| 在歌曲列表中向下导航                           |
| `k` / `↑`| 在歌曲列表中向上导航                           |


## 开发与测试

本项目使用 `ruff` 进行代码规范检查和格式化，使用 `pytest` 进行单元测试。

### 格式化与 Linting

```bash
# 格式化代码
uv run ruff format .

# 检查并修复 Linting 问题
uv run ruff check --fix .
```

### 运行测试

```bash
# 运行所有单元测试
uv run pytest
```

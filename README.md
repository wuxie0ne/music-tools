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
- **下载管理**:
    - 从在线搜索结果中下载歌曲。
    - 自动将封面、歌词等元数据嵌入下载的音乐文件中。
- **播放列表管理**:
    - 创建和管理多个播放列表。
    - 将本地或在线歌曲添加到任何播放列表。
    - 播放列表会自动保存在 `~/.config/music-tools/` 目录下。

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

# (可选) 如果您需要运行测试
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

- **通用**:
    - `d`: 切换深色/浅色模式。
    - `q`: 退出应用。
    - `s`: 跳转到在线搜索界面。
    - `space`: 播放/暂停 (当前实现为停止)。
    - 方向键: 在表格和左侧导航树中移动。
- **在任何歌曲列表上**:
    - `enter`: 播放选中的歌曲。
    - `a`: 将选中的歌曲添加到播放列表。
- **在“搜索”界面**:
    - `d`: 下载选中的歌曲。
- **在“播放列表”界面**:
    - `delete`: 将选中的歌曲从当前播放列表中移除。

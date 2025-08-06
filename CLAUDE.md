# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中操作代码时提供指导。

## Response Language

**除非有特殊说明，请用中文回答。** (Unless otherwise specified, please respond in Chinese.)

## 命令

### 环境与安装

项目使用 `uv`进行依赖管理。

1. **同步依赖**:

    ```bash
    uv sync
    ```

2. **安装测试依赖 (可选)**:

    ```bash
    uv pip install -e ".[test]"
    ```

### 运行应用

项目已重构为一个基于 `Textual` 的全功能终端 UI 应用。旧的命令行模式 (`search`, `execute`) 已被移除。

通过以下命令启动应用：

```bash
music-tools
```

### 运行测试

项目现在使用 `pytest` 进行单元测试。

通过以下命令运行所有测试：

```bash
uv run pytest
```

### 代码规范

项目使用 `ruff` 进行代码格式化和 Linting，使用 `black` 作为备用格式化工具。

1.  **格式化代码**:

    ```bash
    uv run ruff format .
    ```

2.  **检查与修复 Linting 问题**:

    ```bash
    uv run ruff check --fix .
    ```

- 你较大的修改和调整，都应该最后使用 uv run ruff 进行检查和格式化

## TUI 交互快捷键

- **通用**:
  - `d`: 切换深色/浅色模式
  - `q`: 退出应用
  - `s`: 跳转到在线搜索界面
  - `space`: 播放/暂停 (当前实现为停止)
  - 方向键: 在表格和列表中导航
- **歌曲列表 (本地曲库, 播放列表, 搜索结果)**:
  - `enter`: 播放选中的歌曲
  - `a`: 将选中的歌曲添加到播放列表
- **搜索界面**:
  - `d`: 下载选中的歌曲
- **播放列表界面**:
  - `delete`: 将选中的歌曲从当前播放列表中移除

## 架构

应用已重构为模块化的结构，核心是一个基于 `Textual` 的 TUI 应用。

- **`src/music_tools/main.py`**: 应用主入口。负责：
  - 定义 `MusicApp(App)`，这是 `Textual` 应用的核心。
  - 构建主界面布局，包括导航树、歌曲表格和底部的播放状态栏。
  - 管理 `Player` 和 `PlaylistManager` 的实例。
  - 处理全局快捷键和导航逻辑。
  - 管理一个每秒更新的定时器，用于刷新播放进度条。

- **`src/music_tools/player/player.py`**: 封装了对外部播放器 `ffplay` 的调用。
  - 通过 `subprocess.Popen` 异步播放音频。
  - 跟踪当前播放状态和进度。

- **`src/music_tools/library/local.py`**: 负责扫描和解析本地音乐文件。
  - 使用 `mutagen` 读取 `.mp3` 和 `.flac` 文件的元数据。

- **`src/music_tools/api/netease.py`**: 封装了所有与网易云音乐 API 的交互。

- **`src/music_tools/playlist/manager.py`**: 负责播放列表的管理。
  - 在 `~/.config/music-tools/playlists.json` 文件中加载和保存播放列表。
  - 提供创建、添加、删除等操作。

- **`src/music_tools/tui/`**: 包含所有与 `Textual` UI 相关的模块。
  - **`app.css`**: 定义应用的静态样式。
  - **`screens/`**: 存放不同的应用界面 (`Screen`)。
    - `search.py`: 在线搜索界面。
    - `playlist.py`: 单个播放列表的展示和管理界面。
    - `add_to_playlist.py`: 添加歌曲到播放列表的模态对话框。
  - **`actions.py`**: 存放通用的 UI 动作，如 `play_song`，以减少代码重复。

- **`tests/`**: 存放所有 `pytest` 单元测试。
  - 为 `api`, `library`, `player`, `playlist` 等核心模块提供了独立的测试文件。
  - 广泛使用 `pytest-mock` 来模拟外部依赖，如网络请求和文件系统操作。

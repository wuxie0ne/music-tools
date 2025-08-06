from textual.screen import ModalScreen
from textual.widgets import DataTable, Static
from textual.app import ComposeResult
from textual.containers import Vertical

class HelpScreen(ModalScreen):
    """A modal screen that displays a help table of key bindings."""

    def compose(self) -> ComposeResult:
        with Vertical(id="help-container"):
            yield Static("[b]快捷键帮助[/b]", classes="help-title")
            yield DataTable(classes="help-table")
            yield Static("按 [b]Escape[/b] 关闭", classes="help-footer")

    def on_mount(self) -> None:
        """Set up the help table."""
        table = self.query_one(DataTable)
        table.add_columns("按键", "功能")
        
        bindings = [
            ("q", "退出应用"),
            ("space", "暂停 / 继续播放"),
            ("h / ←", "快退 5 秒"),
            ("l / →", "快进 5 秒"),
            ("n", "下一首"),
            ("p", "上一首"),
            ("m", "切换播放模式 (顺序/循环/随机)"),
            ("c", "切换显示/隐藏歌词"),
            ("d", "下载 (在线模式) / 切换主题 (本地模式)"),
            ("x", "删除本地歌曲 (移动到回收站)"),
            ("/", "切换到本地搜索"),
            ("?", "切换到在线搜索"),
            ("enter", "播放选中歌曲"),
            ("escape", "清空搜索 / 关闭此菜单"),
            ("j / ↓", "向下导航"),
            ("k / ↑", "向上导航"),
            ("f1", "显示/隐藏此帮助菜单"),
        ]
        
        table.add_rows(bindings)

    def on_key(self, event) -> None:
        """Pop the screen when escape is pressed."""
        if event.key == "escape":
            self.app.pop_screen()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
一个高效、稳定且功能完备的异步音乐下载器。

本程序通过第三方API下载网易云音乐的歌曲，并自动完成以下任务：
1. 根据歌曲ID，获取高品质音乐文件（如FLAC）、封面和歌词。
2. 使用 `asyncio` 实现高并发下载，显著缩短批量下载时间。
3. 通过 `asyncio.Semaphore` 控制并发量，避免对API服务器造成过大压力。
4. 实现了智能的 `TokenManager`，集中管理和复用API访问令牌，处理令牌失效问题。
5. 集成了基于 `requests` 和 `urllib3` 的自动重试机制，能从容应对网络波动和服务器临时错误。
6. 使用 `mutagen` 库，将歌曲名、歌手、专辑、封面、歌词等元数据嵌入到音频文件中。
7. 提供详细的日志记录，便于追踪程序运行状态和排查问题。

依赖库:
- requests: 用于执行HTTP请求。
- mutagen: 用于读写音频文件的元数据。

使用方法:
1. 确保已安装 `requests` 和 `mutagen` (`pip install requests mutagen`)。
2. 修改下方的 `DOWN_DIR` 配置为你希望保存音乐的目录。
3. 在 `main` 函数中提供需要下载的音乐ID列表。
4. 运行此脚本 (`python your_script_name.py`)。
"""

import os
import asyncio
from datetime import datetime
import requests
import re
import hashlib
import json
import logging
from typing import Dict, Any, Tuple

# 新增导入，用于实现重试逻辑
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 导入 mutagen 相关模块
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, USLT


# --- 1. 全局配置 ---

# 日志配置
logfile = f"log_{datetime.now():%Y%m%d}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(logfile, encoding="utf-8")],
)

# 下载目录配置
DOWN_DIR = "Music"
if not os.path.exists(DOWN_DIR):
    os.makedirs(DOWN_DIR)

# API 地址配置
TOKEN_API_URL = "https://api.toubiec.cn/api/get-token.php"
MUSIC_API_URL = "https://api.toubiec.cn/api/music_v1.php"

# 并发控制：设置最大同时运行的任务数量
MAX_CONCURRENCY = 5


# --- 2. 核心辅助类：Token管理器 ---


class TokenManager:
    """
    一个用于集中管理和刷新API Token的异步安全类。

    该类确保在整个应用生命周期中，Token只在需要时被获取一次，
    并能在失效后安全地刷新，避免了多个并发任务同时请求新Token的竞态条件。
    """

    def __init__(self, session: requests.Session):
        """
        初始化TokenManager。

        Args:
            session (requests.Session): 用于发起网络请求的共享Session对象。
        """
        self._session = session
        self._token: str | None = None
        self._lock = asyncio.Lock()  # 异步锁，用于保护Token的获取和刷新过程

    async def _fetch_new_token(self) -> str | None:
        """
        在后台线程中执行实际的Token获取请求。这是一个阻塞操作。
        """
        try:
            # 使用to_thread在工作线程中运行阻塞的requests调用，避免阻塞事件循环
            req = await asyncio.to_thread(self._session.post, TOKEN_API_URL)
            req.raise_for_status()  # 如果HTTP状态码是4xx或5xx，则抛出异常
            token = req.json()["token"]
            logging.info("成功获取到一个新的共享令牌。")
            return token
        except (
            requests.exceptions.RequestException,
            KeyError,
            json.JSONDecodeError,
        ) as e:
            logging.error(f"从API获取新令牌失败: {e}")
            return None

    async def get_token(self) -> str | None:
        """
        获取一个有效的Token。如果已有缓存则直接返回，否则加锁并获取新Token。

        采用双重检查锁定模式，以提高已获取Token后的访问效率。
        """
        if self._token:
            return self._token

        async with self._lock:
            # 再次检查，防止在等待锁的过程中，已有其他协程获取了Token
            if self._token:
                return self._token
            self._token = await self._fetch_new_token()
            return self._token

    async def invalidate_token(self):
        """
        将当前缓存的Token标记为无效。

        当外部调用发现Token失效时，应调用此方法。
        此操作同样在锁的保护下进行。
        """
        async with self._lock:
            if self._token:
                logging.warning("共享令牌已被标记为失效，将在下次请求时刷新。")
                self._token = None


# --- 3. 同步工作函数 (阻塞操作) ---


def get_wyy_source(
    session: requests.Session, token: str, music_id: int
) -> Dict[str, Any] | None:
    """
    使用给定的Token获取指定音乐ID的源信息。

    Args:
        session (requests.Session): 用于请求的Session对象。
        token (str): 访问API所需的令牌。
        music_id (int): 网易云音乐的歌曲ID。

    Returns:
        Dict[str, Any] | None: 成功时返回API响应的JSON数据，失败时返回None。
    """
    t_headers = {"Authorization": f"Bearer {token}"}
    data = {
        "url": f"https://music.163.com/song?id={music_id}",
        "level": "hires",  # 请求高品质音源
        "type": "song",
        "token": hashlib.md5(token.encode("utf-8")).hexdigest(),
    }
    try:
        r = session.post(url=MUSIC_API_URL, json=data, headers=t_headers)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        # 错误日志由requests的重试机制处理，这里只记录最终失败
        logging.error(f"获取音乐ID {music_id} 源信息最终失败: {e}")
    except json.JSONDecodeError:
        logging.error(f"解析音乐ID {music_id} 的响应时出错，内容非JSON: {r.text}")
    return None


def save_song_files(session: requests.Session, song_data: Dict[str, Any]):
    """
    根据歌曲数据，下载封面、歌曲文件，并嵌入元数据。
    这是一个复合的阻塞函数，包含多个I/O操作。

    Args:
        session (requests.Session): 用于下载文件的Session对象。
        song_data (Dict[str, Any]): 包含歌曲所有信息的字典。
    """
    song_info = song_data.get("song_info", {})
    artist = song_info.get("artist", "未知歌手").replace("/", "&")
    name = song_info.get("name", "未知歌曲").replace("/", "&")
    file_prefix = f"{name} - {artist}"

    # 1. 下载封面
    cover_data, cover_mime_type = None, None
    if cover_url := song_info.get("cover"):
        try:
            cover_res = session.get(cover_url)
            cover_res.raise_for_status()
            cover_data = cover_res.content
            cover_ext = os.path.splitext(cover_url.split("?")[0])[-1].lower() or ".jpg"
            cover_mime_type = (
                "image/jpeg" if cover_ext in [".jpg", ".jpeg"] else "image/png"
            )
        except requests.exceptions.RequestException as e:
            logging.error(f"下载封面时最终失败 ({name}): {e}")

    # 2. 提取歌词
    lyrics_text = song_data.get("lrc", {}).get("lyric")

    # 3. 下载音乐文件并嵌入元数据
    if url_info := song_data.get("url_info", {}):
        if music_url := url_info.get("url"):
            music_type = url_info.get("type", "mp3")
            music_path = os.path.join(DOWN_DIR, f"{file_prefix}.{music_type}")
            try:
                # 使用 stream=True 以流式下载大文件，避免内存占用过高
                with session.get(music_url, stream=True) as music_res:
                    music_res.raise_for_status()
                    with open(music_path, "wb") as f:
                        for chunk in music_res.iter_content(chunk_size=8192):
                            f.write(chunk)
                logging.info(f"音乐文件已保存: {music_path}")

                # 4. 文件下载成功后，添加元数据
                add_metadata_to_song(
                    music_path, song_info, cover_data, cover_mime_type, lyrics_text
                )
            except requests.exceptions.RequestException as e:
                logging.error(f"下载音乐文件时最终失败 ({name}): {e}")
            except IOError as e:
                logging.error(f"写入音乐文件时出错 ({name}): {e}")


def add_metadata_to_song(
    music_path: str,
    song_info: Dict[str, Any],
    cover_data: bytes | None,
    cover_mime_type: str | None,
    lyrics_text: str | None,
):
    """
    使用mutagen为下载好的音频文件添加元数据（封面、标题、歌手等）。

    Args:
        music_path (str): 音频文件的本地路径。
        song_info (Dict[str, Any]): 包含歌曲元数据的字典。
        cover_data (bytes | None): 封面图片的二进制数据。
        cover_mime_type (str | None): 封面图片的MIME类型。
        lyrics_text (str | None): 歌词文本。
    """
    if not os.path.exists(music_path):
        logging.warning(f"音乐文件不存在，跳过元数据嵌入: {music_path}")
        return

    name = song_info.get("name", "未知歌曲")
    artist = song_info.get("artist", "未知歌手")
    album = song_info.get("album", "未知专辑")
    file_ext = os.path.splitext(music_path)[-1].lower()

    try:
        audio = None
        if file_ext == ".flac":
            audio = FLAC(music_path)
            audio.delete()  # 清除已有标签
            audio["title"] = name
            audio["artist"] = artist
            audio["album"] = album
            if lyrics_text:
                audio["LYRICS"] = lyrics_text
            if cover_data and cover_mime_type:
                pic = Picture()
                pic.type = 3  # 封面
                pic.mime = cover_mime_type
                pic.desc = "Cover"
                pic.data = cover_data
                audio.add_picture(pic)
        elif file_ext == ".mp3":
            try:
                audio = MP3(music_path, ID3=ID3)
            except HeaderNotFoundError:
                logging.error(f"无法识别的MP3文件头，跳过元数据: {music_path}")
                return
            audio.clear()
            audio.tags.add(TIT2(encoding=3, text=name))  # 标题
            audio.tags.add(TPE1(encoding=3, text=artist))  # 歌手
            audio.tags.add(TALB(encoding=3, text=album))  # 专辑
            if lyrics_text:
                audio.tags.add(USLT(encoding=3, text=lyrics_text))  # 歌词
            if cover_data and cover_mime_type:
                audio.tags.add(
                    APIC(
                        encoding=3,
                        mime=cover_mime_type,
                        type=3,
                        desc="Cover",
                        data=cover_data,
                    )
                )

        if audio:
            audio.save()
            logging.info(f"成功为 {os.path.basename(music_path)} 添加元数据。")
        else:
            logging.info(f"不支持的格式 {file_ext}，跳过元数据嵌入。")
    except Exception as e:
        logging.error(f"为 {os.path.basename(music_path)} 添加元数据时发生异常: {e}")


# --- 4. 异步并发处理核心 ---


async def process_song(
    session: requests.Session,
    music_id: int,
    token_manager: TokenManager,
    semaphore: asyncio.Semaphore,
) -> Tuple[bool, Dict[str, Any] | str]:
    """
    处理单首歌曲下载的完整异步工作流。

    此函数通过信号量控制并发，并从共享的TokenManager获取令牌。
    所有阻塞I/O操作都通过 `asyncio.to_thread` 在后台线程中执行。

    Args:
        session (requests.Session): 共享的HTTP会话。
        music_id (int): 要处理的歌曲ID。
        token_manager (TokenManager): 共享的令牌管理器实例。
        semaphore (asyncio.Semaphore): 用于控制并发的信号量。

    Returns:
        Tuple[bool, Dict[str, Any] | str]: 一个元组，第一个元素表示是否成功，
                                           第二个元素是成功时的歌曲数据或失败时的错误信息。
    """
    async with semaphore:  # 在进入任务前，首先获取一个信号量许可
        try:
            logging.info(f"[任务开始] 处理音乐ID: {music_id}")

            # 步骤 1: 从Token管理器获取Token
            token = await token_manager.get_token()
            if not token:
                return (
                    False,
                    f"无法为 {music_id} 获取共享Token，请检查Token API是否可用",
                )

            # 步骤 2: 获取歌曲信息
            song_data = await asyncio.to_thread(
                get_wyy_source, session, token, music_id
            )
            if not song_data or song_data.get("status") != 200:
                msg = song_data.get("msg") if song_data else "无API响应"
                # 如果失败原因是Token问题，则通知管理器作废当前Token
                if "token" in msg.lower() or "令牌" in msg:
                    await token_manager.invalidate_token()
                return False, f"获取 {music_id} 源信息失败: {msg}"

            # 步骤 3: 下载和保存文件
            await asyncio.to_thread(save_song_files, session, song_data)

            logging.info(f"[任务成功] 已完成处理音乐ID: {music_id}")
            return True, song_data

        except Exception as e:
            # 捕获任何意外异常
            logging.exception(f"[任务失败] 处理音乐ID {music_id} 时发生未知错误")
            return False, f"处理 {music_id} 时发生异常: {e}"


async def main():
    """
    程序的主异步入口。

    负责初始化环境、创建和并发执行所有下载任务，并最后处理结果。
    """
    start_time = datetime.now()

    # 示例：从硬编码的HTML内容中提取音乐ID
    html_context = """
    <ul class="f-hide">
        <li><a href="/song?id=27713963">好心分手</a></li>
        <li><a href="/song?id=29005019">恰似你的温柔</a></li>
        <li><a href="/song?id=2021881721">测试失败ID</a></li>
        <li><a href="/song?id=33894312">光辉岁月</a></li>
        <li><a href="/song?id=487504313">海阔天空</a></li>
    </ul>
    """

    ids_str = re.findall(r'href="/song\?id=(\d+)"', html_context)
    music_ids = [int(id_str) for id_str in ids_str if id_str.isdigit()]

    if not music_ids:
        logging.info("未找到任何歌曲ID，程序退出。")
        return

    logging.info(f"发现 {len(music_ids)} 首歌曲待处理: {music_ids}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Referer": "https://api.toubiec.cn/wyapi.html",
    }

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    logging.info(f"并发控制器已启动，最大并发数: {MAX_CONCURRENCY}")

    # --- 配置带自动重试策略的Session ---
    # 定义重试策略：总共重试3次，对特定HTTP状态码重试，并采用指数退避算法。
    # urllib3的Retry默认会处理连接错误（如SSLError, ConnectionError）。
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
    )
    # 创建一个HTTP适配器并应用重试策略
    adapter = HTTPAdapter(max_retries=retry_strategy)

    # 创建Session，并为所有http和https请求挂载此适配器
    with requests.Session() as session:
        session.headers.update(headers)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        logging.info("已配置HTTP会话，启用自动重试策略（最多3次，带退避）。")

        token_manager = TokenManager(session)

        tasks = [
            process_song(session, mid, token_manager, semaphore) for mid in music_ids
        ]

        results = await asyncio.gather(*tasks)

    # --- 结果处理与报告 ---
    successful_songs, failed_tasks = [], []
    for success, data_or_msg in results:
        if success:
            successful_songs.append(data_or_msg)
        else:
            failed_tasks.append(data_or_msg)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logging.info("=" * 25 + " 处理完成 " + "=" * 25)
    logging.info(f"总耗时: {duration:.2f} 秒")
    logging.info(
        f"总任务数: {len(music_ids)}, 成功: {len(successful_songs)}, 失败: {len(failed_tasks)}"
    )

    if failed_tasks:
        logging.warning("以下任务失败:")
        for reason in failed_tasks:
            logging.warning(f"  - {reason}")

    # 将所有成功获取的API原始结果写入JSON文件，以便调试或备份
    if successful_songs:
        try:
            with open("wyy-source-successful.json", "w", encoding="utf-8") as f:
                json.dump(successful_songs, f, ensure_ascii=False, indent=4)
            logging.info("成功的API响应已保存到 'wyy-source-successful.json'")
        except IOError as e:
            logging.error(f"写入JSON文件时出错: {e}")


# --- 5. 程序启动入口 ---

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("程序被用户中断。")

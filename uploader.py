from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable
from github import GitHubClient, GitHubError
from zip_handler import ZipEntry

ProgressCallback = Callable[["UploadStats", str], Awaitable[None]]

@dataclass(slots=True)
class UploadStats:
    total: int
    done: int = 0
    failed: int = 0
    retries: int = 0
    rate_limits: int = 0
    started: float = field(default_factory=time.monotonic)
    failed_files: list[tuple[str, str]] = field(default_factory=list)
    @property
    def processed(self) -> int: return self.done + self.failed
    @property
    def percent(self) -> float: return 100 * self.processed / max(1, self.total)
    @property
    def elapsed(self) -> float: return max(0.001, time.monotonic() - self.started)
    @property
    def speed(self) -> float: return self.done / self.elapsed
    @property
    def eta(self) -> float: return max(0, (self.total - self.processed) / self.speed) if self.speed > 0 else 0

class UploadManager:
    def __init__(self) -> None:
        self._cancel: dict[int, asyncio.Event] = {}
    def cancel(self, user_id: int) -> bool:
        event = self._cancel.get(user_id)
        if event:
            event.set()
            return True
        return False
    async def upload(self, user_id: int, client: GitHubClient, owner: str, repo: str, branch: str,
                     entries: list[ZipEntry], message: str, workers: int, retries: int,
                     progress: ProgressCallback, new_empty_repo: bool = False) -> UploadStats:
        cancel = asyncio.Event()
        self._cancel[user_id] = cancel
        stats = UploadStats(len(entries))
        lock = asyncio.Lock()
        queue: asyncio.Queue[ZipEntry] = asyncio.Queue()
        for entry in entries:
            queue.put_nowait(entry)
        if new_empty_repo and entries:
            first = await queue.get()
            try:
                payload = await asyncio.to_thread(first.source.read_bytes)
                await client.put_file(owner, repo, first.path, branch, payload, message, retries, omit_branch=True)
                stats.done += 1
            except Exception as exc:
                stats.failed += 1
                stats.failed_files.append((first.path, str(exc)))
            finally:
                queue.task_done()
                await progress(stats, first.path)
        async def worker() -> None:
            while not cancel.is_set():
                try:
                    entry = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                try:
                    payload = await asyncio.to_thread(entry.source.read_bytes)
                    await client.put_file(owner, repo, entry.path, branch, payload, message, retries)
                    async with lock:
                        stats.done += 1
                except GitHubError as exc:
                    async with lock:
                        stats.failed += 1
                        stats.failed_files.append((entry.path, str(exc)))
                        stats.rate_limits += int(exc.status in {403, 429})
                except Exception as exc:
                    async with lock:
                        stats.failed += 1
                        stats.failed_files.append((entry.path, str(exc)))
                finally:
                    queue.task_done()
                    await progress(stats, entry.path)
        try:
            await asyncio.gather(*(worker() for _ in range(max(1, workers))))
        finally:
            self._cancel.pop(user_id, None)
        return stats

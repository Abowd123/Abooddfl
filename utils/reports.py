from pathlib import Path
from uploader import UploadStats

def write_reports(folder: Path, repo_url: str, branch: str, stats: UploadStats, lines: list[str]) -> tuple[Path, Path, Path | None]:
    folder.mkdir(parents=True, exist_ok=True)
    report, log, failed = folder / "report.txt", folder / "log.txt", folder / "failed.txt"
    report.write_text(f"Repository: {repo_url}\nBranch: {branch}\nTotal: {stats.total}\nUploaded: {stats.done}\nFailed: {stats.failed}\nElapsed: {stats.elapsed:.1f}s\nAverage speed: {stats.speed:.2f} files/s\n", encoding="utf-8")
    log.write_text("\n".join(lines), encoding="utf-8")
    if stats.failed_files:
        failed.write_text("\n".join(f"{path}\t{reason}" for path, reason in stats.failed_files), encoding="utf-8")
        return report, log, failed
    return report, log, None

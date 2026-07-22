from __future__ import annotations

import asyncio
import html
import shutil
import time
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from config import Settings
from database import Database
from github import GitHubClient
from keyboards import cancel_upload, confirm, main_menu, repo_mode, result, visibility
from security import TokenVault
from states import Flow
from uploader import UploadManager, UploadStats
from utils.progress import bar, duration
from utils.reports import write_reports
from zip_handler import ZipEntry, ZipSecurityError, extract_zip

router = Router()
manager = UploadManager()


def clean_repo_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "-" for c in value).strip("-")


@router.callback_query(F.data == "upload:start")
async def upload_start(callback: CallbackQuery, db: Database) -> None:
    record = await db.get_user(callback.from_user.id)
    if not record or not record["encrypted_github_token"]:
        await callback.answer("اربط GitHub Token أولاً", show_alert=True)
        return
    await callback.message.edit_text("📁 اختر وضع المستودع:", reply_markup=repo_mode())
    await callback.answer()


@router.callback_query(F.data.startswith("repo:"))
async def choose_repo(callback: CallbackQuery, state: FSMContext) -> None:
    mode = callback.data.split(":")[1]
    await state.update_data(repo_mode=mode)
    if mode == "new":
        await state.set_state(Flow.repo_name)
        await callback.message.edit_text("أرسل اسم المستودع الجديد:")
    else:
        await state.set_state(Flow.existing_repo)
        await callback.message.edit_text("أرسل المستودع بصيغة <code>owner/name</code>:")
    await callback.answer()


@router.message(Flow.repo_name)
async def repo_name(message: Message, state: FSMContext) -> None:
    name = clean_repo_name((message.text or "").strip())
    if not name:
        await message.answer("اسم غير صالح.")
        return
    await state.update_data(repo_name=name)
    await message.answer("اختر الرؤية:", reply_markup=visibility())


@router.callback_query(F.data.startswith("visibility:"))
async def choose_visibility(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(private=callback.data.endswith("private"))
    await state.set_state(Flow.repo_description)
    await callback.message.edit_text("أرسل وصف المستودع، أو أرسل - للتخطي:")
    await callback.answer()


@router.message(Flow.repo_description)
async def description(message: Message, state: FSMContext) -> None:
    await state.update_data(description="" if message.text == "-" else (message.text or "")[:350])
    await state.set_state(Flow.branch)
    await message.answer("أرسل اسم Branch (مثال: main):")


@router.message(Flow.existing_repo)
async def existing_repo(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if value.count("/") != 1:
        await message.answer("الصيغة الصحيحة owner/name")
        return
    owner, name = value.split("/")
    if not owner or not name:
        await message.answer("الصيغة الصحيحة owner/name")
        return
    await state.update_data(owner=owner, repo_name=name)
    await state.set_state(Flow.branch)
    await message.answer("أرسل اسم Branch:")


@router.message(Flow.branch)
async def branch(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if not value or value.startswith("-") or ".." in value or value.endswith("/"):
        await message.answer("اسم Branch غير صالح.")
        return
    await state.update_data(branch=value)
    await state.set_state(Flow.commit_message)
    await message.answer("أرسل Commit Message:")


@router.message(Flow.commit_message)
async def commit_message(message: Message, state: FSMContext) -> None:
    await state.update_data(commit=(message.text or "Upload via Telegram bot")[:500])
    await state.set_state(Flow.zip_file)
    await message.answer("📦 أرسل ملف ZIP الآن.")


@router.message(Flow.zip_file, F.document)
async def receive_zip(message: Message, state: FSMContext, bot: Bot, settings: Settings) -> None:
    document = message.document
    assert document
    if not (document.file_name or "").lower().endswith(".zip"):
        await message.answer("يجب أن يكون الملف ZIP.")
        return
    if document.file_size and document.file_size > settings.max_zip_size_mb * 1024 * 1024:
        await message.answer("حجم الملف يتجاوز الحد المسموح.")
        return
    folder = settings.download_dir / str(message.from_user.id)
    folder.mkdir(parents=True, exist_ok=True)
    zip_path = folder / f"{int(time.time())}.zip"
    try:
        await bot.download(document, destination=zip_path)
    except Exception as exc:
        await message.answer(f"فشل التنزيل: {html.escape(str(exc))}")
        return
    extract_dir = settings.extract_dir / str(message.from_user.id) / str(int(time.time()))
    try:
        entries = await extract_zip(
            zip_path,
            extract_dir,
            settings.max_files,
            settings.max_extracted_size_mb * 1024 * 1024,
        )
    except (ZipSecurityError, Exception) as exc:
        await message.answer(f"❌ ZIP غير صالح: {html.escape(str(exc))}")
        zip_path.unlink(missing_ok=True)
        return
    if not entries:
        await message.answer("الأرشيف فارغ.")
        return
    await state.update_data(
        zip_path=str(zip_path),
        extract_dir=str(extract_dir),
        zip_name=document.file_name,
        total=len(entries),
    )
    await state.set_state(Flow.confirm)
    data = await state.get_data()
    text = (
        f"✅ جاهز للرفع\n📦 {html.escape(document.file_name or '')}"
        f"\n📁 الملفات: {len(entries)}\n🌿 Branch: <code>{html.escape(data['branch'])}</code>"
    )
    await message.answer(text, reply_markup=confirm())


@router.callback_query(F.data == "upload:confirm")
async def launch_upload(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    vault: TokenVault,
    settings: Settings,
) -> None:
    data = await state.get_data()
    user = await db.get_user(callback.from_user.id)
    if not user or not user["encrypted_github_token"]:
        await callback.answer("Token مفقود", show_alert=True)
        return
    await state.set_state(Flow.uploading)
    await callback.message.edit_text("⏳ جارٍ التحضير...", reply_markup=cancel_upload())
    await callback.answer()
    asyncio.create_task(
        run_upload(
            callback.message,
            callback.from_user.id,
            state,
            db,
            vault,
            settings,
            data,
            user["encrypted_github_token"],
        )
    )


@router.callback_query(F.data == "upload:cancel")
async def stop_upload(callback: CallbackQuery) -> None:
    text = "جارٍ الإلغاء..." if manager.cancel(callback.from_user.id) else "لا يوجد رفع نشط"
    await callback.answer(text, show_alert=True)


async def run_upload(
    message: Message,
    user_id: int,
    state: FSMContext,
    db: Database,
    vault: TokenVault,
    settings: Settings,
    data: dict,
    encrypted_token: bytes,
) -> None:
    extract_dir = Path(data["extract_dir"])
    zip_path = Path(data["zip_path"])
    entries = [
        ZipEntry(str(path.relative_to(extract_dir)).replace("\\", "/"), path, path.stat().st_size)
        for path in extract_dir.rglob("*")
        if path.is_file()
    ]
    workers = int(data.get("workers", settings.default_workers))
    retries = int(data.get("retries", settings.default_retries))
    logs: list[str] = []
    last_update = 0.0
    owner = data.get("owner")
    repository = data["repo_name"]
    is_new = data["repo_mode"] == "new"
    target_branch = data["branch"]
    token = vault.decrypt(encrypted_token)
    operation_id: int | None = None
    try:
        async with GitHubClient(token) as github:
            if is_new:
                repo_data = await github.create_repo(
                    repository, bool(data.get("private")), data.get("description", "")
                )
                owner = repo_data["owner"]["login"]
                repository = repo_data["name"]
            else:
                await github.repo(owner, repository)
            operation_id = await db.start_operation(
                user_id,
                f"{owner}/{repository}",
                target_branch,
                data["zip_name"],
                len(entries),
            )

            async def update_progress(stats: UploadStats, current: str) -> None:
                nonlocal last_update
                logs.append(f"{time.strftime('%H:%M:%S')} processed {current}")
                now = time.monotonic()
                if now - last_update < settings.progress_update_seconds and stats.processed < stats.total:
                    return
                last_update = now
                text = (
                    f"🚀 <b>جارٍ الرفع</b>\n<code>{bar(stats.percent)}</code> {stats.percent:.1f}%\n\n"
                    f"📁 الكل: {stats.total}\n✅ مرفوع: {stats.done}\n❌ فاشل: {stats.failed}"
                    f"\n⏳ متبقٍ: {stats.total - stats.processed}\n⚡ السرعة: {stats.speed:.2f} ملف/ث"
                    f"\n🕒 الوقت المتوقع: {duration(stats.eta)}\n🔄 Workers: {workers} | Retry: {retries}"
                    f"\n\n<code>{html.escape(current[-80:])}</code>"
                )
                try:
                    await message.edit_text(text, reply_markup=cancel_upload())
                except Exception:
                    pass

            stats = await manager.upload(
                user_id,
                github,
                owner,
                repository,
                target_branch,
                entries,
                data["commit"],
                workers,
                retries,
                update_progress,
                new_empty_repo=is_new,
            )
            status = "cancelled" if stats.processed < stats.total else ("partial" if stats.failed else "success")
            await db.finish_operation(operation_id, stats.done, stats.failed, status)
            repo_url = "https:" + "//github.com/" + owner + "/" + repository
            report_dir = settings.log_dir / str(user_id) / str(operation_id)
            report_path, log_path, failed_path = write_reports(
                report_dir, repo_url, target_branch, stats, logs
            )
            await message.edit_text(
                f"🎉 <b>اكتملت العملية</b>\n✅ {stats.done} | ❌ {stats.failed} | ⏱ {duration(stats.elapsed)}\n{repo_url}",
                reply_markup=result(repo_url),
            )
            await message.answer_document(FSInputFile(report_path), caption="📄 التقرير النهائي")
            await message.answer_document(FSInputFile(log_path), caption="🧾 Log.txt")
            if failed_path:
                await message.answer_document(FSInputFile(failed_path), caption="⚠️ Failed.txt")
    except Exception as exc:
        if operation_id is not None:
            await db.finish_operation(operation_id, 0, 0, "failed", str(exc))
        await message.edit_text(
            f"❌ فشلت العملية: <code>{html.escape(str(exc))}</code>",
            reply_markup=main_menu(True),
        )
    finally:
        await state.clear()
        shutil.rmtree(extract_dir, ignore_errors=True)
        zip_path.unlink(missing_ok=True)

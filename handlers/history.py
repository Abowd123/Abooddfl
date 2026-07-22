from aiogram import F, Router
from aiogram.types import CallbackQuery
from database import Database
router = Router()

@router.callback_query(F.data == "history")
async def history(callback: CallbackQuery, db: Database) -> None:
    rows = await db.recent_operations(callback.from_user.id)
    if not rows:
        text = "📜 لا توجد عمليات سابقة."
    else:
        parts = ["📜 <b>آخر العمليات</b>"]
        for row in rows:
            parts.append(f"\n• <code>{row['repository']}</code> [{row['status']}]\n  ✅ {row['uploaded_files']} | ❌ {row['failed_files']} | 📁 {row['total_files']}")
        text = "\n".join(parts)
    await callback.message.answer(text)
    await callback.answer()

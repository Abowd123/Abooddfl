from aiogram import F, Router
from aiogram.types import CallbackQuery
router = Router()

@router.callback_query(F.data == "admin")
async def admin(callback: CallbackQuery, db_user: dict | None) -> None:
    if not db_user or db_user.get("role") != "admin":
        await callback.answer("غير مصرح", show_alert=True)
        return
    await callback.message.answer("🛡 <b>لوحة الإدارة</b>\n\nالصلاحيات المتاحة: user / admin / blocked.")
    await callback.answer()

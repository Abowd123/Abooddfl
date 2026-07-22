from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from config import Settings
from database import Database
from keyboards import main_menu
router = Router()

@router.message(CommandStart())
async def start(message: Message, state: FSMContext, db: Database, settings: Settings) -> None:
    user = message.from_user
    assert user
    await db.register_user(user.id, user.username, user.full_name, user.id in settings.admin_ids)
    await state.clear()
    record = await db.get_user(user.id)
    text = "🚀 <b>ZIP to GitHub Uploader Pro</b>\n\nارفع أرشيف ZIP إلى GitHub بأمان، مع تقدم حي وتقارير كاملة."
    await message.answer(text, reply_markup=main_menu(bool(record and record["encrypted_github_token"]), bool(record and record["role"] == "admin")))

@router.callback_query(F.data == "home")
async def home(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await state.clear()
    record = await db.get_user(callback.from_user.id)
    await callback.message.edit_text("🏠 <b>اللوحة الرئيسية</b>", reply_markup=main_menu(bool(record and record["encrypted_github_token"]), bool(record and record["role"] == "admin")))
    await callback.answer()

@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await state.clear()
    record = await db.get_user(callback.from_user.id)
    await callback.message.edit_text("تم إلغاء العملية.", reply_markup=main_menu(bool(record and record["encrypted_github_token"]), bool(record and record["role"] == "admin")))
    await callback.answer()

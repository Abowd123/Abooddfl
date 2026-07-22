from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from database import Database
from github import GitHubClient, GitHubError
from keyboards import main_menu
from security import TokenVault
from states import Flow
router = Router()

@router.callback_query(F.data == "github:token")
async def ask_token(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Flow.token)
    await callback.message.edit_text("🔑 أرسل GitHub Personal Access Token.\n\nلن يُحفظ كنص صريح وسيتم حذف رسالتك مباشرة.")
    await callback.answer()

@router.message(Flow.token)
async def save_token(message: Message, state: FSMContext, db: Database, vault: TokenVault) -> None:
    raw = (message.text or "").strip()
    try:
        await message.delete()
    except Exception:
        pass
    try:
        async with GitHubClient(raw) as github:
            user = await github.user()
    except GitHubError as exc:
        await message.answer(f"❌ Token غير صالح: <code>{exc}</code>")
        return
    await db.save_token(message.from_user.id, vault.encrypt(raw), user["login"])
    await state.clear()
    text = (f"✅ <b>تم ربط GitHub</b>\n\n👤 {user.get('name') or user['login']} (@{user['login']})"
            f"\n📦 المستودعات: {user.get('public_repos', 0) + user.get('total_private_repos', 0)}"
            f"\n👥 المتابعون: {user.get('followers', 0)}\n🧩 Gists: {user.get('public_gists', 0)}")
    if user.get("avatar_url"):
        await message.answer_photo(user["avatar_url"], caption=text, reply_markup=main_menu(True))
    else:
        await message.answer(text, reply_markup=main_menu(True))

@router.callback_query(F.data == "github:account")
async def account(callback: CallbackQuery, db: Database, vault: TokenVault) -> None:
    record = await db.get_user(callback.from_user.id)
    if not record or not record["encrypted_github_token"]:
        await callback.answer("اربط GitHub أولاً", show_alert=True)
        return
    try:
        async with GitHubClient(vault.decrypt(record["encrypted_github_token"])) as github:
            user = await github.user()
        caption = (f"👤 <b>{user.get('name') or user['login']}</b>\n@{user['login']}"
                   f"\n📦 Repositories: {user.get('public_repos', 0) + user.get('total_private_repos', 0)}"
                   f"\n👥 Followers: {user.get('followers', 0)}\n🧩 Gists: {user.get('public_gists', 0)}")
        if user.get("avatar_url"):
            await callback.message.answer_photo(user["avatar_url"], caption=caption)
        else:
            await callback.message.answer(caption)
    except Exception as exc:
        await callback.message.answer(f"❌ {exc}")
    await callback.answer()

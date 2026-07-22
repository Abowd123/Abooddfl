from aiogram import F,Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery,Message
from config import Settings
from states import Flow
router=Router()
@router.callback_query(F.data=='settings')
async def settings(c:CallbackQuery,state:FSMContext,settings:Settings)->None:
 await state.set_state(Flow.workers);await c.message.answer(f'⚙️ أرسل عدد Workers من 1 إلى {settings.max_workers} (الافتراضي {settings.default_workers}).');await c.answer()
@router.message(Flow.workers)
async def workers(m:Message,state:FSMContext,settings:Settings)->None:
 try:v=int(m.text or '')
 except ValueError:await m.answer('أرسل رقماً صحيحاً.');return
 if not 1<=v<=settings.max_workers:await m.answer('القيمة خارج النطاق.');return
 await state.update_data(workers=v);await state.set_state(Flow.retries);await m.answer('أرسل عدد المحاولات التلقائية من 0 إلى 5.')
@router.message(Flow.retries)
async def retries(m:Message,state:FSMContext)->None:
 try:v=int(m.text or '')
 except ValueError:await m.answer('أرسل رقماً صحيحاً.');return
 if not 0<=v<=5:await m.answer('القيمة خارج النطاق.');return
 await state.update_data(retries=v);await state.set_state(None);await m.answer('✅ حُفظت الإعدادات لهذه الجلسة.')

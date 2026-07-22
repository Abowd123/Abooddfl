from __future__ import annotations
import asyncio,logging
from aiogram import Bot,Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import get_settings
from database import Database
from handlers import routers
from middlewares.auth import AccessMiddleware
from middlewares.session import SessionPersistenceMiddleware
from security import TokenVault
from uploader import UploadManager

async def main()->None:
 settings=get_settings();logging.basicConfig(level=logging.INFO,format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',handlers=[logging.FileHandler(settings.log_dir/'bot.log',encoding='utf-8'),logging.StreamHandler()])
 db=Database(settings.database_url);await db.init();vault=TokenVault(settings.encryption_key)
 bot=Bot(settings.bot_token,default=DefaultBotProperties(parse_mode=ParseMode.HTML));dp=Dispatcher(storage=MemoryStorage())
 dp['db']=db;dp['settings']=settings;dp['vault']=vault
 access=AccessMiddleware(db);dp.message.middleware(access);dp.callback_query.middleware(access)
 session_middleware=SessionPersistenceMiddleware(db)
 dp.message.middleware(session_middleware);dp.callback_query.middleware(session_middleware)
 for r in routers:dp.include_router(r)
 await bot.delete_webhook(drop_pending_updates=False);await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())
if __name__=='__main__':asyncio.run(main())

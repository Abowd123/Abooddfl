from typing import Any,Awaitable,Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from database import Database
class AccessMiddleware(BaseMiddleware):
 def __init__(self,db:Database):self.db=db
 async def __call__(self,handler:Callable[[TelegramObject,dict[str,Any]],Awaitable[Any]],event:TelegramObject,data:dict[str,Any])->Any:
  user=data.get('event_from_user')
  if user:
   record=await self.db.get_user(user.id)
   if record and record['role']=='blocked':
    if hasattr(event,'answer'):await event.answer('⛔ تم حظر حسابك من استخدام البوت.')
    return None
   data['db_user']=record
  return await handler(event,data)

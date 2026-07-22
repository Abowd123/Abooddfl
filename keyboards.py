from aiogram.types import InlineKeyboardButton,InlineKeyboardMarkup,CopyTextButton

def main_menu(authenticated:bool,is_admin:bool=False)->InlineKeyboardMarkup:
 rows=[[InlineKeyboardButton(text='🚀 رفع ZIP إلى GitHub',callback_data='upload:start')],[InlineKeyboardButton(text='👤 حساب GitHub',callback_data='github:account'),InlineKeyboardButton(text='📜 السجل',callback_data='history')],[InlineKeyboardButton(text='🔑 تغيير Token' if authenticated else '🔑 ربط GitHub',callback_data='github:token'),InlineKeyboardButton(text='⚙️ الإعدادات',callback_data='settings')]]
 if is_admin:rows.append([InlineKeyboardButton(text='🛡 الإدارة',callback_data='admin')])
 return InlineKeyboardMarkup(inline_keyboard=rows)

def repo_mode()->InlineKeyboardMarkup:return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='➕ مستودع جديد',callback_data='repo:new'),InlineKeyboardButton(text='📂 مستودع موجود',callback_data='repo:existing')],[InlineKeyboardButton(text='❌ إلغاء',callback_data='cancel')]])
def visibility()->InlineKeyboardMarkup:return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🌐 Public',callback_data='visibility:public'),InlineKeyboardButton(text='🔒 Private',callback_data='visibility:private')]])
def confirm()->InlineKeyboardMarkup:return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✅ بدء الرفع',callback_data='upload:confirm'),InlineKeyboardButton(text='❌ إلغاء',callback_data='cancel')]])
def cancel_upload()->InlineKeyboardMarkup:return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⏹ إلغاء الرفع',callback_data='upload:cancel')]])
def result(repo_url:str)->InlineKeyboardMarkup:return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↗️ فتح Repository',url=repo_url)],[InlineKeyboardButton(text='📋 نسخ الرابط',copy_text=CopyTextButton(text=repo_url))],[InlineKeyboardButton(text='🏠 الرئيسية',callback_data='home')]])

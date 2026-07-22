# ZIP to GitHub Telegram Bot

بوت Telegram متعدد المستخدمين، Async بالكامل، يحوّل وظائف موقع **ZIP to GitHub Uploader Pro** إلى محادثة FSM احترافية.

اقرأ `ANALYSIS_AR.md` للتحليل الكامل والمطابقة الوظيفية والقيود الواقعية.

## التشغيل السريع

```bash
cp .env.example .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# ضع المفتاح وBOT_TOKEN داخل .env
python -m venv .venv
source .venv/bin/activate
pip install -e .
python main.py
```

أو:

```bash
docker compose up -d --build
```

## GitHub Token

استخدم Fine-grained PAT بصلاحية **Contents: Read and write** و**Administration: Read and write** عند إنشاء المستودعات، أو Classic PAT بصلاحية `repo`. لا ترسل الرمز لأي شخص؛ البوت يحذف الرسالة ويخزنه مشفراً.

## البنية

- `config.py`: إعدادات Pydantic.
- `database.py`: SQLite، مستخدمون، جلسات وسجل عمليات.
- `github.py`: عميل GitHub Async مع Retry وRate Limits.
- `zip_handler.py`: فك ZIP آمن إلى القرص.
- `uploader.py`: طابور Workers، تقدم وإلغاء.
- `keyboards.py`: Inline keyboards ونسخ الرابط.
- `handlers/`: تدفق FSM والمصادقة والسجل والإعدادات والإدارة.
- `middlewares/`: منع المستخدمين المحظورين وحقن بيانات الوصول.
- `utils/`: شريط التقدم والتقارير.

## الأمان والتشغيل الإنتاجي

1. اجعل `.env` خارج Git واضبط صلاحياته `chmod 600 .env`.
2. احتفظ بـ `ENCRYPTION_KEY` في Secret Manager؛ فقدانه يجعل الرموز القديمة غير قابلة للفك.
3. شغّل البوت كمستخدم غير root وحدد أحجام Volumes.
4. افحص ZIP بمضاد برمجيات خبيثة إذا كان البوت عاماً.
5. للإنتاج الكبير، استبدل SQLite/PostgreSQL وMemoryStorage بـ PostgreSQL وRedis FSM، وشغّل عاملاً منفصلاً للرفع.

## الاختبارات

```bash
pip install -e '.[dev]'
pytest -q
ruff check .
```

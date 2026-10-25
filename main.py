"""
نظام مستشفى كوستي التعليمي - الحجز الإلكتروني (Flet 1.0)

الأدوار: مريض - موظف استقبال - طبيب - فني مختبر - صيدلي - مدير
"""
import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from datetime import date, datetime

import flet as ft

# ===============================================================
# 1) الإعدادات العامة
# ===============================================================
if os.environ.get("FLET_APP_STORAGE_DATA"):
    DB_PATH = os.path.join(os.environ["FLET_APP_STORAGE_DATA"], "kosti_hospital.db")
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kosti_hospital.db")

APPOINTMENT_FEE = 10_000      # سعر تذكرة الموعد (جنيه)
LAB_TEST_PRICE = 10_000       # سعر الفحص المخبري (جنيه)
MAX_RECEIPT_MB = 8
BANK_ACCOUNT_TEXT = "بنكك: 9147234"

HOSPITAL_NAME = "مستشفى كوستي التعليمي"
HOSPITAL_PHONE = "0121345123"
HOSPITAL_ADDRESS = "مدينة كوستي - ولاية النيل الأبيض، السودان"   # عدّل العنوان التفصيلي (الحي/الشارع) حسب الواقع

CLINICS = ["عيادة الباطنية", "عيادة الجراحة", "عيادة الأطفال", "عيادة النساء والتوليد"]

# أيام الأسبوع بترقيم بايثون (الاثنين=0 ... الأحد=6)
DAY_NAMES = {5: "السبت", 6: "الأحد", 0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس", 4: "الجمعة"}
WEEK_ORDER = [5, 6, 0, 1, 2, 3, 4]
SUN_THU = "6,0,1,2,3"
SAT_WED = "5,6,0,1,2"

# أطباء تجريبيون (3 في كل عيادة) - يمكن للمدير إضافة غيرهم من التطبيق
DOCTORS_SEED = [
    ("محمد أحمد", "عيادة الباطنية", "باطنية", SUN_THU, "8 ص - 2 م"),
    ("عثمان إبراهيم", "عيادة الباطنية", "باطنية - قلب", SUN_THU, "2 م - 8 م"),
    ("آمنة صالح", "عيادة الباطنية", "باطنية - سكري", SAT_WED, "9 ص - 3 م"),
    ("أمير محمد", "عيادة الجراحة", "جراحة عامة", SAT_WED, "8 ص - 2 م"),
    ("ياسر حسن", "عيادة الجراحة", "جراحة عظام", SUN_THU, "9 ص - 3 م"),
    ("نجلاء عبدالله", "عيادة الجراحة", "جراحة عامة", SUN_THU, "2 م - 8 م"),
    ("سلمى خالد", "عيادة الأطفال", "طب الأطفال", SUN_THU, "9 ص - 3 م"),
    ("بشير علي", "عيادة الأطفال", "طب الأطفال", SAT_WED, "8 ص - 2 م"),
    ("رحاب يوسف", "عيادة الأطفال", "حديثي الولادة", SUN_THU, "2 م - 8 م"),
    ("هند عمر", "عيادة النساء والتوليد", "نساء وتوليد", SUN_THU, "9 ص - 3 م"),
    ("منى الطيب", "عيادة النساء والتوليد", "نساء وتوليد", SAT_WED, "8 ص - 2 م"),
    ("سارة آدم", "عيادة النساء والتوليد", "متابعة الحمل", SUN_THU, "2 م - 8 م"),
]

# الفحوصات المخبرية (الأسعار 10,000 جنيه لكل فحص)
LAB_TESTS_SEED = [
    ("فحص الملاريا", LAB_TEST_PRICE),
    ("فحص الالتهاب (CRP)", LAB_TEST_PRICE),
    ("فحص التايفويد", LAB_TEST_PRICE),
]

# أدوية تجريبية بأسعار تقديرية - يعدّلها الصيدلي من شاشة المخزون
MEDICINES_SEED = [
    ("باراسيتامول 500 مجم (شريط)", 1_500, 100),
    ("أموكسيسيلين 500 مجم (شريط)", 4_000, 60),
    ("أوميبرازول 20 مجم (شريط)", 3_500, 50),
    ("أملاح الإماهة الفموية ORS", 800, 120),
    ("فيتامين ج (علبة)", 2_500, 40),
]

# حسابات الموظفين الافتراضية - يُطلب تغيير كلمة السر عند أول دخول
STAFF_SEED = [
    ("reception", "موظف الاستقبال", "reception", "reception123"),
    ("lab", "فني المختبر", "lab", "lab12345"),
    ("pharmacy", "الصيدلي", "pharmacy", "pharmacy123"),
    ("admin", "مدير النظام", "admin", os.environ.get("KOSTI_ADMIN_PASS", "admin123")),
]
DOCTOR_DEFAULT_PASSWORD = "doctor123"

ROLE_NAMES = {"patient": "مريض", "reception": "موظف استقبال", "doctor": "طبيب",
              "lab": "فني مختبر", "pharmacy": "صيدلي", "admin": "مدير"}

# حالات الدفع
PAID, UNPAID, VERIFY = "تم الدفع", "لم يتم الدفع", "بانتظار التحقق"
# حالات الحجز
A_PENDING, A_OK, A_REJECT, A_CANCEL = "بانتظار التأكيد", "مؤكد", "مرفوض", "ملغي"

STATE = {"picker": None, "user": None}

# ===============================================================
# 2) قاعدة البيانات
# ===============================================================
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def db(sql, params=(), fetch=None, commit=False):
    """fetch: one | all | id (يرجع رقم السجل المُدرج)"""
    conn = connect()
    try:
        cur = conn.execute(sql, params)
        out = None
        if fetch == "one":
            out = cur.fetchone()
        elif fetch == "all":
            out = cur.fetchall()
        elif fetch == "id":
            out = cur.lastrowid
        if commit:
            conn.commit()
        return out
    finally:
        conn.close()


def ensure_column(table, column, decl):
    cols = [r["name"] for r in db(f"PRAGMA table_info({table})", fetch="all")]
    if column not in cols:
        db(f"ALTER TABLE {table} ADD COLUMN {column} {decl}", commit=True)


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000).hex()
    return salt, digest


def verify_password(password, salt, digest):
    return hmac.compare_digest(hash_password(password, salt)[1], digest)


def add_user(username, full_name, role, password, national_id=None, phone=None, must_change=0):
    salt, digest = hash_password(password)
    return db("""INSERT INTO users (username, full_name, national_id, phone, password_salt,
                 password_hash, role, must_change, created_at) VALUES (?,?,?,?,?,?,?,?,?)""",
              (username, full_name, national_id, phone, salt, digest, role, must_change,
               datetime.now().strftime("%Y-%m-%d %H:%M")), fetch="id", commit=True)


def add_doctor(name, clinic, specialty, work_days, hours, username, password):
    uid = add_user(username, f"د. {name}", "doctor", password, must_change=1)
    return db("""INSERT INTO doctors (user_id, name, clinic, specialty, work_days, hours)
                 VALUES (?,?,?,?,?,?)""", (uid, name, clinic, specialty, work_days, hours),
              fetch="id", commit=True)


def init_db():
    db("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        national_id TEXT UNIQUE,
        phone TEXT,
        password_salt TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        must_change INTEGER DEFAULT 0,
        created_at TEXT)""", commit=True)
    db("""CREATE TABLE IF NOT EXISTS doctors (
        doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        clinic TEXT NOT NULL,
        specialty TEXT,
        work_days TEXT,
        hours TEXT)""", commit=True)
    db("""CREATE TABLE IF NOT EXISTS doctor_absences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id INTEGER NOT NULL,
        day TEXT NOT NULL,
        UNIQUE(doctor_id, day))""", commit=True)
    db("""CREATE TABLE IF NOT EXISTS appointments (
        appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        patient_name TEXT,
        national_id TEXT,
        clinic_name TEXT,
        doctor_id INTEGER,
        doctor_name TEXT,
        appointment_date TEXT,
        booked_at TEXT,
        status TEXT DEFAULT 'بانتظار التأكيد',
        staff_note TEXT,
        fee INTEGER DEFAULT 10000,
        payment_status TEXT DEFAULT 'لم يتم الدفع',
        receipt BLOB)""", commit=True)
    # ترقية قاعدة البيانات القديمة (النسخ السابقة من التطبيق)
    for col, decl in [("user_id", "INTEGER"), ("doctor_id", "INTEGER"),
                      ("status", "TEXT DEFAULT 'بانتظار التأكيد'"), ("staff_note", "TEXT"),
                      ("fee", "INTEGER DEFAULT 10000"), ("payment_status", "TEXT DEFAULT 'لم يتم الدفع'"),
                      ("receipt", "BLOB")]:
        ensure_column("appointments", col, decl)
    db("""CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,
        ref_id INTEGER NOT NULL,
        user_id INTEGER,
        amount INTEGER,
        method TEXT,
        bank TEXT,
        reference TEXT,
        status TEXT,
        receipt BLOB,
        created_at TEXT)""", commit=True)
    db("""CREATE TABLE IF NOT EXISTS lab_tests (
        test_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        price INTEGER NOT NULL)""", commit=True)
    db("""CREATE TABLE IF NOT EXISTS lab_orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        patient_name TEXT,
        test_id INTEGER,
        test_name TEXT,
        price INTEGER,
        requested_at TEXT,
        payment_status TEXT DEFAULT 'لم يتم الدفع',
        status TEXT DEFAULT 'قيد الفحص',
        result TEXT,
        result_notes TEXT,
        result_at TEXT)""", commit=True)
    db("""CREATE TABLE IF NOT EXISTS medicines (
        med_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        price INTEGER NOT NULL,
        stock INTEGER NOT NULL DEFAULT 0)""", commit=True)
    db("""CREATE TABLE IF NOT EXISTS pharmacy_orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        patient_name TEXT,
        total INTEGER,
        created_at TEXT,
        payment_status TEXT DEFAULT 'لم يتم الدفع',
        status TEXT DEFAULT 'قيد التجهيز')""", commit=True)
    db("""CREATE TABLE IF NOT EXISTS pharmacy_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        med_id INTEGER,
        name TEXT,
        qty INTEGER,
        unit_price INTEGER)""", commit=True)
    db("""CREATE TABLE IF NOT EXISTS sms_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        phone TEXT,
        message TEXT,
        status TEXT,
        created_at TEXT)""", commit=True)

    # نقل الإيصالات القديمة (من النسخة السابقة) إلى جدول المدفوعات بحالة "بانتظار التحقق"
    legacy = db("""SELECT appointment_id FROM appointments WHERE receipt IS NOT NULL AND user_id IS NULL
                   AND appointment_id NOT IN (SELECT ref_id FROM payments WHERE kind='appointment')""",
                fetch="all")
    for r in legacy:
        rec = db("SELECT receipt FROM appointments WHERE appointment_id=?", (r["appointment_id"],), fetch="one")
        db("""INSERT INTO payments (kind, ref_id, amount, method, status, receipt, created_at)
              VALUES ('appointment', ?, ?, 'receipt', ?, ?, ?)""",
           (r["appointment_id"], APPOINTMENT_FEE, VERIFY, rec["receipt"], now()), commit=True)
        db("UPDATE appointments SET payment_status=?, receipt=NULL WHERE appointment_id=?",
           (VERIFY, r["appointment_id"]), commit=True)
    db("UPDATE appointments SET payment_status=? WHERE payment_status='لم يتم إرفاق صورة'", (UNPAID,), commit=True)

    seed_data()


def seed_data():
    if not db("SELECT 1 FROM doctors LIMIT 1", fetch="one"):
        for i, (name, clinic, spec, days, hours) in enumerate(DOCTORS_SEED, start=1):
            add_doctor(name, clinic, spec, days, hours, f"doctor{i}", DOCTOR_DEFAULT_PASSWORD)
    for username, full_name, role, password in STAFF_SEED:
        if not db("SELECT 1 FROM users WHERE role=? LIMIT 1", (role,), fetch="one"):
            add_user(username, full_name, role, password, must_change=1)
    if not db("SELECT 1 FROM lab_tests LIMIT 1", fetch="one"):
        for name, price in LAB_TESTS_SEED:
            db("INSERT INTO lab_tests (name, price) VALUES (?,?)", (name, price), commit=True)
    if not db("SELECT 1 FROM medicines LIMIT 1", fetch="one"):
        for name, price, stock in MEDICINES_SEED:
            db("INSERT INTO medicines (name, price, stock) VALUES (?,?,?)", (name, price, stock), commit=True)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def money(n):
    return f"{int(n or 0):,} جنيه"


# ===============================================================
# 3) الحسابات وتسجيل الدخول
# ===============================================================
_FAILED = {}  # محاولات الدخول الفاشلة: {المعرّف: (العدد، وقت القفل)}


def register_patient(full_name, national_id, phone, password, confirm):
    full_name, national_id, phone = full_name.strip(), national_id.strip(), phone.strip()
    if not (full_name and national_id and phone and password):
        return None, "أدخل جميع البيانات"
    if len(national_id) != 11 or not national_id.isdigit():
        return None, "الرقم الوطني 11 رقماً"
    if len(phone) != 10 or not phone.isdigit() or not phone.startswith("09"):
        return None, "رقم الهاتف غير صحيح (10 أرقام تبدأ بـ 09)"
    if len(password) < 6:
        return None, "كلمة السر 6 أحرف على الأقل"
    if password != confirm:
        return None, "كلمتا السر غير متطابقتين"
    if db("SELECT 1 FROM users WHERE national_id=? OR username=?", (national_id, national_id), fetch="one"):
        return None, "هذا الرقم الوطني مسجّل مسبقاً، سجّل الدخول"
    uid = add_user(national_id, full_name, "patient", password, national_id=national_id, phone=phone)
    return get_user(uid), None


def get_user(uid):
    row = db("SELECT * FROM users WHERE user_id=?", (uid,), fetch="one")
    return dict(row) if row else None


def authenticate(identifier, password):
    identifier = identifier.strip()
    count, locked_until = _FAILED.get(identifier, (0, 0))
    if locked_until > time.time():
        return None, "تم إيقاف المحاولات مؤقتاً، حاول بعد دقيقة"
    row = db("SELECT * FROM users WHERE username=? OR national_id=?", (identifier, identifier), fetch="one")
    if row and verify_password(password, row["password_salt"], row["password_hash"]):
        _FAILED.pop(identifier, None)
        return dict(row), None
    count += 1
    _FAILED[identifier] = (count, time.time() + 60 if count >= 5 else 0)
    return None, "بيانات الدخول غير صحيحة"


def change_password(uid, current, new, confirm):
    user = get_user(uid)
    if not verify_password(current, user["password_salt"], user["password_hash"]):
        return "كلمة السر الحالية غير صحيحة"
    if len(new) < 6:
        return "كلمة السر الجديدة 6 أحرف على الأقل"
    if new != confirm:
        return "كلمتا السر غير متطابقتين"
    if new == current:
        return "اختر كلمة سر مختلفة عن الحالية"
    salt, digest = hash_password(new)
    db("UPDATE users SET password_salt=?, password_hash=?, must_change=0 WHERE user_id=?",
       (salt, digest, uid), commit=True)
    return None


# ===============================================================
# 3.5) رسائل SMS للمريض
# ===============================================================
class SmsGateway:
    """واجهة إرسال الرسائل النصية. للربط الفعلي:
    1) اشترك لدى مزوّد رسائل SMS يدعم السودان واحصل على مفتاح API ومعرّف مرسل (Sender ID).
    2) أنشئ صنفاً يرث من هذا الصنف ونفّذ send() بنداء HTTPS للمزوّد (المفتاح من متغير بيئة، ليس من الكود).
    3) بدّل SMS بالصنف الجديد. التطبيق يتحمل فشل الإرسال دون أن يتعطل الحجز.
    """

    def send(self, phone, text):
        """يرجع (نجح؟، رسالة)"""
        raise NotImplementedError


class SandboxSms(SmsGateway):
    """وضع تجريبي: لا يرسل شيئاً فعلياً، يكتفي بتسجيل الرسالة في جدول sms_log (تظهر في تقارير المدير)."""

    def send(self, phone, text):
        return True, "تم تسجيل الرسالة (تجريبي)"


SMS = SandboxSms()


def notify_patient(user_id, text):
    """يرسل رسالة SMS للمريض ويسجلها. أي فشل في الإرسال لا يوقف العملية الأصلية."""
    if not user_id:
        return
    try:
        u = db("SELECT phone FROM users WHERE user_id=?", (user_id,), fetch="one")
        if not u or not u["phone"]:
            return
        message = f"{HOSPITAL_NAME}: {text}"
        try:
            ok, _ = SMS.send(u["phone"], message)
            status = "مُرسلة" if ok else "فشل الإرسال"
        except Exception:
            status = "فشل الإرسال"
        db("INSERT INTO sms_log (user_id, phone, message, status, created_at) VALUES (?,?,?,?,?)",
           (user_id, u["phone"], message, status, now()), commit=True)
    except Exception:
        pass


# ===============================================================
# 4) منطق الأطباء والحجز
# ===============================================================
def parse_days(s):
    return [int(x) for x in (s or "").split(",") if x.strip() != ""]


def days_text(s):
    days = sorted(parse_days(s), key=WEEK_ORDER.index)
    if not days:
        return "—"
    idx = [WEEK_ORDER.index(d) for d in days]
    if len(idx) > 2 and idx == list(range(idx[0], idx[0] + len(idx))):
        return f"{DAY_NAMES[days[0]]} - {DAY_NAMES[days[-1]]}"
    return "، ".join(DAY_NAMES[d] for d in days)


def doctor_available_on(doctor_id, day):
    """يرجع (متاح؟، سبب عدم التوفر)"""
    doc = db("SELECT * FROM doctors WHERE doctor_id=?", (doctor_id,), fetch="one")
    if not doc:
        return False, "الطبيب غير موجود"
    if day.weekday() not in parse_days(doc["work_days"]):
        return False, f"الطبيب لا يعمل يوم {DAY_NAMES[day.weekday()]} (أيام العمل: {days_text(doc['work_days'])})"
    if db("SELECT 1 FROM doctor_absences WHERE doctor_id=? AND day=?", (doctor_id, day.isoformat()), fetch="one"):
        return False, "الطبيب غير موجود في هذا التاريخ"
    return True, ""


def book_appointment(user, doctor_id, date_text):
    try:
        day = datetime.strptime(date_text.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None, "صيغة التاريخ غير صحيحة (مثال: 2026-11-15)"
    if day < date.today():
        return None, "لا يمكن الحجز في تاريخ سابق"
    ok, why = doctor_available_on(doctor_id, day)
    if not ok:
        return None, why
    doc = db("SELECT * FROM doctors WHERE doctor_id=?", (doctor_id,), fetch="one")
    if db("""SELECT 1 FROM appointments WHERE user_id=? AND doctor_id=? AND appointment_date=?
             AND status IN (?,?)""", (user["user_id"], doctor_id, day.isoformat(), A_PENDING, A_OK), fetch="one"):
        return None, "لديك حجز عند هذا الطبيب في نفس التاريخ"
    aid = db("""INSERT INTO appointments (user_id, patient_name, national_id, clinic_name, doctor_id,
                doctor_name, appointment_date, booked_at, status, fee, payment_status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
             (user["user_id"], user["full_name"], user["national_id"], doc["clinic"], doctor_id,
              doc["name"], day.isoformat(), now(), A_PENDING, APPOINTMENT_FEE, UNPAID),
             fetch="id", commit=True)
    return aid, None


def review_appointment(appointment_id, approve, note):
    """تغذية راجعة من موظف الاستقبال: تأكيد أو رفض الحجز."""
    a = db("SELECT * FROM appointments WHERE appointment_id=?", (appointment_id,), fetch="one")
    if not a or a["status"] != A_PENDING:
        return "الحجز غير متاح للمراجعة"
    if approve and a["payment_status"] != PAID:
        return "تحقق من الدفع أولاً (إيصال أو استلام نقدي) قبل التأكيد"
    if not approve and not note.strip():
        return "اكتب سبب الرفض ليظهر للمريض"
    db("UPDATE appointments SET status=?, staff_note=? WHERE appointment_id=?",
       (A_OK if approve else A_REJECT, note.strip() or None, appointment_id), commit=True)
    what = f"عند د. {a['doctor_name']} ({a['clinic_name']}) بتاريخ {a['appointment_date']}"
    if approve:
        text = f"تم تأكيد حجزك {what}."
        if note.strip():
            text += f" ملاحظة: {note.strip()}"
    else:
        text = f"نعتذر، تم رفض حجزك {what}. السبب: {note.strip()}"
    notify_patient(a["user_id"], text)
    return None


def cancel_appointment(appointment_id, user_id):
    a = db("SELECT * FROM appointments WHERE appointment_id=? AND user_id=?", (appointment_id, user_id), fetch="one")
    if not a or a["status"] not in (A_PENDING, A_OK):
        return "لا يمكن إلغاء هذا الحجز"
    if a["payment_status"] == PAID:
        return "الحجز مدفوع، تواصل مع الاستقبال لإلغائه"
    db("UPDATE appointments SET status=? WHERE appointment_id=?", (A_CANCEL, appointment_id), commit=True)
    return None


def set_today_presence(doctor_id, present):
    today = date.today().isoformat()
    if present:
        db("DELETE FROM doctor_absences WHERE doctor_id=? AND day=?", (doctor_id, today), commit=True)
    else:
        db("INSERT OR IGNORE INTO doctor_absences (doctor_id, day) VALUES (?,?)", (doctor_id, today), commit=True)


def add_absence(doctor_id, date_text):
    try:
        day = datetime.strptime(date_text.strip(), "%Y-%m-%d").date()
    except ValueError:
        return "صيغة التاريخ غير صحيحة (مثال: 2026-11-15)"
    if day < date.today():
        return "التاريخ سابق"
    db("INSERT OR IGNORE INTO doctor_absences (doctor_id, day) VALUES (?,?)", (doctor_id, day.isoformat()), commit=True)
    return None


# ===============================================================
# 5) المدفوعات (بوابة الدفع)
# ===============================================================
PAY_TABLES = {
    "appointment": ("appointments", "appointment_id", "fee"),
    "lab": ("lab_orders", "order_id", "price"),
    "pharmacy": ("pharmacy_orders", "order_id", "total"),
}

# البنوك المعروضة في شاشة الدفع الإلكتروني (قابلة للتعديل)
BANKS = ["بنك الخرطوم (بنكك)", "بنك فيصل الإسلامي", "بنك أم درمان الوطني", "البنك الإسلامي السوداني"]


class PaymentGateway:
    """واجهة بوابة الدفع. للربط الفعلي مع بنك أو مزوّد دفع:
    1) وقّع عقد تاجر (Merchant) مع البنك أو مزوّد الدفع واحصل على مفاتيح API.
    2) أنشئ صنفاً يرث من هذا الصنف ونفّذ charge() بنداء HTTPS للبنك، وخزّن المفاتيح في متغيرات البيئة.
    3) بدّل GATEWAY بالصنف الجديد. لا تُخزّن بيانات البطاقات أو رموز التحقق في القاعدة أبداً.
    """
    name = "base"

    def charge(self, *, bank, account, otp, amount, reference):
        """يرجع (نجح؟، رقم العملية، رسالة)"""
        raise NotImplementedError


class SandboxGateway(PaymentGateway):
    """بوابة تجريبية: لا تتصل بأي بنك ولا تحرّك أموالاً حقيقية. رمز التحقق الصحيح: 123456"""
    name = "sandbox"
    OTP = "123456"

    def charge(self, *, bank, account, otp, amount, reference):
        if bank not in BANKS:
            return False, "", "اختر البنك"
        if not account.isdigit() or len(account) < 8:
            return False, "", "رقم الحساب أو الهاتف غير صحيح (8 أرقام على الأقل)"
        if otp != self.OTP:
            return False, "", "رمز التحقق غير صحيح"
        return True, "SBX-" + secrets.token_hex(5).upper(), "تمت العملية بنجاح"


GATEWAY = SandboxGateway()


def get_payment_row(kind, ref_id):
    table, idcol, _ = PAY_TABLES[kind]
    return db(f"SELECT * FROM {table} WHERE {idcol}=?", (ref_id,), fetch="one")


def get_amount(kind, ref_id):
    row = get_payment_row(kind, ref_id)
    return int(row[PAY_TABLES[kind][2]]) if row else 0


def get_payment_state(kind, ref_id):
    row = get_payment_row(kind, ref_id)
    return row["payment_status"] if row else UNPAID


def set_payment_state(kind, ref_id, state):
    table, idcol, _ = PAY_TABLES[kind]
    db(f"UPDATE {table} SET payment_status=? WHERE {idcol}=?", (state, ref_id), commit=True)


def describe_item(kind, ref_id):
    row = get_payment_row(kind, ref_id)
    if not row:
        return ""
    if kind == "appointment":
        return f"حجز عند د. {row['doctor_name']} - {row['clinic_name']} - {row['appointment_date']}"
    if kind == "lab":
        return f"فحص مخبري: {row['test_name']}"
    return f"طلب أدوية رقم #{row['order_id']}"


def pay_electronically(kind, ref_id, user_id, bank, account, otp):
    row = get_payment_row(kind, ref_id)
    if not row:
        return False, "العنصر غير موجود"
    if row["payment_status"] == PAID:
        return False, "تم دفعه مسبقاً"
    amount = get_amount(kind, ref_id)  # المبلغ يُقرأ من القاعدة وليس من الشاشة
    ok, txn, msg = GATEWAY.charge(bank=bank, account=account.strip(), otp=otp.strip(),
                                  amount=amount, reference=f"{kind}-{ref_id}")
    if not ok:
        return False, msg
    db("""INSERT INTO payments (kind, ref_id, user_id, amount, method, bank, reference, status, created_at)
          VALUES (?,?,?,?,?,?,?,?,?)""", (kind, ref_id, user_id, amount, "electronic", bank, txn, "تم", now()),
       commit=True)
    set_payment_state(kind, ref_id, PAID)
    return True, txn


def attach_receipt(kind, ref_id, user_id, data):
    if get_payment_state(kind, ref_id) == PAID:
        return "تم دفعه مسبقاً"
    db("""INSERT INTO payments (kind, ref_id, user_id, amount, method, status, receipt, created_at)
          VALUES (?,?,?,?,?,?,?,?)""", (kind, ref_id, user_id, get_amount(kind, ref_id), "receipt", VERIFY, data, now()),
       commit=True)
    set_payment_state(kind, ref_id, VERIFY)
    return None


def staff_confirm_payment(kind, ref_id):
    """تأكيد إيصال مرفوع، أو تسجيل استلام نقدي."""
    row = get_payment_row(kind, ref_id)
    if not row or row["payment_status"] == PAID:
        return
    last = db("SELECT payment_id, method FROM payments WHERE kind=? AND ref_id=? ORDER BY payment_id DESC LIMIT 1",
              (kind, ref_id), fetch="one")
    if row["payment_status"] == VERIFY and last and last["method"] == "receipt":
        db("UPDATE payments SET status='تم' WHERE payment_id=?", (last["payment_id"],), commit=True)
    else:
        db("""INSERT INTO payments (kind, ref_id, user_id, amount, method, status, created_at)
              VALUES (?,?,?,?,?,?,?)""", (kind, ref_id, row["user_id"], get_amount(kind, ref_id), "cash", "تم", now()),
           commit=True)
    set_payment_state(kind, ref_id, PAID)


def staff_reject_receipt(kind, ref_id):
    last = db("SELECT payment_id FROM payments WHERE kind=? AND ref_id=? AND method='receipt' ORDER BY payment_id DESC LIMIT 1",
              (kind, ref_id), fetch="one")
    if last:
        db("UPDATE payments SET status='مرفوض' WHERE payment_id=?", (last["payment_id"],), commit=True)
    set_payment_state(kind, ref_id, UNPAID)


# ===============================================================
# 6) المختبر والصيدلية
# ===============================================================
def request_lab_test(user, test_id):
    t = db("SELECT * FROM lab_tests WHERE test_id=?", (test_id,), fetch="one")
    if not t:
        return None
    return db("""INSERT INTO lab_orders (user_id, patient_name, test_id, test_name, price, requested_at)
                 VALUES (?,?,?,?,?,?)""", (user["user_id"], user["full_name"], t["test_id"], t["name"],
                                          t["price"], now()), fetch="id", commit=True)


def save_lab_result(order_id, result, notes):
    o = db("SELECT * FROM lab_orders WHERE order_id=?", (order_id,), fetch="one")
    if not o:
        return "الطلب غير موجود"
    if o["payment_status"] != PAID:
        return "لا يمكن إدخال النتيجة قبل الدفع"
    if not result.strip():
        return "اكتب النتيجة"
    db("""UPDATE lab_orders SET result=?, result_notes=?, result_at=?, status='جاهزة النتيجة'
          WHERE order_id=?""", (result.strip(), notes.strip() or None, now(), order_id), commit=True)
    notify_patient(o["user_id"], f"نتيجة فحص ({o['test_name']}) جاهزة، يمكنك الاطلاع عليها من التطبيق.")
    return None


def create_pharmacy_order(user, items):
    """items: قائمة (رقم الدواء، الكمية). تُنقص الكمية من المخزون عند إنشاء الطلب."""
    conn = connect()
    try:
        rows, total = [], 0
        for med_id, qty in items:
            if qty <= 0:
                continue
            m = conn.execute("SELECT * FROM medicines WHERE med_id=?", (med_id,)).fetchone()
            if not m:
                continue
            if m["stock"] < qty:
                raise ValueError(f"المتوفر من {m['name']} هو {m['stock']} فقط")
            rows.append((m, qty))
            total += m["price"] * qty
        if not rows:
            raise ValueError("لم تحدد أي دواء")
        cur = conn.execute("""INSERT INTO pharmacy_orders (user_id, patient_name, total, created_at)
                              VALUES (?,?,?,?)""", (user["user_id"], user["full_name"], total, now()))
        oid = cur.lastrowid
        for m, qty in rows:
            conn.execute("INSERT INTO pharmacy_items (order_id, med_id, name, qty, unit_price) VALUES (?,?,?,?,?)",
                         (oid, m["med_id"], m["name"], qty, m["price"]))
            conn.execute("UPDATE medicines SET stock = stock - ? WHERE med_id=?", (qty, m["med_id"]))
        conn.commit()
        return oid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def set_pharmacy_status(order_id, status):
    o = db("SELECT * FROM pharmacy_orders WHERE order_id=?", (order_id,), fetch="one")
    if not o:
        return "الطلب غير موجود"
    if status in ("جاهز للاستلام", "تم التسليم") and o["payment_status"] != PAID:
        return "استلم الدفع أولاً قبل تأكيد الجاهزية"
    if o["status"] == "ملغي":
        return "الطلب ملغي"
    db("UPDATE pharmacy_orders SET status=? WHERE order_id=?", (status, order_id), commit=True)
    if status == "جاهز للاستلام":
        notify_patient(o["user_id"], f"طلب الأدوية رقم #{order_id} جاهز للاستلام من الصيدلية.")
    return None


def cancel_pharmacy_order(order_id):
    o = db("SELECT * FROM pharmacy_orders WHERE order_id=?", (order_id,), fetch="one")
    if not o or o["status"] in ("ملغي", "تم التسليم"):
        return "لا يمكن إلغاء هذا الطلب"
    for it in db("SELECT * FROM pharmacy_items WHERE order_id=?", (order_id,), fetch="all"):
        db("UPDATE medicines SET stock = stock + ? WHERE med_id=?", (it["qty"], it["med_id"]), commit=True)
    db("UPDATE pharmacy_orders SET status='ملغي' WHERE order_id=?", (order_id,), commit=True)
    return None


# ===============================================================
# 7) أدوات الواجهة
# ===============================================================
BLACK = ft.Colors.BLACK


def show_snack(page, text, color=ft.Colors.BLUE_700):
    page.show_dialog(ft.SnackBar(
        content=ft.Text(text, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
        bgcolor=color, duration=3500))


def ok_snack(page, text):
    show_snack(page, "✅ " + text, ft.Colors.GREEN_600)


def err_snack(page, text):
    show_snack(page, "⚠️ " + text, ft.Colors.RED_600)


def btn(text, on_click, bgcolor, color, height=45):
    return ft.Button(content=text, on_click=on_click, expand=True, height=height, bgcolor=bgcolor, color=color)


def primary(text, on_click):
    return btn(text, on_click, ft.Colors.BLUE_600, ft.Colors.WHITE)


def success(text, on_click, height=45):
    return btn(text, on_click, ft.Colors.GREEN_600, ft.Colors.WHITE, height)


def danger(text, on_click, height=40):
    return btn(text, on_click, ft.Colors.RED_100, ft.Colors.RED_900, height)


def back_btn(text, on_click):
    return btn(text, on_click, ft.Colors.GREY_300, BLACK, 40)


def h1(text, color=ft.Colors.BLUE_900):
    return ft.Text(text, size=20, weight=ft.FontWeight.BOLD, color=color)


def info(text, size=12, bold=False, color=BLACK):
    return ft.Text(text, size=size, color=color, weight=ft.FontWeight.BOLD if bold else None)


def field(label, **kw):
    return ft.TextField(label=label, color=BLACK, **kw)


def card(controls, bg=ft.Colors.BLUE_50):
    return ft.Container(content=ft.Column(controls, spacing=5), padding=12, bgcolor=bg, border_radius=10)


def state_color(s):
    if s in (PAID, A_OK, "جاهزة النتيجة", "جاهز للاستلام", "تم التسليم", "موجود"):
        return ft.Colors.GREEN_700
    if s in (UNPAID, A_REJECT, A_CANCEL, "ملغي", "غير موجود"):
        return ft.Colors.RED_600
    return ft.Colors.ORANGE_800


def badge(label, s):
    return info(f"{label}: {s}", 12, True, state_color(s))


def page_view(page, *controls, spacing=12):
    page.clean()
    page.add(ft.Column([ft.Container(height=15), *controls], spacing=spacing,
                       horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
    page.update()


def make_dropdown(label, options, value=None):
    opt = getattr(ft, "DropdownOption", None) or ft.dropdown.Option
    return ft.Dropdown(label=label, options=[opt(key=o, text=o) for o in options], value=value, color=BLACK)


def ask_note(page, title, on_submit, required=False, label="ملاحظة للمريض"):
    note = ft.TextField(label=label, multiline=True, min_lines=2, color=BLACK)
    err = ft.Text("", color=ft.Colors.RED_600, size=12)

    def ok(e):
        text = (note.value or "").strip()
        if required and not text:
            err.value = "هذا الحقل مطلوب"
            page.update()
            return
        page.pop_dialog()
        on_submit(text)

    page.show_dialog(ft.AlertDialog(
        title=ft.Text(title, size=16), content=ft.Column([note, err], tight=True),
        actions=[ft.TextButton(content="حفظ", on_click=ok),
                 ft.TextButton(content="إلغاء", on_click=lambda e: page.pop_dialog())]))


def show_receipt(page, payment_id):
    row = db("SELECT receipt FROM payments WHERE payment_id=?", (payment_id,), fetch="one")
    if not row or not row["receipt"]:
        err_snack(page, "لا توجد صورة إيصال")
        return
    page.show_dialog(ft.AlertDialog(
        title=ft.Text("صورة الإيصال", size=16),
        content=ft.Container(content=ft.Image(src=base64.b64encode(row["receipt"]).decode("ascii"),
                                              fit=ft.BoxFit.CONTAIN), width=320, height=420),
        actions=[ft.TextButton(content="إغلاق", on_click=lambda e: page.pop_dialog())]))


def payment_staff_controls(page, kind, ref_id, refresh):
    """أزرار الموظف لمراجعة الدفع: عرض الإيصال، تأكيده، رفضه، أو استلام نقدي."""
    state = get_payment_state(kind, ref_id)
    last = db("SELECT * FROM payments WHERE kind=? AND ref_id=? ORDER BY payment_id DESC LIMIT 1",
              (kind, ref_id), fetch="one")
    items = []
    if last and last["method"] == "electronic":
        items.append(info(f"💳 دفع إلكتروني: {last['bank']} — عملية {last['reference']}", 11))
    if last and last["method"] == "receipt" and last["receipt"]:
        items.append(ft.TextButton(content="🧾 عرض صورة الإيصال",
                                   on_click=lambda e, p=last["payment_id"]: show_receipt(page, p)))
    if state != PAID:
        def confirm(e):
            staff_confirm_payment(kind, ref_id)
            refresh()
            ok_snack(page, "تم تسجيل الدفع")

        def reject(e):
            staff_reject_receipt(kind, ref_id)
            refresh()
            show_snack(page, "تم رفض الإيصال")

        if state == VERIFY:
            items.append(ft.Row([success("✅ تأكيد الإيصال", confirm, 38), danger("رفض الإيصال", reject, 38)], spacing=8))
        else:
            items.append(btn("💵 استلام الدفع نقداً", confirm, ft.Colors.TEAL_100, ft.Colors.TEAL_900, 38))
    return items


def read_picked_file(f):
    try:
        if getattr(f, "path", None):
            with open(f.path, "rb") as fh:
                return fh.read()
        if getattr(f, "bytes", None):
            return f.bytes
    except Exception:
        pass
    return None


# ===============================================================
# 8) الدخول وإنشاء الحساب
# ===============================================================
def go_home(page):
    user = STATE["user"]
    if not user:
        return show_login(page)
    {"patient": show_patient_home, "reception": show_reception_home, "doctor": show_doctor_home,
     "lab": show_lab_home, "pharmacy": show_pharmacy_home, "admin": show_admin_home}[user["role"]](page)


def require(page, role):
    user = STATE["user"]
    if not user or user["role"] != role:
        show_login(page)
        return False
    return True


def logout(page):
    STATE["user"] = None
    show_home(page)


def contact_card():
    return card([info("📞 للتواصل والاستفسار", 13, True), info(f"هاتف المستشفى: {HOSPITAL_PHONE}"),
                 info(f"📍 العنوان: {HOSPITAL_ADDRESS}")], ft.Colors.GREY_100)


def login_required_dialog(page):
    page.show_dialog(ft.AlertDialog(
        title=ft.Text("يلزم تسجيل الدخول", size=16),
        content=ft.Text("الحجز وطلب الفحوصات والأدوية متاح للمرضى المسجلين فقط. سجّل الدخول أو أنشئ حساباً للمتابعة."),
        actions=[ft.TextButton(content="تسجيل الدخول", on_click=lambda e: (page.pop_dialog(), show_login(page))),
                 ft.TextButton(content="إنشاء حساب", on_click=lambda e: (page.pop_dialog(), show_register(page))),
                 ft.TextButton(content="إلغاء", on_click=lambda e: page.pop_dialog())]))


def show_home(page):
    """الشاشة الرئيسية: أول ما يراه أي شخص قبل تسجيل الدخول."""
    STATE["user"] = None
    page_view(page,
              ft.Container(height=10),
              ft.Text(HOSPITAL_NAME, size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900,
                      text_align=ft.TextAlign.CENTER),
              ft.Text("نظام الحجز الإلكتروني", size=14, color=ft.Colors.GREY_700, text_align=ft.TextAlign.CENTER),
              ft.Text("احجز موعدك واطلب فحوصاتك وأدويتك بدون عناء الانتظار.", size=13, color=BLACK,
                      text_align=ft.TextAlign.CENTER),
              ft.Container(height=5),
              primary("🔑 تسجيل الدخول", lambda e: show_login(page)),
              btn("➕ إنشاء حساب جديد", lambda e: show_register(page), ft.Colors.GREEN_100, ft.Colors.GREEN_900),
              btn("👁️ تصفح كزائر", lambda e: show_guest_home(page), ft.Colors.GREY_200, BLACK),
              ft.Divider(),
              card([info("خدماتنا", 14, True),
                    info("🏥 4 عيادات وعدة أطباء في كل عيادة"),
                    info(f"📅 تذكرة الموعد: {money(APPOINTMENT_FEE)}"),
                    info(f"🧪 فحوصات مخبرية (ملاريا - التهاب - تايفويد): {money(LAB_TEST_PRICE)} للفحص"),
                    info("💊 صيدلية المستشفى"),
                    info("💳 دفع إلكتروني أو تحويل بنكي")]),
              contact_card())


def show_guest_home(page):
    STATE["user"] = None
    page_view(page, h1("👁️ تصفح كزائر"),
              info("يمكنك الاطلاع على العيادات والأطباء والأسعار. الحجز يتطلب حساباً.", 12, False, ft.Colors.GREY_700),
              btn("🏥 العيادات والأطباء", lambda e: show_clinics(page, guest=True), ft.Colors.BLUE_50, ft.Colors.BLUE_900),
              btn("🧪 الفحوصات المخبرية وأسعارها", lambda e: show_lab_catalog(page, guest=True), ft.Colors.BLUE_50, ft.Colors.BLUE_900),
              contact_card(),
              ft.Divider(),
              primary("🔑 تسجيل الدخول للحجز", lambda e: show_login(page)),
              back_btn("← الرئيسية", lambda e: show_home(page)))


def show_login(page):
    STATE["user"] = None
    ident = field("الرقم الوطني أو اسم المستخدم")
    pw = field("كلمة السر", password=True, can_reveal_password=True)

    def do_login(e):
        user, err = authenticate(ident.value or "", pw.value or "")
        if err:
            err_snack(page, err)
            return
        STATE["user"] = user
        if user["must_change"]:
            show_change_password(page, forced=True)
        else:
            go_home(page)

    page_view(page,
              ft.Container(height=15),
              ft.Text(HOSPITAL_NAME, size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
              ft.Text("نظام الحجز الإلكتروني", size=14, color=ft.Colors.GREY_700),
              ft.Container(height=10),
              ident, pw,
              primary("تسجيل الدخول", do_login),
              ft.Divider(),
              info("مريض جديد؟", 13),
              btn("إنشاء حساب جديد", lambda e: show_register(page), ft.Colors.GREEN_100, ft.Colors.GREEN_900),
              back_btn("← الرئيسية", lambda e: show_home(page)))


def show_register(page):
    name = field("الاسم الكامل", text_align=ft.TextAlign.RIGHT)
    nat = field("الرقم الوطني (11 رقماً)", keyboard_type=ft.KeyboardType.NUMBER, max_length=11)
    phone = field("رقم الهاتف (09xxxxxxxx)", keyboard_type=ft.KeyboardType.PHONE, max_length=10)
    pw = field("كلمة السر (6 أحرف على الأقل)", password=True, can_reveal_password=True)
    pw2 = field("تأكيد كلمة السر", password=True, can_reveal_password=True)

    def do_register(e):
        user, err = register_patient(name.value or "", nat.value or "", phone.value or "",
                                     pw.value or "", pw2.value or "")
        if err:
            err_snack(page, err)
            return
        STATE["user"] = user
        go_home(page)
        ok_snack(page, "تم إنشاء حسابك بنجاح")

    page_view(page, h1("إنشاء حساب جديد"), name, nat, phone, pw, pw2,
              success("إنشاء الحساب", do_register, 50),
              back_btn("← العودة لتسجيل الدخول", lambda e: show_login(page)),
              back_btn("← الرئيسية", lambda e: show_home(page)))


def show_change_password(page, forced=False):
    user = STATE["user"]
    cur = field("كلمة السر الحالية", password=True, can_reveal_password=True)
    new = field("كلمة السر الجديدة", password=True, can_reveal_password=True)
    new2 = field("تأكيد كلمة السر الجديدة", password=True, can_reveal_password=True)

    def save(e):
        err = change_password(user["user_id"], cur.value or "", new.value or "", new2.value or "")
        if err:
            err_snack(page, err)
            return
        STATE["user"] = get_user(user["user_id"])
        go_home(page)
        ok_snack(page, "تم تغيير كلمة السر")

    controls = [h1("تغيير كلمة السر")]
    if forced:
        controls.append(info("هذا أول دخول لك بكلمة سر افتراضية، يجب تغييرها الآن.", 12, True, ft.Colors.ORANGE_800))
    controls += [cur, new, new2, primary("حفظ", save)]
    controls.append(back_btn("خروج", lambda e: logout(page)) if forced else back_btn("← رجوع", lambda e: go_home(page)))
    page_view(page, *controls)


def header(page, subtitle=""):
    user = STATE["user"]
    return ft.Column([
        info(f"مرحباً: {user['full_name']} ({ROLE_NAMES[user['role']]})", 14, True, ft.Colors.GREEN_700),
        info(subtitle, 12, False, ft.Colors.GREY_700) if subtitle else ft.Container(height=0),
    ], spacing=2)


def footer(page):
    return ft.Row([
        btn("🔑 كلمة السر", lambda e: show_change_password(page), ft.Colors.GREY_200, BLACK, 38),
        btn("🚪 خروج", lambda e: logout(page), ft.Colors.RED_100, ft.Colors.RED_900, 38),
    ], spacing=10)


# ===============================================================
# 9) المريض
# ===============================================================
def show_patient_home(page):
    if not require(page, "patient"):
        return
    page_view(page, header(page), h1("ماذا تريد أن تفعل؟"),
              btn("📅 حجز موعد عند طبيب", lambda e: show_clinics(page), ft.Colors.BLUE_50, ft.Colors.BLUE_900),
              btn("📋 مواعيدي", lambda e: show_my_appointments(page), ft.Colors.ORANGE_100, ft.Colors.ORANGE_900),
              ft.Divider(),
              btn("🧪 طلب فحص مخبري", lambda e: show_lab_catalog(page), ft.Colors.BLUE_50, ft.Colors.BLUE_900),
              btn("📄 فحوصاتي ونتائجها", lambda e: show_my_lab(page), ft.Colors.ORANGE_100, ft.Colors.ORANGE_900),
              ft.Divider(),
              btn("💊 طلب أدوية من الصيدلية", lambda e: show_pharmacy_catalog(page), ft.Colors.BLUE_50, ft.Colors.BLUE_900),
              btn("🛍️ طلباتي من الصيدلية", lambda e: show_my_pharmacy(page), ft.Colors.ORANGE_100, ft.Colors.ORANGE_900),
              ft.Divider(), footer(page))


def show_clinics(page, guest=False):
    if not guest and not require(page, "patient"):
        return
    page_view(page, h1("العيادات" if guest else "اختر العيادة المطلوبة"),
              *[btn(c, lambda e, c=c: show_doctors(page, c, guest), ft.Colors.BLUE_50, ft.Colors.BLUE_900) for c in CLINICS],
              back_btn("← رجوع", lambda e: show_guest_home(page) if guest else go_home(page)))


def show_doctors(page, clinic, guest=False):
    if not guest and not require(page, "patient"):
        return
    docs = db("SELECT * FROM doctors WHERE clinic=? ORDER BY doctor_id", (clinic,), fetch="all")
    cards = []
    for d in docs:
        present, why = doctor_available_on(d["doctor_id"], date.today())
        if present:
            today_state = "موجود"
        elif parse_days(d["work_days"]) and date.today().weekday() in parse_days(d["work_days"]):
            today_state = "غير موجود"
        else:
            today_state = "لا يعمل اليوم"
        cards.append(card([
            info(f"د. {d['name']}", 15, True),
            info(f"{d['specialty']} — {days_text(d['work_days'])} — {d['hours']}"),
            badge("اليوم", today_state),
            btn("🔒 سجّل الدخول للحجز", lambda e: login_required_dialog(page), ft.Colors.GREY_200, BLACK, 40) if guest
            else success("📅 حجز موعد", lambda e, i=d["doctor_id"]: show_booking(page, i), 40),
        ]))
    page_view(page, h1(f"أطباء {clinic}"), *cards, back_btn("← العيادات", lambda e: show_clinics(page, guest)))


def show_booking(page, doctor_id):
    if not require(page, "patient"):
        return
    user = STATE["user"]
    d = db("SELECT * FROM doctors WHERE doctor_id=?", (doctor_id,), fetch="one")
    date_field = field("تاريخ الموعد (مثال: 2026-11-15)")

    def confirm(e):
        aid, err = book_appointment(user, doctor_id, date_field.value or "")
        if err:
            err_snack(page, err)
            return
        show_payment(page, "appointment", aid, lambda: show_my_appointments(page))

    page_view(page, h1("حجز موعد جديد"),
              card([info(f"د. {d['name']} — {d['clinic']}", 14, True),
                    info(f"أيام العمل: {days_text(d['work_days'])} — {d['hours']}")]),
              info(f"سعر تذكرة الموعد: {money(APPOINTMENT_FEE)}", 12, True, ft.Colors.GREY_800),
              date_field,
              info("بعد التأكيد تنتقل لاختيار طريقة الدفع، ثم يراجع موظف الاستقبال الحجز ويؤكده.", 11, False, ft.Colors.GREY_700),
              success("متابعة", confirm, 50),
              back_btn("← الأطباء", lambda e: show_doctors(page, d["clinic"])))


def show_payment(page, kind, ref_id, back):
    """شاشة الدفع المشتركة: حجز - فحص - أدوية."""
    user = STATE["user"]
    if get_payment_state(kind, ref_id) == PAID:
        back()
        return
    amount = get_amount(kind, ref_id)
    receipt = {"data": None}
    status = info("لم يتم إرفاق صورة", 12, False, ft.Colors.RED_600)
    preview = ft.Image(src="", height=160, fit=ft.BoxFit.CONTAIN, visible=False)

    async def pick(e):
        files = await STATE["picker"].pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)
        if not files:
            return
        data = read_picked_file(files[0])
        if not data:
            err_snack(page, "تعذر قراءة الصورة، حاول مرة أخرى")
            return
        if len(data) > MAX_RECEIPT_MB * 1024 * 1024:
            err_snack(page, f"حجم الصورة أكبر من {MAX_RECEIPT_MB} ميجا")
            return
        receipt["data"] = data
        status.value = f"تم اختيار الصورة: {files[0].name}"
        status.color = ft.Colors.GREEN_700
        preview.src = base64.b64encode(data).decode("ascii")
        preview.visible = True
        page.update()

    def send_receipt(e):
        if not receipt["data"]:
            err_snack(page, "اختر صورة الإيصال أولاً")
            return
        err = attach_receipt(kind, ref_id, user["user_id"], receipt["data"])
        if err:
            err_snack(page, err)
            return
        back()
        ok_snack(page, "تم إرسال الإيصال، بانتظار تحقق الموظف")

    page_view(page, h1("الدفع"),
              card([info(describe_item(kind, ref_id), 13, True), info(f"المبلغ المطلوب: {money(amount)}", 14, True, ft.Colors.RED_700)]),
              primary("💳 دفع إلكتروني عبر البنك", lambda e: show_electronic_payment(page, kind, ref_id, back)),
              ft.Divider(),
              info(f"أو حوّل المبلغ على حسابنا ({BANK_ACCOUNT_TEXT}) وأرفق صورة الإيصال:", 12),
              btn("📎 اختيار صورة الإيصال", pick, ft.Colors.WHITE, ft.Colors.BLUE_900),
              status, preview,
              success("إرسال الإيصال", send_receipt),
              ft.Divider(),
              back_btn("الدفع لاحقاً (في الاستقبال)", lambda e: back()))


def show_electronic_payment(page, kind, ref_id, back):
    user = STATE["user"]
    amount = get_amount(kind, ref_id)
    bank = make_dropdown("البنك", BANKS)
    account = field("رقم الحساب أو رقم الهاتف المرتبط بالمحفظة", keyboard_type=ft.KeyboardType.NUMBER, max_length=16)
    otp = field("رمز التحقق (التجريبي: 123456)", keyboard_type=ft.KeyboardType.NUMBER, max_length=6)

    def pay(e):
        ok, msg = pay_electronically(kind, ref_id, user["user_id"], bank.value or "", account.value or "", otp.value or "")
        if not ok:
            err_snack(page, msg)
            return
        back()
        ok_snack(page, f"تم الدفع بنجاح — رقم العملية {msg}")

    page_view(page, h1("الدفع الإلكتروني"),
              card([info(describe_item(kind, ref_id), 13, True), info(f"المبلغ: {money(amount)}", 14, True, ft.Colors.RED_700)]),
              info("⚠️ البوابة الحالية تجريبية ولا تحرّك أموالاً حقيقية.", 11, True, ft.Colors.ORANGE_800),
              bank, account, otp,
              success(f"دفع {money(amount)}", pay, 50),
              back_btn("← رجوع", lambda e: show_payment(page, kind, ref_id, back)))


def show_my_appointments(page):
    if not require(page, "patient"):
        return
    user = STATE["user"]
    rows = db("SELECT * FROM appointments WHERE user_id=? ORDER BY appointment_id DESC", (user["user_id"],), fetch="all")

    def cancel(aid):
        err = cancel_appointment(aid, user["user_id"])
        show_my_appointments(page)
        err_snack(page, err) if err else show_snack(page, "تم إلغاء الحجز", ft.Colors.ORANGE_700)

    cards = [info("لا توجد مواعيد محجوزة", 13, False, ft.Colors.GREY_600)] if not rows else []
    for a in rows:
        items = [info(f"رقم الحجز: #{a['appointment_id']}", 12, True),
                 info(f"👨‍⚕️ د. {a['doctor_name']} / {a['clinic_name']}"),
                 info(f"📅 {a['appointment_date']}"),
                 badge("حالة الحجز", a["status"]), badge("💳 الدفع", a["payment_status"])]
        if a["staff_note"]:
            items.append(info(f"💬 ملاحظة الاستقبال: {a['staff_note']}", 12, True, ft.Colors.PURPLE_800))
        if a["status"] in (A_PENDING, A_OK) and a["payment_status"] != PAID:
            items.append(success("💳 ادفع الآن", lambda e, i=a["appointment_id"]: show_payment(
                page, "appointment", i, lambda: show_my_appointments(page)), 38))
        if a["status"] in (A_PENDING, A_OK) and a["payment_status"] != PAID:
            items.append(danger("إلغاء الحجز", lambda e, i=a["appointment_id"]: cancel(i), 36))
        cards.append(card(items))
    page_view(page, h1("📋 مواعيدي"), *cards, back_btn("← الرئيسية", lambda e: go_home(page)), spacing=10)


# ---- المختبر (المريض) ----
def show_lab_catalog(page, guest=False):
    if not guest and not require(page, "patient"):
        return
    user = STATE["user"]
    tests = db("SELECT * FROM lab_tests ORDER BY test_id", (), fetch="all")

    def order(tid):
        oid = request_lab_test(user, tid)
        show_payment(page, "lab", oid, lambda: show_my_lab(page))

    cards = [card([info(t["name"], 14, True), info(f"السعر: {money(t['price'])}"),
                   btn("🔒 سجّل الدخول للطلب", lambda e: login_required_dialog(page), ft.Colors.GREY_200, BLACK, 38) if guest
                   else success("طلب الفحص والدفع", lambda e, i=t["test_id"]: order(i), 38)]) for t in tests]
    page_view(page, h1("🧪 الفحوصات المخبرية"), *cards,
              back_btn("← رجوع", lambda e: show_guest_home(page) if guest else go_home(page)))


def show_my_lab(page):
    if not require(page, "patient"):
        return
    user = STATE["user"]
    rows = db("SELECT * FROM lab_orders WHERE user_id=? ORDER BY order_id DESC", (user["user_id"],), fetch="all")
    cards = [info("لا توجد فحوصات", 13, False, ft.Colors.GREY_600)] if not rows else []
    for o in rows:
        items = [info(f"فحص #{o['order_id']}: {o['test_name']}", 13, True), info(f"📅 {o['requested_at']}"),
                 badge("💳 الدفع", o["payment_status"]), badge("الحالة", o["status"])]
        if o["result"]:
            items.append(info(f"النتيجة: {o['result']}", 14, True, ft.Colors.BLUE_900))
            if o["result_notes"]:
                items.append(info(f"ملاحظات: {o['result_notes']}"))
        if o["payment_status"] != PAID:
            items.append(success("💳 ادفع الآن", lambda e, i=o["order_id"]: show_payment(
                page, "lab", i, lambda: show_my_lab(page)), 38))
        cards.append(card(items))
    page_view(page, h1("📄 فحوصاتي"), *cards, back_btn("← الرئيسية", lambda e: go_home(page)), spacing=10)


# ---- الصيدلية (المريض) ----
def show_pharmacy_catalog(page):
    if not require(page, "patient"):
        return
    user = STATE["user"]
    meds = db("SELECT * FROM medicines WHERE stock > 0 ORDER BY name", (), fetch="all")
    qty_fields = {}
    rows = []
    for m in meds:
        qf = ft.TextField(value="0", width=70, color=BLACK, keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.CENTER)
        qty_fields[m["med_id"]] = qf
        rows.append(card([info(m["name"], 13, True), info(f"{money(m['price'])} — المتوفر: {m['stock']}"),
                          ft.Row([info("الكمية:"), qf], spacing=8)]))

    def submit(e):
        items = []
        for med_id, qf in qty_fields.items():
            try:
                q = int((qf.value or "0").strip() or 0)
            except ValueError:
                err_snack(page, "الكمية يجب أن تكون رقماً")
                return
            if q < 0:
                err_snack(page, "الكمية لا يمكن أن تكون سالبة")
                return
            items.append((med_id, q))
        try:
            oid = create_pharmacy_order(user, items)
        except ValueError as ex:
            err_snack(page, str(ex))
            return
        show_payment(page, "pharmacy", oid, lambda: show_my_pharmacy(page))

    body = rows or [info("لا توجد أدوية متوفرة حالياً", 13, False, ft.Colors.GREY_600)]
    page_view(page, h1("💊 صيدلية المستشفى"), *body,
              success("إنشاء الطلب والمتابعة للدفع", submit, 50),
              back_btn("← الرئيسية", lambda e: go_home(page)), spacing=10)


def show_my_pharmacy(page):
    if not require(page, "patient"):
        return
    user = STATE["user"]
    rows = db("SELECT * FROM pharmacy_orders WHERE user_id=? ORDER BY order_id DESC", (user["user_id"],), fetch="all")
    cards = [info("لا توجد طلبات", 13, False, ft.Colors.GREY_600)] if not rows else []
    for o in rows:
        its = db("SELECT * FROM pharmacy_items WHERE order_id=?", (o["order_id"],), fetch="all")
        items = [info(f"طلب #{o['order_id']} — {o['created_at']}", 13, True)]
        items += [info(f"• {i['name']} × {i['qty']}") for i in its]
        items += [info(f"الإجمالي: {money(o['total'])}", 12, True), badge("💳 الدفع", o["payment_status"]),
                  badge("الحالة", o["status"])]
        if o["status"] == "جاهز للاستلام":
            items.append(info("✅ طلبك جاهز، تفضل بالاستلام من الصيدلية.", 12, True, ft.Colors.GREEN_700))
        if o["payment_status"] != PAID and o["status"] != "ملغي":
            items.append(success("💳 ادفع الآن", lambda e, i=o["order_id"]: show_payment(
                page, "pharmacy", i, lambda: show_my_pharmacy(page)), 38))
        cards.append(card(items))
    page_view(page, h1("🛍️ طلباتي من الصيدلية"), *cards, back_btn("← الرئيسية", lambda e: go_home(page)), spacing=10)


# ===============================================================
# 10) موظف الاستقبال
# ===============================================================
def show_reception_home(page, only_pending=True):
    if not require(page, "reception"):
        return
    where = "WHERE a.status=?" if only_pending else "WHERE ?"
    rows = db(f"""SELECT a.*, u.phone FROM appointments a LEFT JOIN users u ON a.user_id=u.user_id
                  {where} ORDER BY a.appointment_id DESC LIMIT 100""",
              (A_PENDING if only_pending else 1,), fetch="all")
    refresh = lambda: show_reception_home(page, only_pending)

    def review(aid, approve):
        def submit(note):
            err = review_appointment(aid, approve, note)
            refresh()
            err_snack(page, err) if err else ok_snack(page, "تم تأكيد الحجز" if approve else "تم رفض الحجز")
        ask_note(page, "تأكيد الحجز" if approve else "رفض الحجز", submit, required=not approve,
                 label="ملاحظة للمريض (اختياري)" if approve else "سبب الرفض (إلزامي)")

    cards = [info("لا توجد حجوزات", 13, False, ft.Colors.GREY_600)] if not rows else []
    for a in rows:
        items = [info(f"#{a['appointment_id']} — {a['patient_name']}", 14, True),
                 info(f"📞 {a['phone'] or '—'}"),
                 info(f"👨‍⚕️ د. {a['doctor_name']} / {a['clinic_name']}"),
                 info(f"📅 {a['appointment_date']}"),
                 badge("الحجز", a["status"]), badge("💳 الدفع", a["payment_status"])]
        if a["staff_note"]:
            items.append(info(f"💬 {a['staff_note']}", 12, False, ft.Colors.PURPLE_800))
        if a["status"] == A_PENDING:
            items += payment_staff_controls(page, "appointment", a["appointment_id"], refresh)
            items.append(ft.Row([success("✅ تأكيد الحجز", lambda e, i=a["appointment_id"]: review(i, True), 40),
                                 danger("❌ رفض", lambda e, i=a["appointment_id"]: review(i, False), 40)], spacing=8))
        cards.append(card(items))
    page_view(page, header(page, "لوحة الاستقبال"), h1("الحجوزات"),
              ft.Row([btn("بانتظار التأكيد", lambda e: show_reception_home(page, True),
                          ft.Colors.BLUE_600 if only_pending else ft.Colors.GREY_200,
                          ft.Colors.WHITE if only_pending else BLACK, 38),
                      btn("كل الحجوزات", lambda e: show_reception_home(page, False),
                          ft.Colors.GREY_200 if only_pending else ft.Colors.BLUE_600,
                          BLACK if only_pending else ft.Colors.WHITE, 38)], spacing=8),
              *cards, footer(page), spacing=10)


# ===============================================================
# 11) الطبيب
# ===============================================================
def show_doctor_home(page):
    if not require(page, "doctor"):
        return
    user = STATE["user"]
    d = db("SELECT * FROM doctors WHERE user_id=?", (user["user_id"],), fetch="one")
    if not d:
        err_snack(page, "حسابك غير مرتبط بطبيب")
        return logout(page)
    did = d["doctor_id"]
    today = date.today()
    works_today = today.weekday() in parse_days(d["work_days"])
    present, _ = doctor_available_on(did, today)

    def toggle(e):
        set_today_presence(did, not present)
        show_doctor_home(page)
        show_snack(page, "تم تسجيلك: غير موجود اليوم" if present else "تم تسجيلك: موجود اليوم",
                   ft.Colors.ORANGE_700 if present else ft.Colors.GREEN_600)

    abs_date = field("تاريخ غياب قادم (مثال: 2026-11-15)")

    def add_abs(e):
        err = add_absence(d["doctor_id"], abs_date.value or "")
        show_doctor_home(page)
        err_snack(page, err) if err else show_snack(page, "تم تسجيل الغياب", ft.Colors.ORANGE_700)

    def remove_abs(day):
        db("DELETE FROM doctor_absences WHERE doctor_id=? AND day=?", (did, day), commit=True)
        show_doctor_home(page)

    absences = db("SELECT day FROM doctor_absences WHERE doctor_id=? AND day>=? ORDER BY day",
                  (did, today.isoformat()), fetch="all")
    abs_rows = [ft.Row([info(f"❌ {a['day']}"), ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED_600,
                                                              tooltip="إلغاء الغياب",
                                                              on_click=lambda e, dd=a["day"]: remove_abs(dd))],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN) for a in absences]

    appts = db("""SELECT * FROM appointments WHERE doctor_id=? AND status=? AND appointment_date>=?
                  ORDER BY appointment_date, appointment_id""", (did, A_OK, today.isoformat()), fetch="all")
    appt_cards = [card([info(f"📅 {a['appointment_date']} — {a['patient_name']}", 13, True)]) for a in appts] \
        or [info("لا توجد حجوزات مؤكدة قادمة", 12, False, ft.Colors.GREY_600)]

    if not works_today:
        status_text, status_val = "اليوم خارج أيام عملك", "لا يعمل اليوم"
    else:
        status_text, status_val = "حالتك اليوم", "موجود" if present else "غير موجود"

    controls = [header(page, f"{d['clinic']} — {d['specialty']}"), h1("جدول العمل"),
                card([info(f"أيام العمل: {days_text(d['work_days'])} — {d['hours']}"), badge(status_text, status_val)])]
    if works_today:
        controls.append(btn("❌ تسجيل: غير موجود اليوم" if present else "✅ تسجيل: موجود اليوم", toggle,
                            ft.Colors.RED_100 if present else ft.Colors.GREEN_100,
                            ft.Colors.RED_900 if present else ft.Colors.GREEN_900))
    controls += [info("أيام الغياب القادمة", 14, True), *abs_rows, abs_date,
                 btn("إضافة يوم غياب", add_abs, ft.Colors.ORANGE_100, ft.Colors.ORANGE_900, 40),
                 ft.Divider(), h1("حجوزاتي المؤكدة القادمة"), *appt_cards, footer(page)]
    page_view(page, *controls, spacing=10)


# ===============================================================
# 12) فني المختبر
# ===============================================================
def show_lab_home(page, only_open=True):
    if not require(page, "lab"):
        return
    rows = db("SELECT * FROM lab_orders WHERE status!=? ORDER BY order_id DESC LIMIT 100" if only_open
              else "SELECT * FROM lab_orders WHERE ? ORDER BY order_id DESC LIMIT 100",
              ("جاهزة النتيجة" if only_open else 1,), fetch="all")
    refresh = lambda: show_lab_home(page, only_open)

    def enter_result(oid):
        result = ft.TextField(label="النتيجة (مثال: سلبي / إيجابي)", color=BLACK)
        notes = ft.TextField(label="ملاحظات (اختياري)", multiline=True, min_lines=2, color=BLACK)
        err = ft.Text("", color=ft.Colors.RED_600, size=12)

        def save(e):
            msg = save_lab_result(oid, result.value or "", notes.value or "")
            if msg:
                err.value = msg
                page.update()
                return
            page.pop_dialog()
            refresh()
            ok_snack(page, "تم حفظ النتيجة")

        page.show_dialog(ft.AlertDialog(
            title=ft.Text("إدخال نتيجة الفحص", size=16), content=ft.Column([result, notes, err], tight=True),
            actions=[ft.TextButton(content="حفظ", on_click=save),
                     ft.TextButton(content="إلغاء", on_click=lambda e: page.pop_dialog())]))

    cards = [info("لا توجد طلبات", 13, False, ft.Colors.GREY_600)] if not rows else []
    for o in rows:
        items = [info(f"#{o['order_id']} — {o['test_name']}", 14, True), info(f"👤 {o['patient_name']}"),
                 info(f"📅 {o['requested_at']} — {money(o['price'])}"),
                 badge("💳 الدفع", o["payment_status"]), badge("الحالة", o["status"])]
        if o["result"]:
            items.append(info(f"النتيجة: {o['result']}", 13, True, ft.Colors.BLUE_900))
        items += payment_staff_controls(page, "lab", o["order_id"], refresh)
        if o["payment_status"] == PAID and o["status"] != "جاهزة النتيجة":
            items.append(primary("📝 إدخال النتيجة", lambda e, i=o["order_id"]: enter_result(i)))
        cards.append(card(items))
    page_view(page, header(page, "المختبر"), h1("طلبات الفحوصات"),
              ft.Row([btn("قيد الفحص", lambda e: show_lab_home(page, True),
                          ft.Colors.BLUE_600 if only_open else ft.Colors.GREY_200, ft.Colors.WHITE if only_open else BLACK, 38),
                      btn("الكل", lambda e: show_lab_home(page, False),
                          ft.Colors.GREY_200 if only_open else ft.Colors.BLUE_600, BLACK if only_open else ft.Colors.WHITE, 38)],
                     spacing=8),
              *cards, footer(page), spacing=10)


# ===============================================================
# 13) الصيدلي
# ===============================================================
def show_pharmacy_home(page, only_open=True):
    if not require(page, "pharmacy"):
        return
    rows = db("SELECT * FROM pharmacy_orders WHERE status IN ('قيد التجهيز','جاهز للاستلام') ORDER BY order_id DESC LIMIT 100"
              if only_open else "SELECT * FROM pharmacy_orders ORDER BY order_id DESC LIMIT 100", (), fetch="all")
    refresh = lambda: show_pharmacy_home(page, only_open)

    def set_status(oid, status):
        err = set_pharmacy_status(oid, status)
        refresh()
        err_snack(page, err) if err else ok_snack(page, "تم تحديث حالة الطلب")

    def cancel(oid):
        err = cancel_pharmacy_order(oid)
        refresh()
        err_snack(page, err) if err else show_snack(page, "تم إلغاء الطلب وإرجاع الكميات للمخزون", ft.Colors.ORANGE_700)

    cards = [info("لا توجد طلبات", 13, False, ft.Colors.GREY_600)] if not rows else []
    for o in rows:
        its = db("SELECT * FROM pharmacy_items WHERE order_id=?", (o["order_id"],), fetch="all")
        items = [info(f"طلب #{o['order_id']} — 👤 {o['patient_name']}", 14, True)]
        items += [info(f"• {i['name']} × {i['qty']}") for i in its]
        items += [info(f"الإجمالي: {money(o['total'])}", 12, True), badge("💳 الدفع", o["payment_status"]),
                  badge("الحالة", o["status"])]
        if o["status"] not in ("ملغي", "تم التسليم"):
            items += payment_staff_controls(page, "pharmacy", o["order_id"], refresh)
            if o["status"] == "قيد التجهيز":
                items.append(success("📦 تأكيد جاهزية الطلب", lambda e, i=o["order_id"]: set_status(i, "جاهز للاستلام"), 40))
            if o["status"] == "جاهز للاستلام":
                items.append(primary("🤝 تم تسليم الطلب", lambda e, i=o["order_id"]: set_status(i, "تم التسليم")))
            items.append(danger("إلغاء الطلب", lambda e, i=o["order_id"]: cancel(i), 36))
        cards.append(card(items))
    page_view(page, header(page, "الصيدلية"), h1("طلبات الأدوية"),
              ft.Row([btn("الطلبات المفتوحة", lambda e: show_pharmacy_home(page, True),
                          ft.Colors.BLUE_600 if only_open else ft.Colors.GREY_200, ft.Colors.WHITE if only_open else BLACK, 38),
                      btn("الكل", lambda e: show_pharmacy_home(page, False),
                          ft.Colors.GREY_200 if only_open else ft.Colors.BLUE_600, BLACK if only_open else ft.Colors.WHITE, 38)],
                     spacing=8),
              btn("📦 المخزون والأسعار", lambda e: show_pharmacy_stock(page), ft.Colors.PURPLE_100, ft.Colors.PURPLE_900),
              *cards, footer(page), spacing=10)


def show_pharmacy_stock(page):
    if not require(page, "pharmacy"):
        return
    meds = db("SELECT * FROM medicines ORDER BY name", (), fetch="all")
    editors = []
    rows = []
    for m in meds:
        price = ft.TextField(label="السعر", value=str(m["price"]), width=110, color=BLACK, keyboard_type=ft.KeyboardType.NUMBER)
        stock = ft.TextField(label="المخزون", value=str(m["stock"]), width=100, color=BLACK, keyboard_type=ft.KeyboardType.NUMBER)
        editors.append((m["med_id"], price, stock))
        rows.append(card([info(m["name"], 13, True), ft.Row([price, stock], spacing=8)]))

    def save_all(e):
        try:
            for med_id, p, s in editors:
                pv, sv = int(p.value), int(s.value)
                if pv < 0 or sv < 0:
                    raise ValueError
                db("UPDATE medicines SET price=?, stock=? WHERE med_id=?", (pv, sv, med_id), commit=True)
        except ValueError:
            err_snack(page, "السعر والمخزون يجب أن يكونا أرقاماً موجبة")
            return
        ok_snack(page, "تم حفظ التعديلات")

    new_name = field("اسم دواء جديد")
    new_price = field("السعر", keyboard_type=ft.KeyboardType.NUMBER)
    new_stock = field("الكمية", keyboard_type=ft.KeyboardType.NUMBER)

    def add_med(e):
        try:
            name, pv, sv = (new_name.value or "").strip(), int(new_price.value), int(new_stock.value)
            if not name or pv < 0 or sv < 0:
                raise ValueError
            db("INSERT INTO medicines (name, price, stock) VALUES (?,?,?)", (name, pv, sv), commit=True)
        except ValueError:
            err_snack(page, "أدخل الاسم والسعر والكمية بشكل صحيح")
            return
        except sqlite3.IntegrityError:
            err_snack(page, "هذا الدواء موجود مسبقاً")
            return
        show_pharmacy_stock(page)
        ok_snack(page, "تمت إضافة الدواء")

    page_view(page, h1("📦 المخزون والأسعار"), *rows, success("حفظ التعديلات", save_all),
              ft.Divider(), info("إضافة دواء جديد", 14, True), new_name, new_price, new_stock,
              btn("إضافة", add_med, ft.Colors.PURPLE_100, ft.Colors.PURPLE_900),
              back_btn("← الطلبات", lambda e: show_pharmacy_home(page)), spacing=10)


# ===============================================================
# 14) المدير
# ===============================================================
def show_admin_home(page):
    if not require(page, "admin"):
        return
    def count(sql, params=()):
        return db(sql, params, fetch="one")[0]

    patients = count("SELECT COUNT(*) FROM users WHERE role='patient'")
    doctors = count("SELECT COUNT(*) FROM doctors")
    total_appts = count("SELECT COUNT(*) FROM appointments")
    pending = count("SELECT COUNT(*) FROM appointments WHERE status=?", (A_PENDING,))
    revenue = count("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='تم'")
    page_view(page, header(page, "لوحة الإدارة"), h1("نظرة عامة", ft.Colors.PURPLE_800),
              card([info(f"المرضى المسجلون: {patients}"),
                    info(f"الأطباء: {doctors}"),
                    info(f"الحجوزات: {total_appts} (بانتظار التأكيد: {pending})"),
                    info(f"إجمالي المدفوعات المؤكدة: {money(revenue)}", 13, True, ft.Colors.GREEN_700)],
                   ft.Colors.PURPLE_50),
              btn("📊 التقارير", lambda e: show_admin_reports(page), ft.Colors.PURPLE_100, ft.Colors.PURPLE_900),
              btn("➕ إضافة طبيب", lambda e: show_admin_add_doctor(page), ft.Colors.BLUE_50, ft.Colors.BLUE_900),
              btn("➕ إضافة موظف", lambda e: show_admin_add_staff(page), ft.Colors.BLUE_50, ft.Colors.BLUE_900),
              footer(page))


def show_admin_reports(page):
    if not require(page, "admin"):
        return
    appts = db("SELECT * FROM appointments ORDER BY appointment_id DESC LIMIT 100", (), fetch="all")
    pays = db("SELECT * FROM payments ORDER BY payment_id DESC LIMIT 100", (), fetch="all")
    kind_names = {"appointment": "حجز", "lab": "فحص", "pharmacy": "أدوية"}
    method_names = {"electronic": "إلكتروني", "receipt": "إيصال", "cash": "نقداً"}

    def head(t):
        return ft.DataColumn(ft.Text(t, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD))

    def cell(t, color=BLACK):
        return ft.DataCell(ft.Text(str(t or ""), size=13, color=color))

    t1 = ft.DataTable(columns=[head("المريض"), head("الطبيب"), head("الموعد"), head("الحجز"), head("الدفع")],
                      rows=[ft.DataRow(cells=[cell(a["patient_name"]), cell(a["doctor_name"]), cell(a["appointment_date"]),
                                              cell(a["status"], state_color(a["status"])),
                                              cell(a["payment_status"], state_color(a["payment_status"]))]) for a in appts],
                      heading_row_color=ft.Colors.PURPLE_600)
    t2 = ft.DataTable(columns=[head("النوع"), head("المبلغ"), head("الطريقة"), head("البنك"), head("الحالة"), head("التاريخ")],
                      rows=[ft.DataRow(cells=[cell(kind_names.get(p["kind"])), cell(money(p["amount"])),
                                              cell(method_names.get(p["method"])), cell(p["bank"] or "—"),
                                              cell(p["status"]), cell(p["created_at"])]) for p in pays],
                      heading_row_color=ft.Colors.PURPLE_600)
    sms = db("SELECT * FROM sms_log ORDER BY id DESC LIMIT 50", (), fetch="all")
    t3 = ft.DataTable(columns=[head("الهاتف"), head("الرسالة"), head("الحالة"), head("التاريخ")],
                      rows=[ft.DataRow(cells=[cell(s["phone"]), cell(s["message"]), cell(s["status"]), cell(s["created_at"])])
                            for s in sms],
                      heading_row_color=ft.Colors.PURPLE_600)
    page_view(page, h1(f"📊 الحجوزات ({len(appts)})", ft.Colors.PURPLE_800), ft.Row([t1], scroll=ft.ScrollMode.AUTO),
              h1(f"💳 المدفوعات ({len(pays)})", ft.Colors.PURPLE_800), ft.Row([t2], scroll=ft.ScrollMode.AUTO),
              h1(f"✉️ الرسائل النصية ({len(sms)})", ft.Colors.PURPLE_800), ft.Row([t3], scroll=ft.ScrollMode.AUTO),
              back_btn("← رجوع", lambda e: show_admin_home(page)))


def show_admin_add_doctor(page):
    if not require(page, "admin"):
        return
    name = field("اسم الطبيب (بدون لقب)")
    clinic = make_dropdown("العيادة", CLINICS)
    spec = field("التخصص")
    hours = field("ساعات العمل (مثال: 8 ص - 2 م)")
    day_boxes = {d: ft.Checkbox(label=DAY_NAMES[d], value=d in parse_days(SUN_THU)) for d in WEEK_ORDER}
    username = field("اسم المستخدم للدخول (بالإنجليزية)")
    password = field("كلمة سر مؤقتة", password=True, can_reveal_password=True)

    def save(e):
        days = ",".join(str(d) for d, c in day_boxes.items() if c.value)
        n, u, p = (name.value or "").strip(), (username.value or "").strip(), password.value or ""
        if not (n and clinic.value and (spec.value or "").strip() and (hours.value or "").strip() and days and u):
            err_snack(page, "أكمل جميع الحقول واختر يوم عمل واحداً على الأقل")
            return
        if len(p) < 6:
            err_snack(page, "كلمة السر 6 أحرف على الأقل")
            return
        try:
            add_doctor(n, clinic.value, spec.value.strip(), days, hours.value.strip(), u, p)
        except sqlite3.IntegrityError:
            err_snack(page, "اسم المستخدم مستخدم مسبقاً")
            return
        show_admin_home(page)
        ok_snack(page, "تمت إضافة الطبيب، سيُطلب منه تغيير كلمة السر عند أول دخول")

    page_view(page, h1("➕ إضافة طبيب", ft.Colors.PURPLE_800), name, clinic, spec, hours,
              info("أيام العمل:", 13, True), ft.Wrap(list(day_boxes.values()), spacing=8), username, password,
              success("حفظ", save, 50), back_btn("← رجوع", lambda e: show_admin_home(page)))


def show_admin_add_staff(page):
    if not require(page, "admin"):
        return
    roles = {"موظف استقبال": "reception", "فني مختبر": "lab", "صيدلي": "pharmacy", "مدير": "admin"}
    role = make_dropdown("الوظيفة", list(roles))
    full_name = field("الاسم الكامل")
    username = field("اسم المستخدم (بالإنجليزية)")
    password = field("كلمة سر مؤقتة", password=True, can_reveal_password=True)

    def save(e):
        n, u, p = (full_name.value or "").strip(), (username.value or "").strip(), password.value or ""
        if not (role.value and n and u):
            err_snack(page, "أكمل جميع الحقول")
            return
        if len(p) < 6:
            err_snack(page, "كلمة السر 6 أحرف على الأقل")
            return
        try:
            add_user(u, n, roles[role.value], p, must_change=1)
        except sqlite3.IntegrityError:
            err_snack(page, "اسم المستخدم مستخدم مسبقاً")
            return
        show_admin_home(page)
        ok_snack(page, "تمت إضافة الموظف")

    page_view(page, h1("➕ إضافة موظف", ft.Colors.PURPLE_800), role, full_name, username, password,
              success("حفظ", save, 50), back_btn("← رجوع", lambda e: show_admin_home(page)))


# ===============================================================
def main(page: ft.Page):
    page.title = HOSPITAL_NAME
    page.rtl = True
    page.scroll = ft.ScrollMode.AUTO
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.bgcolor = ft.Colors.WHITE

    init_db()
    STATE["picker"] = ft.FilePicker()
    page.services.append(STATE["picker"])
    show_home(page)


if __name__ == "__main__":
    ft.run(main)

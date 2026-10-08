import flet as ft
import sqlite3
import os
import shutil
import time

TICKET_PRICE = "10.000"

# على الأندرويد نستخدم مجلد تخزين التطبيق، وعلى الكمبيوتر مجلد الكود
DATA_DIR = os.getenv("FLET_APP_STORAGE_DATA") or os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DATA_DIR, "kosti_hospital.db")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")

CLINICS = [
    "عيادة الباطنية",
    "عيادة الأطفال",
    "عيادة النساء والتوليد",
    "عيادة العظام",
    "عيادة الجلدية",
    "عيادة المخ والأعصاب",
]


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
            national_id TEXT UNIQUE,
            phone_number TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            national_id TEXT,
            clinic_name TEXT,
            appointment_date TEXT,
            attachment_path TEXT
        )
    """)
    conn.commit()
    conn.close()


def main(page: ft.Page):
    page.title = "مستشفى كوستي التعليمي"
    page.rtl = True
    page.bgcolor = ft.Colors.WHITE
    page.scroll = ft.ScrollMode.AUTO
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    init_db()
    state = {"nat_id": ""}

    def snack(text):
        page.show_dialog(
            ft.SnackBar(ft.Text(text, color=ft.Colors.WHITE), bgcolor=ft.Colors.BLUE_700)
        )

    # ---------------- شاشة الدخول ----------------
    def show_login(e=None):
        page.clean()

        nat_field = ft.TextField(
            label="الرقم الوطني", width=320,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        phone_field = ft.TextField(
            label="رقم الهاتف (مثال: 0912345678)", width=320,
            keyboard_type=ft.KeyboardType.PHONE,
        )

        def login(ev):
            nat = (nat_field.value or "").strip()
            phone = (phone_field.value or "").strip()

            if not nat or not phone:
                snack("الرجاء إدخال الرقم الوطني ورقم الهاتف")
                return
            if not (phone.isdigit() and len(phone) == 10 and phone.startswith("0")):
                snack("رقم الهاتف غير صحيح: 10 أرقام ويبدأ بصفر")
                return

            try:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM patients WHERE national_id = ?", (nat,))
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO patients (national_id, phone_number) VALUES (?, ?)",
                        (nat, phone),
                    )
                    conn.commit()
                conn.close()
            except sqlite3.Error as err:
                snack(f"خطأ في قاعدة البيانات: {err}")
                return

            state["nat_id"] = nat
            show_clinics()

        page.add(
            ft.Column(
                [
                    ft.Text("مستشفى كوستي التعليمي", size=22,
                            weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                    ft.Text("يرجى إدخال البيانات للمتابعة", size=14, color=ft.Colors.GREY_700),
                    nat_field,
                    phone_field,
                    ft.Button(content="تسجيل الدخول", on_click=login, width=320, height=45),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=15,
            )
        )
        page.update()

    # ---------------- شاشة العيادات ----------------
    def show_clinics():
        page.clean()

        buttons = [
            ft.Button(
                content=name,
                on_click=lambda ev, n=name: show_booking(n),
                width=320, height=45,
            )
            for name in CLINICS
        ]

        price_box = ft.Container(
            content=ft.Text(
                f"سعر التذكرة: {TICKET_PRICE} جنيه",
                size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_900,
            ),
            bgcolor=ft.Colors.ORANGE_50,
            padding=10, border_radius=8, width=320,
            alignment=ft.Alignment.CENTER,
        )

        page.add(
            ft.Column(
                [
                    ft.Text("اختر العيادة المطلوبة", size=20,
                            weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                    price_box,
                    *buttons,
                    ft.TextButton(content="تسجيل الخروج", on_click=show_login),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            )
        )
        page.update()

    # ---------------- شاشة الحجز ----------------
    def show_booking(clinic_name):
        page.clean()
        attachment = {"path": None, "name": None}

        date_field = ft.TextField(
            label="تاريخ الموعد (مثال: 2026-06-15)", width=320,
        )
        attach_label = ft.Text("لم يتم اختيار صورة", size=13, color=ft.Colors.GREY_700)

        async def pick_image(ev):
            files = await ft.FilePicker().pick_files(
                dialog_title="اختر صورة",
                file_type=ft.FilePickerFileType.IMAGE,
                allow_multiple=False,
            )
            if files:
                attachment["path"] = files[0].path
                attachment["name"] = files[0].name
                attach_label.value = f"تم اختيار: {files[0].name}"
                attach_label.color = ft.Colors.GREEN_700
                page.update()

        def confirm(ev):
            date_val = (date_field.value or "").strip()
            if not date_val:
                snack("الرجاء تحديد تاريخ الموعد")
                return

            saved = None
            src = attachment["path"]
            if src and os.path.exists(src):
                try:
                    ext = os.path.splitext(src)[1]
                    dest = os.path.join(UPLOADS_DIR, f"{state['nat_id']}_{int(time.time())}{ext}")
                    shutil.copy2(src, dest)
                    saved = dest
                except OSError as err:
                    snack(f"تعذر حفظ الصورة: {err}")
                    return
            elif attachment["name"]:
                saved = attachment["name"]

            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute(
                    "INSERT INTO appointments (national_id, clinic_name, appointment_date, attachment_path) "
                    "VALUES (?, ?, ?, ?)",
                    (state["nat_id"], clinic_name, date_val, saved),
                )
                conn.commit()
                conn.close()
            except sqlite3.Error as err:
                snack(f"خطأ في قاعدة البيانات: {err}")
                return

            snack("تم حجز الموعد بنجاح!")
            show_clinics()

        page.add(
            ft.Column(
                [
                    ft.Text(f"حجز موعد في: {clinic_name}", size=18,
                            weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                    date_field,
                    ft.OutlinedButton(content="إرفاق صورة", icon=ft.Icons.ATTACH_FILE,
                                      on_click=pick_image, width=320, height=45),
                    attach_label,
                    ft.Button(content="تأكيد الحجز", on_click=confirm, width=320, height=45),
                    ft.TextButton(content="العودة للعيادات", icon=ft.Icons.ARROW_BACK,
                                  on_click=lambda ev: show_clinics()),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=15,
            )
        )
        page.update()

    show_login()


ft.run(main)

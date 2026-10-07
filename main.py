import flet as ft
import sqlite3
import os
from datetime import datetime

# ============================================================
# مسار قاعدة البيانات
# ============================================================
if os.environ.get("FLET_APP_STORAGE_DATA"):
    DB_PATH = os.path.join(os.environ["FLET_APP_STORAGE_DATA"], "kosti_hospital.db")
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kosti_hospital.db")

TICKET_PRICE = "10,000 جنيه"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
            national_id TEXT UNIQUE,
            phone_number TEXT,
            registered_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT,
            national_id TEXT,
            clinic_name TEXT,
            doctor_name TEXT,
            appointment_date TEXT,
            booked_at TEXT
        )
    """)
    conn.commit()
    conn.close()


CLINICS = [
    {"name": "عيادة الباطنية", "room": "غرفة 101", "icon": ft.Icons.MEDICAL_SERVICES, "color": "#1976D2"},
    {"name": "عيادة الأطفال", "room": "غرفة 103", "icon": ft.Icons.CHILD_CARE, "color": "#43A047"},
    {"name": "عيادة النساء والتوليد", "room": "غرفة 104", "icon": ft.Icons.PREGNANT_WOMAN, "color": "#E91E63"},
    {"name": "عيادة العظام", "room": "غرفة 105", "icon": ft.Icons.ACCESSIBILITY_NEW, "color": "#FB8C00"},
    {"name": "عيادة المخ والأعصاب", "room": "غرفة 106", "icon": ft.Icons.PSYCHOLOGY, "color": "#8E24AA"},
    {"name": "عيادة الجلدية", "room": "غرفة 107", "icon": ft.Icons.FACE_RETOUCHING_NATURAL, "color": "#00897B"},
]

DOCTORS = {
    "عيادة الباطنية": [("محمد أحمد", "باطنية", "الأحد - الخميس", "8 ص - 2 م")],
    "عيادة الأطفال": [("سلمى خالد", "طب الأطفال", "الأحد - الخميس", "9 ص - 3 م")],
    "عيادة النساء والتوليد": [("هند عمر", "نساء وتوليد", "الأحد - الخميس", "9 ص - 3 م")],
    "عيادة العظام": [("عمر يوسف", "جراحة عظام", "السبت - الأربعاء", "8 ص - 2 م")],
    "عيادة المخ والأعصاب": [("أحمد الطيب", "مخ وأعصاب", "الأحد - الخميس", "10 ص - 4 م")],
    "عيادة الجلدية": [("منى حسن", "جلدية", "السبت - الأربعاء", "9 ص - 3 م")],
}


def main(page: ft.Page):
    page.title = "مستشفى كوستي التعليمي"
    page.rtl = True
    page.bgcolor = "#F5F7FA"
    page.scroll = ft.ScrollMode.AUTO
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 15

    try:
        page.window.width = 420
        page.window.height = 720
    except Exception:
        pass

    init_db()

    current_patient = {"nat_id": "", "name": ""}
    ADMIN_PASSWORD = "admin123"

    def show_snack(text, color="#1976D2"):
        try:
            snack = ft.SnackBar(
                content=ft.Text(text, color="white", weight=ft.FontWeight.BOLD),
                bgcolor=color,
                duration=3000
            )
            page.show_dialog(snack)
            page.update()
        except Exception as e:
            print(f"Snack error: {e}")

    # ============================================================
    # 1) تسجيل الدخول
    # ============================================================
    def show_login_screen(e=None):
        page.clean()
        current_patient["nat_id"] = ""
        current_patient["name"] = ""

        name_field = ft.TextField(
            label="الاسم الكامل",
            text_align=ft.TextAlign.RIGHT,
            expand=True,
            border_color="#1976D2",
        )
        nat_field = ft.TextField(
            label="الرقم الوطني",
            text_align=ft.TextAlign.RIGHT,
            expand=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            max_length=11,
            border_color="#1976D2",
        )
        phone_field = ft.TextField(
            label="رقم الهاتف",
            text_align=ft.TextAlign.RIGHT,
            expand=True,
            border_color="#1976D2",
        )

        def handle_login(ev):
            name = (name_field.value or "").strip()
            nat_id = (nat_field.value or "").strip()
            phone = (phone_field.value or "").strip()

            if not name:
                show_snack("⚠️ أدخل الاسم", "#E53935")
                return
            if not nat_id:
                show_snack("⚠️ أدخل الرقم الوطني", "#E53935")
                return
            if not nat_id.isdigit() or len(nat_id) != 11:
                show_snack("⚠️ الرقم الوطني 11 رقماً", "#E53935")
                return
            if not phone:
                show_snack("⚠️ أدخل رقم الهاتف", "#E53935")
                return

            current_patient["nat_id"] = nat_id
            current_patient["name"] = name

            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT patient_id FROM patients WHERE national_id = ?", (nat_id,)
                )
                user = cursor.fetchone()
                if not user:
                    cursor.execute("""
                        INSERT INTO patients (national_id, phone_number, registered_at)
                        VALUES (?, ?, ?)
                    """, (nat_id, phone, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                conn.close()
            except sqlite3.Error as err:
                show_snack(f"❌ خطأ: {err}", "#E53935")
                return

            show_snack("✅ تم تسجيل الدخول", "#43A047")
            show_clinics_screen()

        page.add(
            ft.Column([
                ft.Container(expand=True),
                ft.Icon(ft.Icons.LOCAL_HOSPITAL, size=90, color="#1976D2"),
                ft.Text("مستشفى كوستي التعليمي", size=24,
                        weight=ft.FontWeight.BOLD, color="#0D47A1",
                        text_align=ft.TextAlign.CENTER),
                ft.Text("نظام الحجز الإلكتروني", size=15, color="#546E7A"),
                ft.Container(height=25),
                name_field,
                nat_field,
                phone_field,
                ft.Container(height=15),
                ft.Button(
                    content=ft.Row([
                        ft.Icon(ft.Icons.LOGIN, color="white"),
                        ft.Text("تسجيل الدخول", color="white",
                                weight=ft.FontWeight.BOLD, size=16)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    on_click=handle_login,
                    expand=True,
                    height=55,
                    bgcolor="#1976D2",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=12),
                    )
                ),
                ft.Container(expand=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=12)
        )
        page.update()

    # ============================================================
    # 2) العيادات
    # ============================================================
    def show_clinics_screen(e=None):
        page.clean()

        price_card = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CONFIRMATION_NUMBER, color="white", size=28),
                ft.Column([
                    ft.Text("سعر التذكرة", size=13, color="white70"),
                    ft.Text(TICKET_PRICE, size=18, color="white",
                            weight=ft.FontWeight.BOLD),
                ], spacing=2)
            ], spacing=15),
            padding=15,
            bgcolor="#FF9800",
            border_radius=12,
        )

        clinic_cards = []
        for clinic in CLINICS:
            def make_handler(name):
                def handler(ev):
                    show_doctors_screen(name)
                return handler

            card = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(clinic["icon"], color="white", size=28),
                        bgcolor=clinic["color"],
                        border_radius=50,
                        width=50, height=50,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column([
                        ft.Text(clinic["name"], size=15,
                                weight=ft.FontWeight.BOLD, color="#0D47A1"),
                        ft.Text(clinic["room"], size=12, color="#546E7A")
                    ], spacing=2, expand=True),
                    ft.Icon(ft.Icons.ARROW_BACK_IOS, color="#90A4AE", size=16)
                ], spacing=15, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=15,
                expand=True,
                bgcolor="white",
                border_radius=12,
                border=ft.border.all(1, "#E0E0E0"),
                on_click=make_handler(clinic["name"]),
                ink=True,
            )
            clinic_cards.append(card)

        page.add(
            ft.Column([
                ft.Text("🏥 العيادات المتاحة", size=22,
                        weight=ft.FontWeight.BOLD, color="#0D47A1"),
                ft.Text(f"مرحباً: {current_patient['name']}", size=14, color="#43A047"),
                ft.Container(height=10),
                price_card,
                ft.Container(height=10),
                *clinic_cards,
                ft.Container(height=10),
                ft.Button(
                    content=ft.Row([
                        ft.Icon(ft.Icons.LIST_ALT, color="#E65100"),
                        ft.Text("مواعيدي", color="#E65100",
                                weight=ft.FontWeight.BOLD)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    on_click=show_my_appointments_screen,
                    expand=True, height=50,
                    bgcolor="#FFE0B2",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                ),
                ft.Container(height=5),
                ft.Row([
                    ft.TextButton(
                        content="👨‍💼 الإدارة",
                        icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                        icon_color="#6A1B9A",
                        on_click=show_admin_login
                    ),
                    ft.TextButton(
                        content="🚪 خروج",
                        icon=ft.Icons.LOGOUT,
                        icon_color="#E53935",
                        on_click=show_login_screen
                    ),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
               spacing=8, expand=True)
        )
        page.update()

    # ============================================================
    # 3) الأطباء
    # ============================================================
    def show_doctors_screen(clinic_name):
        page.clean()

        doctors = DOCTORS.get(clinic_name, [])

        doctor_cards = []
        for doc_name, spec, days, hours in doctors:
            def make_handler(dname, dspec):
                def handler(ev):
                    show_booking_screen(clinic_name, dname, dspec)
                return handler

            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Text(doc_name[0], size=24, color="white",
                                            weight=ft.FontWeight.BOLD),
                            bgcolor="#1976D2",
                            border_radius=50,
                            width=60, height=60,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Column([
                            ft.Text(f"{doc_name} / {clinic_name}",
                                    size=14, weight=ft.FontWeight.BOLD,
                                    color="#0D47A1"),
                            ft.Text(spec, size=12, color="#546E7A")
                        ], spacing=4, expand=True)
                    ], spacing=12),
                    ft.Divider(height=1, color="#E0E0E0"),
                    ft.Row([
                        ft.Icon(ft.Icons.SCHEDULE, size=16, color="#546E7A"),
                        ft.Text(days, size=12, color="#546E7A")
                    ], spacing=5),
                    ft.Row([
                        ft.Icon(ft.Icons.ACCESS_TIME, size=16, color="#546E7A"),
                        ft.Text(hours, size=12, color="#546E7A")
                    ], spacing=5),
                    ft.Button(
                        content=ft.Row([
                            ft.Icon(ft.Icons.EVENT_AVAILABLE, color="white"),
                            ft.Text("حجز موعد", color="white",
                                    weight=ft.FontWeight.BOLD)
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        on_click=make_handler(doc_name, spec),
                        expand=True, height=45,
                        bgcolor="#43A047",
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                    )
                ], spacing=8),
                padding=15, expand=True,
                bgcolor="white",
                border_radius=14,
                border=ft.border.all(1, "#E0E0E0"),
            )
            doctor_cards.append(card)

        page.add(
            ft.Column([
                ft.Text(f"👨‍⚕️ أطباء {clinic_name}", size=20,
                        weight=ft.FontWeight.BOLD, color="#0D47A1"),
                ft.Text(f"سعر التذكرة: {TICKET_PRICE}", size=13, color="#FF9800"),
                ft.Container(height=10),
                *doctor_cards,
                ft.Container(height=10),
                ft.TextButton(
                    content="← العودة للعيادات",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=show_clinics_screen
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
               spacing=12, expand=True)
        )
        page.update()

    # ============================================================
    # 4) الحجز - مع حقل إرفاق صور
    # ============================================================
    def show_booking_screen(clinic_name, doctor_name, specialization):
        page.clean()

        name_field = ft.TextField(
            label="اسم المريض",
            value=current_patient["name"],
            text_align=ft.TextAlign.RIGHT,
            expand=True,
            border_color="#43A047",
        )

        date_field = ft.TextField(
            label="تاريخ الموعد (مثال: 2026-06-15)",
            text_align=ft.TextAlign.RIGHT,
            expand=True,
            border_color="#43A047",
        )

        # ✅ حقل إرفاق الصور
        def attach_image(ev):
            show_snack("📎 ميزة إرفاق الصور ستتوفر قريباً", "#FF9800")

        attach_btn = ft.Button(
            content=ft.Row([
                ft.Icon(ft.Icons.ATTACH_FILE, color="white"),
                ft.Text("إرفاق صور", color="white",
                        weight=ft.FontWeight.BOLD)
            ], alignment=ft.MainAxisAlignment.CENTER),
            on_click=attach_image,
            expand=True, height=50,
            bgcolor="#0288D1",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
        )

        # معاينة الصورة
        image_preview = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.IMAGE, size=40, color="#90A4AE"),
                ft.Text("لا توجد صورة", color="#90A4AE", size=11)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
            width=110, height=110,
            bgcolor="#ECEFF1",
            border_radius=10,
            alignment=ft.Alignment.CENTER,
        )

        def confirm_booking(ev):
            name_val = (name_field.value or "").strip()
            date_val = (date_field.value or "").strip()

            if not name_val:
                show_snack("⚠️ أدخل اسم المريض", "#E53935")
                return
            if not date_val:
                show_snack("⚠️ أدخل تاريخ الموعد", "#E53935")
                return

            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO appointments 
                    (patient_name, national_id, clinic_name, doctor_name,
                     appointment_date, booked_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (name_val, current_patient["nat_id"], clinic_name,
                      doctor_name, date_val,
                      datetime.now().strftime("%Y-%m-%d %H:%M")))
                conn.commit()
                conn.close()
            except sqlite3.Error as err:
                show_snack(f"❌ خطأ: {err}", "#E53935")
                return

            show_snack("✅ تم تأكيد الحجز بنجاح", "#43A047")
            show_my_appointments_screen()

        page.add(
            ft.Column([
                ft.Icon(ft.Icons.EVENT_AVAILABLE, size=70, color="#43A047"),
                ft.Text("حجز موعد جديد", size=22,
                        weight=ft.FontWeight.BOLD, color="#0D47A1"),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.PERSON, color="#1976D2"),
                            ft.Text(f"{doctor_name} / {clinic_name}",
                                    size=14, weight=ft.FontWeight.BOLD,
                                    color="#0D47A1")
                        ], spacing=8),
                        ft.Row([
                            ft.Icon(ft.Icons.MEDICAL_SERVICES, size=16,
                                    color="#546E7A"),
                            ft.Text(specialization, size=12, color="#546E7A")
                        ], spacing=8),
                        ft.Row([
                            ft.Icon(ft.Icons.CONFIRMATION_NUMBER, size=16,
                                    color="#FF9800"),
                            ft.Text(f"سعر التذكرة: {TICKET_PRICE}",
                                    size=12, color="#FF9800",
                                    weight=ft.FontWeight.BOLD)
                        ], spacing=8)
                    ], spacing=6),
                    padding=15, expand=True,
                    bgcolor="#E3F2FD",
                    border_radius=12,
                    border=ft.border.all(1, "#BBDEFB")
                ),
                ft.Container(height=15),
                name_field,
                date_field,
                ft.Container(height=10),
                ft.Text("📎 إرفاق صورة (اختياري):",
                        size=13, color="#546E7A"),
                ft.Row([
                    image_preview,
                    ft.Column([attach_btn], expand=True)
                ], spacing=10),
                ft.Container(height=15),
                ft.Button(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color="white"),
                        ft.Text("تأكيد الحجز", color="white",
                                weight=ft.FontWeight.BOLD, size=16)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    on_click=confirm_booking,
                    expand=True, height=55,
                    bgcolor="#43A047",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=12),
                    )
                ),
                ft.Container(height=5),
                ft.TextButton(
                    content="← العودة للأطباء",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: show_doctors_screen(clinic_name)
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
               spacing=10, expand=True)
        )
        page.update()

    # ============================================================
    # 5) مواعيدي
    # ============================================================
    def show_my_appointments_screen(e=None):
        page.clean()

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT appointment_id, patient_name, clinic_name,
                       doctor_name, appointment_date
                FROM appointments
                WHERE national_id = ?
                ORDER BY appointment_id DESC
            """, (current_patient["nat_id"],))
            rows = cursor.fetchall()
            conn.close()
        except sqlite3.Error:
            rows = []

        appt_cards = []
        if not rows:
            appt_cards.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.EVENT_BUSY, size=70, color="#90A4AE"),
                        ft.Text("لا توجد مواعيد محجوزة", size=14, color="#546E7A")
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=40
                )
            )
        else:
            for aid, name, clinic, doctor, date in rows:
                appt_cards.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"رقم الحجز: #{aid}", size=12, color="#546E7A"),
                            ft.Text(f"👤 {name}", size=14,
                                    weight=ft.FontWeight.BOLD, color="#0D47A1"),
                            ft.Text(f"👨‍⚕️ {doctor} / {clinic}", size=13, color="#37474F"),
                            ft.Text(f"📅 {date}", size=12, color="#546E7A"),
                        ], spacing=4),
                        padding=12, expand=True,
                        bgcolor="white",
                        border_radius=12,
                        border=ft.border.all(1, "#E0E0E0")
                    )
                )

        page.add(
            ft.Column([
                ft.Text("📋 مواعيدي", size=22,
                        weight=ft.FontWeight.BOLD, color="#0D47A1"),
                ft.Container(height=10),
                *appt_cards,
                ft.Container(height=10),
                ft.TextButton(
                    content="← العودة للعيادات",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=show_clinics_screen
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
               spacing=10, expand=True)
        )
        page.update()

    # ============================================================
    # 6) دخول الإدارة
    # ============================================================
    def show_admin_login(e=None):
        page.clean()

        pass_field = ft.TextField(
            label="كلمة سر الإدارة",
            password=True,
            can_reveal_password=True,
            text_align=ft.TextAlign.RIGHT,
            expand=True,
            border_color="#8E24AA",
        )

        def do_login(ev):
            entered = (pass_field.value or "").strip()
            if entered == ADMIN_PASSWORD:
                show_snack("✅ مرحباً بك", "#43A047")
                show_admin_dashboard()
            else:
                show_snack("❌ كلمة السر غير صحيحة", "#E53935")

        page.add(
            ft.Column([
                ft.Container(expand=True),
                ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, size=90, color="#6A1B9A"),
                ft.Text("لوحة الإدارة", size=24,
                        weight=ft.FontWeight.BOLD, color="#4A148C"),
                ft.Text("للموظفين المصرح لهم فقط", size=13, color="#546E7A"),
                ft.Container(height=25),
                pass_field,
                ft.Container(height=15),
                ft.Button(
                    content=ft.Row([
                        ft.Icon(ft.Icons.LOCK_OPEN, color="white"),
                        ft.Text("دخول", color="white",
                                weight=ft.FontWeight.BOLD, size=16)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    on_click=do_login,
                    expand=True, height=55,
                    bgcolor="#6A1B9A",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))
                ),
                ft.Container(height=8),
                ft.TextButton(
                    content="← العودة",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=show_clinics_screen
                ),
                ft.Container(expand=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=10)
        )
        page.update()

    # ============================================================
    # 7) لوحة الإدارة
    # ============================================================
    def show_admin_dashboard():
        page.clean()

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.appointment_id, a.patient_name, a.appointment_date,
                       a.clinic_name, p.phone_number
                FROM appointments a
                LEFT JOIN patients p ON a.national_id = p.national_id
                ORDER BY a.appointment_id DESC
            """)
            rows = cursor.fetchall()
            conn.close()
        except sqlite3.Error:
            rows = []

        table_rows = []
        for aid, name, date, clinic, phone in rows:
            table_rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(name or "", size=14)),
                    ft.DataCell(ft.Text(date or "", size=14)),
                    ft.DataCell(ft.Text(clinic or "", size=14)),
                    ft.DataCell(ft.Text(phone or "", size=14)),
                ])
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("الاسم", size=15,
                                      weight=ft.FontWeight.BOLD, color="white")),
                ft.DataColumn(ft.Text("الموعد", size=15,
                                      weight=ft.FontWeight.BOLD, color="white")),
                ft.DataColumn(ft.Text("العيادة", size=15,
                                      weight=ft.FontWeight.BOLD, color="white")),
                ft.DataColumn(ft.Text("رقم الهاتف", size=15,
                                      weight=ft.FontWeight.BOLD, color="white")),
            ],
            rows=table_rows,
            heading_row_color="#6A1B9A",
            heading_row_height=60,
            data_row_min_height=55,
            data_row_max_height=70,
            column_spacing=15,
            horizontal_lines=ft.BorderSide(1, "#E0E0E0"),
            vertical_lines=ft.BorderSide(1, "#E0E0E0"),
            border_radius=10,
        )

        page.add(
            ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Text("👨‍💼 تقارير الحجوزات", size=22,
                                weight=ft.FontWeight.BOLD, color="#4A148C"),
                        ft.Text(f"({len(rows)})", size=18, color="#546E7A")
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=15, bgcolor="#F3E5F5", border_radius=10
                ),
                ft.Container(height=10),
                ft.Column([table], scroll=ft.ScrollMode.AUTO, expand=True,
                          horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(height=10),
                ft.TextButton(
                    content="← خروج من الإدارة",
                    icon=ft.Icons.LOGOUT,
                    icon_color="#E53935",
                    on_click=show_clinics_screen
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
               spacing=8, expand=True)
        )
        page.update()

    # ============================================================
    # بدء التطبيق
    # ============================================================
    show_login_screen()


if __name__ == "__main__":
    ft.run(main)

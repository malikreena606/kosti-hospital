import flet as ft
import sqlite3
import os
from datetime import datetime

if os.environ.get("FLET_APP_STORAGE_DATA"):
    DB_PATH = os.path.join(os.environ["FLET_APP_STORAGE_DATA"], "kosti_hospital.db")
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kosti_hospital.db")


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
    print("✅ قاعدة البيانات جاهزة")


def make_border(color, width=1):
    try:
        return ft.border.all(width, color)
    except AttributeError:
        try:
            return ft.border.Border(
                top=ft.border.BorderSide(width, color),
                bottom=ft.border.BorderSide(width, color),
                left=ft.border.BorderSide(width, color),
                right=ft.border.BorderSide(width, color),
            )
        except Exception:
            return None


def main(page: ft.Page):
    page.title = "مستشفى كوستي التعليمي"
    page.rtl = True
    page.bgcolor = ft.Colors.WHITE
    page.scroll = ft.ScrollMode.AUTO
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 15

    try:
        page.window.width = 420
        page.window.height = 720
    except Exception:
        pass

    init_db()

    current_patient = {"nat_id": "", "clinic": "", "name": ""}
    ADMIN_PASSWORD = "admin123"

    def show_snack(text, color=ft.Colors.BLUE_700):
        try:
            snack = ft.SnackBar(
                content=ft.Text(text, color=ft.Colors.WHITE,
                                weight=ft.FontWeight.BOLD),
                bgcolor=color,
                duration=3000
            )
            page.show_dialog(snack)
            page.update()
        except Exception as e:
            print(f"Snack error: {e}")

    def show_login_screen(e=None):
        page.clean()
        current_patient["nat_id"] = ""
        current_patient["name"] = ""

        name_field = ft.TextField(
            label="الاسم الكامل",
            text_align=ft.TextAlign.RIGHT,
            expand=True,
            border_color=ft.Colors.BLUE_400,
            focused_border_color=ft.Colors.BLUE_700
        )
        nat_field = ft.TextField(
            label="الرقم الوطني (11 رقم)",
            text_align=ft.TextAlign.RIGHT,
            expand=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            max_length=11,
            border_color=ft.Colors.BLUE_400,
            focused_border_color=ft.Colors.BLUE_700
        )
        phone_field = ft.TextField(
            label="رقم الهاتف (09xxxxxxxx)",
            text_align=ft.TextAlign.RIGHT,
            expand=True,
            keyboard_type=ft.KeyboardType.PHONE,
            max_length=10,
            border_color=ft.Colors.BLUE_400,
            focused_border_color=ft.Colors.BLUE_700
        )

        def handle_login(ev):
            name = (name_field.value or "").strip()
            nat_id = (nat_field.value or "").strip()
            phone = (phone_field.value or "").strip()

            if not name:
                show_snack("⚠️ أدخل الاسم", ft.Colors.RED_600)
                return
            if not nat_id:
                show_snack("⚠️ أدخل الرقم الوطني", ft.Colors.RED_600)
                return
            if not nat_id.isdigit() or len(nat_id) != 11:
                show_snack("⚠️ الرقم الوطني 11 رقماً", ft.Colors.RED_600)
                return
            if not phone:
                show_snack("⚠️ أدخل رقم الهاتف", ft.Colors.RED_600)
                return
            if not phone.isdigit() or len(phone) != 10 or not phone.startswith("09"):
                show_snack("⚠️ الرقم يبدأ بـ 09 و 10 أرقام", ft.Colors.RED_600)
                return

            current_patient["nat_id"] = nat_id
            current_patient["name"] = name

            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT patient_id FROM patients WHERE national_id = ?",
                    (nat_id,)
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
                show_snack(f"❌ خطأ: {err}", ft.Colors.RED_600)
                return

            show_snack("✅ تم تسجيل الدخول", ft.Colors.GREEN_600)
            show_clinics_screen()

        page.add(
            ft.Column([
                ft.Container(expand=True),
                ft.Icon(ft.Icons.LOCAL_HOSPITAL, size=80, color=ft.Colors.BLUE_700),
                ft.Text("مستشفى كوستي التعليمي", size=22,
                        weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                ft.Text("نظام الحجز الذكي", size=14, color=ft.Colors.GREY_600),
                ft.Container(height=25),
                name_field,
                nat_field,
                phone_field,
                ft.Container(height=15),
                ft.Button(
                    content="🔐 تسجيل الدخول",
                    on_click=handle_login,
                    expand=True,
                    height=50,
                    bgcolor=ft.Colors.BLUE_600,
                    color=ft.Colors.WHITE
                ),
                ft.Container(expand=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=12)
        )
        page.update()

    def show_clinics_screen(e=None):
        page.clean()

        clinics = [
            ("عيادة الباطنية", "غرفة 101"),
            ("عيادة الجراحة", "غرفة 102"),
            ("عيادة الأطفال", "غرفة 103"),
            ("عيادة النساء والتوليد", "غرفة 104"),
        ]

        icons = {
            "عيادة الباطنية": ft.Icons.MEDICAL_SERVICES,
            "عيادة الجراحة": ft.Icons.HEALING,
            "عيادة الأطفال": ft.Icons.CHILD_CARE,
            "عيادة النساء والتوليد": ft.Icons.PREGNANT_WOMAN,
        }

        clinic_cards = []
        for cname, room in clinics:
            icon = icons.get(cname, ft.Icons.LOCAL_HOSPITAL)

            def make_handler(name):
                def handler(ev):
                    show_doctors_screen(name)
                return handler

            clinic_cards.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(icon, color=ft.Colors.BLUE_700, size=32),
                        ft.Column([
                            ft.Text(cname, size=15,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_900),
                            ft.Text(room, size=12, color=ft.Colors.GREY_600)
                        ], spacing=2, expand=True),
                        ft.Icon(ft.Icons.ARROW_BACK_IOS,
                                color=ft.Colors.GREY_400, size=16)
                    ], spacing=15, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=18,
                    expand=True,
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=12,
                    border=make_border(ft.Colors.BLUE_200),
                    on_click=make_handler(cname),
                    ink=True
                )
            )

        page.add(
            ft.Column([
                ft.Text("🏥 العيادات المتاحة", size=20,
                        weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                ft.Text(f"مرحباً: {current_patient['name']}", size=14,
                        color=ft.Colors.GREEN_700),
                ft.Text("اختر العيادة المطلوبة", size=13, color=ft.Colors.GREY_600),
                ft.Container(height=10),
                *clinic_cards,
                ft.Container(height=10),
                ft.Button(
                    content="📋 مواعيدي",
                    icon=ft.Icons.LIST_ALT,
                    on_click=show_my_appointments_screen,
                    expand=True, height=50,
                    bgcolor=ft.Colors.ORANGE_100,
                    color=ft.Colors.ORANGE_900
                ),
                ft.Container(height=5),
                ft.Row([
                    ft.TextButton(
                        content="👨‍💼 الإدارة",
                        icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                        icon_color=ft.Colors.PURPLE_600,
                        on_click=show_admin_login
                    ),
                    ft.TextButton(
                        content="🚪 خروج",
                        icon=ft.Icons.LOGOUT,
                        icon_color=ft.Colors.RED_600,
                        on_click=show_login_screen
                    ),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=10, expand=True)
        )
        page.update()

    def show_doctors_screen(clinic_name):
        page.clean()
        current_patient["clinic"] = clinic_name

        doctors_data = {
            "عيادة الباطنية": [
                ("محمد أحمد", "باطنية", "الأحد - الخميس", "8 ص - 2 م")
            ],
            "عيادة الجراحة": [
                ("أمير محمد", "جراحة عامة", "السبت - الأربعاء", "8 ص - 2 م")
            ],
            "عيادة الأطفال": [
                ("سلمى خالد", "طب الأطفال", "الأحد - الخميس", "9 ص - 3 م")
            ],
            "عيادة النساء والتوليد": [
                ("هند عمر", "نساء وتوليد", "الأحد - الخميس", "9 ص - 3 م")
            ],
        }

        doctors = doctors_data.get(clinic_name, [])

        doctor_cards = []
        for doc_name, spec, days, hours in doctors:

            def make_handler(dname, dspec):
                def handler(ev):
                    show_booking_screen(clinic_name, dname, dspec)
                return handler

            doctor_cards.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.CircleAvatar(
                                content=ft.Icon(ft.Icons.PERSON,
                                                color=ft.Colors.WHITE),
                                bgcolor=ft.Colors.BLUE_600,
                                radius=26
                            ),
                            ft.Column([
                                ft.Text(f"{doc_name} / {clinic_name}",
                                        size=14,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLUE_900),
                                ft.Text(spec, size=12,
                                        color=ft.Colors.GREY_700)
                            ], spacing=2, expand=True)
                        ], spacing=12),
                        ft.Divider(height=1, color=ft.Colors.GREY_300),
                        ft.Row([
                            ft.Icon(ft.Icons.SCHEDULE, size=14,
                                    color=ft.Colors.GREY_600),
                            ft.Text(days, size=12, color=ft.Colors.GREY_700)
                        ], spacing=5),
                        ft.Row([
                            ft.Icon(ft.Icons.ACCESS_TIME, size=14,
                                    color=ft.Colors.GREY_600),
                            ft.Text(hours, size=12, color=ft.Colors.GREY_700)
                        ], spacing=5),
                        ft.Button(
                            content="📅 حجز موعد",
                            on_click=make_handler(doc_name, spec),
                            expand=True, height=42,
                            bgcolor=ft.Colors.GREEN_600,
                            color=ft.Colors.WHITE
                        )
                    ], spacing=8),
                    padding=15, expand=True,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    border=make_border(ft.Colors.BLUE_200)
                )
            )

        page.add(
            ft.Column([
                ft.Text(f"👨‍⚕️ أطباء {clinic_name}", size=18,
                        weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                ft.Container(height=10),
                *doctor_cards,
                ft.Container(height=10),
                ft.TextButton(
                    content="← العودة للعيادات",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=show_clinics_screen
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=12, expand=True)
        )
        page.update()

    def show_booking_screen(clinic_name, doctor_name, specialization):
        page.clean()

        name_field = ft.TextField(
            label="اسم المريض",
            value=current_patient["name"],
            text_align=ft.TextAlign.RIGHT,
            expand=True,
            border_color=ft.Colors.GREEN_400,
            focused_border_color=ft.Colors.GREEN_700
        )

        date_field = ft.TextField(
            label="تاريخ الموعد (مثال: 2026-06-15)",
            text_align=ft.TextAlign.RIGHT,
            expand=True,
            border_color=ft.Colors.GREEN_400,
            focused_border_color=ft.Colors.GREEN_700
        )

        def confirm_booking(ev):
            name_val = (name_field.value or "").strip()
            date_val = (date_field.value or "").strip()

            if not name_val:
                show_snack("⚠️ أدخل اسم المريض", ft.Colors.RED_600)
                return
            if not date_val:
                show_snack("⚠️ أدخل تاريخ الموعد", ft.Colors.RED_600)
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
                show_snack(f"❌ خطأ: {err}", ft.Colors.RED_600)
                return

            show_snack("✅ تم تأكيد الحجز بنجاح", ft.Colors.GREEN_600)
            show_my_appointments_screen()

        page.add(
            ft.Column([
                ft.Icon(ft.Icons.EVENT_AVAILABLE, size=60,
                        color=ft.Colors.GREEN_700),
                ft.Text("حجز موعد جديد", size=20,
                        weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.PERSON, color=ft.Colors.BLUE_700),
                            ft.Text(f"{doctor_name} / {clinic_name}",
                                    size=14, weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_900)
                        ], spacing=8),
                        ft.Row([
                            ft.Icon(ft.Icons.MEDICAL_SERVICES, size=16,
                                    color=ft.Colors.GREY_700),
                            ft.Text(specialization, size=12,
                                    color=ft.Colors.GREY_700)
                        ], spacing=8)
                    ], spacing=4),
                    padding=15, expand=True,
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=12,
                    border=make_border(ft.Colors.BLUE_200)
                ),
                ft.Container(height=15),
                name_field,
                date_field,
                ft.Container(height=15),
                ft.Button(
                    content="✅ تأكيد الحجز",
                    on_click=confirm_booking,
                    expand=True, height=50,
                    bgcolor=ft.Colors.GREEN_600,
                    color=ft.Colors.WHITE
                ),
                ft.Container(height=5),
                ft.TextButton(
                    content="← العودة للأطباء",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: show_doctors_screen(clinic_name)
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=10, expand=True)
        )
        page.update()

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
                        ft.Icon(ft.Icons.EVENT_BUSY, size=60,
                                color=ft.Colors.GREY_400),
                        ft.Text("لا توجد مواعيد محجوزة", size=14,
                                color=ft.Colors.GREY_600)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                       spacing=10),
                    padding=40
                )
            )
        else:
            for aid, name, clinic, doctor, date in rows:
                appt_cards.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"رقم الحجز: #{aid}", size=12,
                                    color=ft.Colors.GREY_600),
                            ft.Text(f"👤 {name}", size=13,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_900),
                            ft.Text(f"👨‍⚕️ {doctor} / {clinic}", size=12,
                                    color=ft.Colors.GREY_800),
                            ft.Text(f"📅 {date}", size=12,
                                    color=ft.Colors.GREY_700)
                        ], spacing=4),
                        padding=12, expand=True,
                        bgcolor=ft.Colors.BLUE_50,
                        border_radius=10,
                        border=make_border(ft.Colors.BLUE_200)
                    )
                )

        page.add(
            ft.Column([
                ft.Text("📋 مواعيدي", size=20,
                        weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                ft.Container(height=10),
                *appt_cards,
                ft.Container(height=10),
                ft.TextButton(
                    content="← العودة للعيادات",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=show_clinics_screen
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=10, expand=True)
        )
        page.update()

    def show_admin_login(e=None):
        page.clean()

        pass_field = ft.TextField(
            label="كلمة سر الإدارة",
            password=True,
            can_reveal_password=True,
            text_align=ft.TextAlign.RIGHT,
            expand=True,
            border_color=ft.Colors.PURPLE_400,
            focused_border_color=ft.Colors.PURPLE_700
        )

        def do_login(ev):
            entered = (pass_field.value or "").strip()
            if entered == ADMIN_PASSWORD:
                show_snack("✅ مرحباً بك", ft.Colors.GREEN_600)
                show_admin_dashboard()
            else:
                show_snack("❌ كلمة السر غير صحيحة", ft.Colors.RED_600)

        page.add(
            ft.Column([
                ft.Container(expand=True),
                ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, size=70,
                        color=ft.Colors.PURPLE_700),
                ft.Text("لوحة الإدارة", size=22,
                        weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_900),
                ft.Text("للموظفين المصرح لهم فقط", size=13,
                        color=ft.Colors.GREY_600),
                ft.Container(height=25),
                pass_field,
                ft.Container(height=15),
                ft.Button(
                    content="🔓 دخول",
                    on_click=do_login,
                    expand=True, height=50,
                    bgcolor=ft.Colors.PURPLE_600,
                    color=ft.Colors.WHITE
                ),
                ft.Container(height=8),
                ft.TextButton(
                    content="← العودة",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=show_clinics_screen
                ),
                ft.Container(expand=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=10, expand=True)
        )
        page.update()

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
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(name or "", size=15)),
                        ft.DataCell(ft.Text(date or "", size=15)),
                        ft.DataCell(ft.Text(clinic or "", size=15)),
                        ft.DataCell(ft.Text(phone or "", size=15)),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("الاسم", size=16,
                                      weight=ft.FontWeight.BOLD,
                                      color=ft.Colors.WHITE)),
                ft.DataColumn(ft.Text("الموعد", size=16,
                                      weight=ft.FontWeight.BOLD,
                                      color=ft.Colors.WHITE)),
                ft.DataColumn(ft.Text("العيادة", size=16,
                                      weight=ft.FontWeight.BOLD,
                                      color=ft.Colors.WHITE)),
                ft.DataColumn(ft.Text("رقم الهاتف", size=16,
                                      weight=ft.FontWeight.BOLD,
                                      color=ft.Colors.WHITE)),
            ],
            rows=table_rows,
            heading_row_color=ft.Colors.PURPLE_600,
            heading_row_height=60,
            data_row_min_height=55,
            data_row_max_height=70,
            column_spacing=15,
            horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_300),
            vertical_lines=ft.BorderSide(1, ft.Colors.GREY_300),
            border=make_border(ft.Colors.GREY_400, 2),
            border_radius=10,
        )

        table_container = ft.Column(
            [table],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        page.add(
            ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Text("👨‍💼 تقارير الحجوزات", size=22,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.PURPLE_900),
                        ft.Text(f"({len(rows)})", size=18,
                                color=ft.Colors.GREY_700)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=15,
                    bgcolor=ft.Colors.PURPLE_50,
                    border_radius=10
                ),
                ft.Container(height=10),
                table_container,
                ft.Container(height=10),
                ft.TextButton(
                    content="← خروج من الإدارة",
                    icon=ft.Icons.LOGOUT,
                    icon_color=ft.Colors.RED_600,
                    on_click=show_clinics_screen
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
               spacing=8, expand=True)
        )
        page.update()

    show_login_screen()


if __name__ == "__main__":
    ft.run(main)

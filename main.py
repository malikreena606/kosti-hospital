import flet as ft
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kosti_hospital.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
            national_id TEXT UNIQUE,
            phone_number TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            national_id TEXT,
            clinic_name TEXT,
            appointment_date TEXT
        )
    """)
    conn.commit()
    conn.close()


def main(page: ft.Page):
    page.title = "مستشفى كوستي التعليمي - نظام الحجز الإلكتروني"
    page.rtl = True
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window.width = 420
    page.window.height = 720
    page.bgcolor = ft.Colors.WHITE
    page.scroll = ft.ScrollMode.AUTO

    init_db()
    current_patient = {"nat_id": "", "clinic": ""}

    def show_snack(text):
        page.show_dialog(
            ft.SnackBar(ft.Text(text, color=ft.Colors.WHITE), bgcolor=ft.Colors.BLUE_700)
        )

    def show_login_screen(e=None):
        page.clean()

        nat_id_field = ft.TextField(
            label="الرقم الوطني",
            text_align=ft.TextAlign.RIGHT,
            width=320,
            border_color=ft.Colors.BLUE_400,
            focused_border_color=ft.Colors.BLUE_700
        )
        phone_field = ft.TextField(
            label="رقم الهاتف",
            text_align=ft.TextAlign.RIGHT,
            width=320,
            border_color=ft.Colors.BLUE_400,
            focused_border_color=ft.Colors.BLUE_700
        )

        def handle_login(event):
            nat_id = nat_id_field.value.strip() if nat_id_field.value else ""
            phone = phone_field.value.strip() if phone_field.value else ""

            if not nat_id or not phone:
                show_snack("الرجاء إدخال الرقم الوطني ورقم الهاتف معاً")
                return

            current_patient["nat_id"] = nat_id

            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM patients WHERE national_id = ?", (nat_id,))
                user = cursor.fetchone()

                if not user:
                    cursor.execute(
                        "INSERT INTO patients (national_id, phone_number) VALUES (?, ?)",
                        (nat_id, phone)
                    )
                    conn.commit()
                conn.close()
            except sqlite3.Error as db_err:
                show_snack(f"حدث خطأ في قاعدة البيانات: {db_err}")
                return

            show_clinics_screen()

        login_btn = ft.Button(
            content="تسجيل الدخول",
            on_click=handle_login,
            width=320,
            height=45,
            bgcolor=ft.Colors.BLUE_600,
            color=ft.Colors.WHITE
        )

        page.add(
            ft.Column([
                ft.Container(
                    content=ft.Text("مستشفى كوستي التعليمي", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                    alignment=ft.Alignment.CENTER
                ),
                ft.Text("نظام الحجز الإلكتروني", size=14, color=ft.Colors.GREY_700),
                ft.Container(height=10),
                nat_id_field,
                phone_field,
                ft.Container(height=10),
                login_btn
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)
        )
        page.update()

    def show_booking_screen(clinic_name):
        page.clean()
        current_patient["clinic"] = clinic_name

        # ============ بطاقة معلومات الدفع ============
        payment_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.CONFIRMATION_NUMBER, color=ft.Colors.WHITE, size=24),
                    ft.Text("سعر التذكرة: 5,000 جنيه", size=16,
                            weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
                ft.Divider(height=1, color=ft.Colors.WHITE),
                ft.Row([
                    ft.Icon(ft.Icons.ACCOUNT_BALANCE, color=ft.Colors.WHITE, size=24),
                    ft.Text("رقم حساب الدفع: 9147234", size=16,
                            weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=8)
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=15,
            width=320,
            bgcolor=ft.Colors.ORANGE_700,
            border_radius=12
        )
        # =========================================

        date_field = ft.TextField(
            label="تاريخ الموعد (مثال: 2026-06-15)",
            text_align=ft.TextAlign.RIGHT,
            width=320,
            border_color=ft.Colors.GREEN_400,
            focused_border_color=ft.Colors.GREEN_700
        )

        # ============ حقل إرفاق صورة (شكلي) ============
        image_preview = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.IMAGE, size=40, color=ft.Colors.GREY_500),
                ft.Text("لا توجد صورة", size=11, color=ft.Colors.GREY_600)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
            width=110,
            height=110,
            bgcolor=ft.Colors.GREY_200,
            border_radius=8,
            alignment=ft.Alignment.CENTER
        )

        def attach_image(e):
            show_snack("📎 ميزة إرفاق الصور ستتوفر قريباً")

        attach_btn = ft.Button(
            content="📎 إرفاق صورة",
            on_click=attach_image,
            width=200,
            height=50,
            bgcolor=ft.Colors.BLUE_600,
            color=ft.Colors.WHITE
        )
        # ==============================================

        def confirm_booking(e):
            date_val = date_field.value.strip() if date_field.value else ""
            if not date_val:
                show_snack("الرجاء تحديد تاريخ الموعد")
                return

            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO appointments (national_id, clinic_name, appointment_date)
                    VALUES (?, ?, ?)
                """, (current_patient["nat_id"], clinic_name, date_val))
                conn.commit()
                conn.close()
            except sqlite3.Error as db_err:
                show_snack(f"حدث خطأ في قاعدة البيانات: {db_err}")
                return

            show_snack("✅ تم تأكيد الحجز بنجاح")
            show_clinics_screen()

        confirm_btn = ft.Button(
            content="تأكيد الحجز",
            on_click=confirm_booking,
            width=320,
            height=45,
            bgcolor=ft.Colors.GREEN_600,
            color=ft.Colors.WHITE
        )

        back_btn = ft.TextButton(
            content="العودة للعيادات",
            on_click=lambda e: show_clinics_screen(),
            icon=ft.Icons.ARROW_BACK
        )

        page.add(
            ft.Column([
                ft.Text(f"حجز موعد في: {clinic_name}", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                ft.Container(height=10),
                # ============ بطاقة الدفع ============
                payment_card,
                ft.Container(height=15),
                # ====================================
                date_field,
                ft.Container(height=10),
                # ============ حقل إرفاق الصورة ============
                ft.Text("📎 إرفاق صورة (اختياري):", size=13, color=ft.Colors.GREY_700),
                ft.Container(height=5),
                ft.Row([
                    image_preview,
                    attach_btn
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
                ft.Container(height=10),
                # ==========================================
                confirm_btn,
                ft.Container(height=5),
                back_btn
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)
        )
        page.update()

    def show_clinics_screen():
        page.clean()

        clinics = [
            "عيادة الباطنية",
            "عيادة الجراحة",
            "عيادة الأطفال",
            "عيادة النساء والتوليد"
        ]

        clinic_buttons = []
        for c in clinics:
            btn = ft.Button(
                content=c,
                on_click=lambda e, name=c: show_booking_screen(name),
                width=320,
                height=45,
                bgcolor=ft.Colors.BLUE_50,
                color=ft.Colors.BLUE_900
            )
            clinic_buttons.append(btn)

        logout_btn = ft.TextButton(
            content="تسجيل الخروج",
            on_click=show_login_screen,
            icon=ft.Icons.LOGOUT
        )

        page.add(
            ft.Column([
                ft.Text("اختر العيادة المطلوبة", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                ft.Container(height=10),
                *clinic_buttons,
                ft.Container(height=15),
                logout_btn
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)
        )
        page.update()

    show_login_screen()


if __name__ == "__main__":
    ft.run(main)

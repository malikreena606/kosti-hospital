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
    page.title = "مستشفى كوستي التعليمي"
    page.rtl = True
    page.bgcolor = ft.colors.WHITE

    init_db()
    current_patient = {"nat_id": "", "clinic": ""}

    def show_snack(text):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(text, color=ft.colors.WHITE),
            bgcolor=ft.colors.BLUE_700
        )
        page.snack_bar.open = True
        page.update()

    def show_login_screen(e=None):
        page.clean()
        nat_id_field = ft.TextField(label="الرقم الوطني", width=320)
        phone_field = ft.TextField(label="رقم الهاتف", width=320)

        def handle_login(event):
            nat_id = nat_id_field.value.strip() if nat_id_field.value else ""
            phone = phone_field.value.strip() if phone_field.value else ""
            if not nat_id or not phone:
                show_snack("الرجاء إدخال البيانات")
                return
            current_patient["nat_id"] = nat_id
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM patients WHERE national_id = ?", (nat_id,))
                user = cursor.fetchone()
                if not user:
                    cursor.execute("INSERT INTO patients (national_id, phone_number) VALUES (?, ?)", (nat_id, phone))
                    conn.commit()
                conn.close()
            except sqlite3.Error as err:
                show_snack(f"خطأ: {err}")
                return
            show_clinics_screen()

        page.add(ft.Column([
            ft.Text("مستشفى كوستي التعليمي", size=22, weight=ft.FontWeight.BOLD),
            ft.Text("نظام الحجز الإلكتروني", size=14),
            nat_id_field,
            phone_field,
            ft.ElevatedButton(text="تسجيل الدخول", on_click=handle_login, width=320, height=45)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15))
        page.update()

    def show_booking_screen(clinic_name):
        page.clean()
        current_patient["clinic"] = clinic_name
        date_field = ft.TextField(label="تاريخ الموعد", width=320)

        # بطاقة السعر ورقم الحساب
        payment_card = ft.Container(
            content=ft.Column([
                ft.Text("سعر التذكرة: 5,000 جنيه", size=15,
                        weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
                ft.Text("رقم حساب الدفع: 9147234", size=15,
                        weight=ft.FontWeight.BOLD, color=ft.colors.WHITE)
            ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=15,
            width=320,
            bgcolor=ft.colors.ORANGE_700,
            border_radius=12
        )

        # معاينة الصورة
        image_preview = ft.Container(
            content=ft.Text("لا توجد صورة", size=11, color=ft.colors.GREY_600),
            width=110,
            height=110,
            bgcolor=ft.colors.GREY_200,
            border_radius=8,
            alignment=ft.alignment.center
        )

        def attach_image(e):
            show_snack("📎 ميزة إرفاق الصور ستتوفر قريباً")

        attach_btn = ft.ElevatedButton(
            text="📎 إرفاق صورة",
            on_click=attach_image,
            width=200,
            height=50
        )

        def confirm_booking(e):
            date_val = date_field.value.strip() if date_field.value else ""
            if not date_val:
                show_snack("أدخل التاريخ")
                return
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO appointments (national_id, clinic_name, appointment_date) VALUES (?, ?, ?)",
                               (current_patient["nat_id"], clinic_name, date_val))
                conn.commit()
                conn.close()
            except sqlite3.Error as err:
                show_snack(f"خطأ: {err}")
                return
            show_snack("✅ تم تأكيد الحجز بنجاح")
            show_clinics_screen()

        page.add(ft.Column([
            ft.Text(f"حجز موعد في: {clinic_name}", size=18, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            payment_card,
            ft.Container(height=10),
            date_field,
            ft.Container(height=10),
            ft.Text("إرفاق صورة (اختياري):", size=13),
            ft.Row([image_preview, attach_btn],
                   alignment=ft.MainAxisAlignment.CENTER, spacing=15),
            ft.Container(height=10),
            ft.ElevatedButton(text="تأكيد الحجز", on_click=confirm_booking, width=320, height=45),
            ft.TextButton(text="العودة", on_click=lambda e: show_clinics_screen())
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15))
        page.update()

    def show_clinics_screen():
        page.clean()
        clinics = ["عيادة الباطنية", "عيادة الجراحة", "عيادة الأطفال", "عيادة النساء والتوليد"]
        buttons = []
        for c in clinics:
            buttons.append(ft.ElevatedButton(
                text=c,
                on_click=lambda e, name=c: show_booking_screen(name),
                width=320,
                height=45
            ))

        page.add(ft.Column([
            ft.Text("اختر العيادة المطلوبة", size=20, weight=ft.FontWeight.BOLD),
            *buttons,
            ft.TextButton(text="تسجيل الخروج", on_click=show_login_screen)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12))
        page.update()

    show_login_screen()


if __name__ == "__main__":
    ft.app(target=main)

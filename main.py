import flet as ft
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kosti_hospital.db")

TICKET_PRICE = "10,000 جنيه"


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
    page.bgcolor = ft.Colors.WHITE
    page.window.width = 420
    page.window.height = 650

    init_db()
    current_patient = {"nat_id": "", "clinic": ""}

    def show_snack(text):
        page.show_dialog(
            ft.SnackBar(ft.Text(text, color=ft.Colors.WHITE), bgcolor=ft.Colors.BLUE_700)
        )

    # ==================== تسجيل الدخول ====================
    def show_login_screen(e=None):
        page.clean()
        nat_id_field = ft.TextField(label="الرقم الوطني", text_align=ft.TextAlign.RIGHT, width=320)
        phone_field = ft.TextField(label="رقم الهاتف", text_align=ft.TextAlign.RIGHT, width=320)

        def handle_login(event):
            nat_id = nat_id_field.value.strip() if nat_id_field.value else ""
            phone = phone_field.value.strip() if phone_field.value else ""
            # رقم الهاتف بدون شرط (يقبل أي رقم)
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
                    cursor.execute(
                        "INSERT INTO patients (national_id, phone_number) VALUES (?, ?)",
                        (nat_id, phone)
                    )
                    conn.commit()
                conn.close()
            except sqlite3.Error as err:
                show_snack(f"خطأ: {err}")
                return
            show_clinics_screen()

        page.add(ft.Column([
            ft.Container(
                content=ft.Text("مستشفى كوستي التعليمي", size=22,
                                weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                alignment=ft.Alignment.CENTER
            ),
            ft.Text("نظام الحجز الإلكتروني", size=14, color=ft.Colors.GREY_700),
            ft.Container(height=10),
            nat_id_field,
            phone_field,
            ft.Container(height=10),
            ft.Button(content="تسجيل الدخول", on_click=handle_login,
                      width=320, height=45,
                      bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15))
        page.update()

    # ==================== شاشة الحجز ====================
    def show_booking_screen(clinic_name):
        page.clean()
        current_patient["clinic"] = clinic_name

        date_field = ft.TextField(
            label="تاريخ الموعد",
            text_align=ft.TextAlign.RIGHT,
            width=320,
            border_color=ft.Colors.GREEN_400
        )

        # معاينة الصورة
        image_preview = ft.Container(
            content=ft.Text("لا توجد صورة", size=12, color=ft.Colors.GREY_600),
            width=100, height=100,
            bgcolor=ft.Colors.GREY_200,
            border_radius=8,
            alignment=ft.Alignment.CENTER
        )

        def attach_image(e):
            show_snack("📎 ميزة إرفاق الصور ستتوفر قريباً")

        def confirm_booking(e):
            date_val = date_field.value.strip() if date_field.value else ""
            if not date_val:
                show_snack("أدخل التاريخ")
                return
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO appointments (national_id, clinic_name, appointment_date) VALUES (?, ?, ?)",
                    (current_patient["nat_id"], clinic_name, date_val)
                )
                conn.commit()
                conn.close()
            except sqlite3.Error as err:
                show_snack(f"خطأ: {err}")
                return
            show_snack("✅ تم تأكيد الحجز بنجاح")
            show_clinics_screen()

        page.add(ft.Column([
            ft.Text(f"حجز في: {clinic_name}", size=18,
                    weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
            ft.Container(height=10),
            date_field,
            ft.Container(height=10),
            # حقل إرفاق صورة
            ft.Row([
                image_preview,
                ft.Button(
                    content="📎 إرفاق صورة",
                    on_click=attach_image,
                    width=180, height=45,
                    bgcolor=ft.Colors.PURPLE_600,
                    color=ft.Colors.WHITE
                )
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
            ft.Container(height=10),
            ft.Button(content="تأكيد الحجز", on_click=confirm_booking,
                      width=320, height=45,
                      bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE),
            ft.TextButton(content="العودة", on_click=lambda e: show_clinics_screen())
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15))
        page.update()

    # ==================== شاشة العيادات ====================
    def show_clinics_screen():
        page.clean()

        # 6 عيادات (بدون الجراحة)
        clinics = [
            "عيادة الباطنية",
            "عيادة الأطفال",
            "عيادة النساء والتوليد",
            "عيادة العظام",
            "عيادة المخ والأعصاب",
            "عيادة الجلدية"
        ]

        buttons = []
        for c in clinics:
            buttons.append(ft.Button(
                content=c,
                on_click=lambda e, name=c: show_booking_screen(name),
                width=320, height=45,
                bgcolor=ft.Colors.BLUE_50,
                color=ft.Colors.BLUE_900
            ))

        # بطاقة السعر
        price_card = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CONFIRMATION_NUMBER, color=ft.Colors.WHITE, size=28),
                ft.Text(f"سعر التذكرة: {TICKET_PRICE}", size=16,
                        weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
            padding=15,
            bgcolor=ft.Colors.ORANGE_600,
            border_radius=10,
            width=320
        )

        page.add(ft.Column([
            ft.Text("اختر العيادة", size=20,
                    weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
            ft.Container(height=5),
            price_card,
            ft.Container(height=10),
            *buttons,
            ft.Container(height=10),
            ft.TextButton(content="تسجيل الخروج", on_click=show_login_screen,
                          icon=ft.Icons.LOGOUT)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10))
        page.update()

    show_login_screen()


if __name__ == "__main__":
    ft.run(main)

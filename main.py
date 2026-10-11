import flet as ft


def main(page: ft.Page):
    page.title = "اختبار"
    page.rtl = True
    page.bgcolor = ft.Colors.WHITE

    page.add(
        ft.Text("مرحبا، التطبيق يعمل!", size=30, color=ft.Colors.BLUE)
    )
    page.update()


if __name__ == "__main__":
    ft.run(main)

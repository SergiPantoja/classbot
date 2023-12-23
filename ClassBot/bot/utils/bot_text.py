def main_menu(fullname: str, role: str = None, course_name: str = None, classroom_name: str = None, welcome: bool = False):
    text = ""
    if welcome:
        if role == "teacher":
            text += f"Hola profe {fullname}!\n"
        else:
            text += f"Hola {fullname}!\n"
    text += "Menú principal\n"
    if course_name:
        text += f"<b>Curso:</b> {course_name}\n"
    if classroom_name:
        text += f"<b>Aula:</b> {classroom_name}\n"
    return text


from telegram import InlineKeyboardButton


CANCEL = [["/cancel"]]
NEW_USER = [["Crear cuenta", "/cancel"]]
SELECT_ROLE = [["Estudiante", "Profesor"]]
TEACHER_LOGIN = [["Ingresar al aula", "Crear"]]
TEACHER_CREATE = [["Crear curso", "Crear aula"]]

TEACHER_MAIN_MENU = [["Opciones", "..."]]
TEACHER_SETTINGS = [["Editar curso", "Editar aula"], ["Atrás", "Salir"]]
TEACHER_EDIT_COURSE = [
    [
        InlineKeyboardButton("Cambiar nombre", callback_data="option_edit_course_name"),
        InlineKeyboardButton("Transferir", callback_data="option_transfer_course"),
    ],
    [
        InlineKeyboardButton("Eliminar", callback_data="option_delete_course"),
        InlineKeyboardButton("Otros cursos", callback_data="option_other_courses"),
    ],
    [InlineKeyboardButton("Atrás", callback_data="option_edit_course_back")], 
]

STUDENT_MAIN_MENU = [["Opciones", "..."]]

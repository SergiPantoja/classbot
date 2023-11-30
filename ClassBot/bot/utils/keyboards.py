from telegram import InlineKeyboardButton


CANCEL = [["/cancel"]]
NEW_USER = [["Crear cuenta", "/cancel"]]
SELECT_ROLE = [["Estudiante", "Profesor"]]
TEACHER_LOGIN = [["Ingresar al aula", "Crear"]]
TEACHER_CREATE = [["Crear curso", "Crear aula"]]

TEACHER_MAIN_MENU = [["Opciones", "Conferencias del aula"], ["..."]]
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
TEACHER_EDIT_CLASSROOM = [
    [
        InlineKeyboardButton("Cambiar nombre", callback_data="option_edit_classroom_name"),
        InlineKeyboardButton("Cambiar contraseñas", callback_data="option_edit_classroom_passwords"),
    ],
    [
        InlineKeyboardButton("Cambiar de aula", callback_data="option_change_classroom"),
        InlineKeyboardButton("Eliminar estudiantes", callback_data="option_remove_students"),
    ],
    [InlineKeyboardButton("Atrás", callback_data="option_edit_classroom_back")],
]
TEACHER_EDIT_CLASSROOM_OWNER = [
    [
        InlineKeyboardButton("Cambiar nombre", callback_data="option_edit_classroom_name"),
        InlineKeyboardButton("Cambiar contraseñas", callback_data="option_edit_classroom_passwords"),
    ],
    [
        InlineKeyboardButton("Cambiar de aula", callback_data="option_change_classroom"),
        InlineKeyboardButton("Eliminar estudiantes", callback_data="option_remove_students"),
    ],
    [
        InlineKeyboardButton("Eliminar profesores", callback_data="option_remove_teachers"),
        InlineKeyboardButton("Eliminar aula", callback_data="option_delete_classroom"),
    ],
    [InlineKeyboardButton("Atrás", callback_data="option_edit_classroom_back")],
]
TEACHER_CONFERENCE_CREATE = [
    [
        InlineKeyboardButton("Crear conferencia", callback_data="conference_create"),
        InlineKeyboardButton("Atrás", callback_data="conference_back"),
    ],
]
TEACHER_CONFERENCE_EDIT = [
    [
        InlineKeyboardButton("Cambiar nombre", callback_data="conference_edit_name"),
        InlineKeyboardButton("Cambiar fecha", callback_data="conference_edit_date"),
    ],
    [
        InlineKeyboardButton("Cambiar archivo", callback_data="conference_edit_file"),
        InlineKeyboardButton("Eliminar", callback_data="conference_edit_delete"),
    ],
    [InlineKeyboardButton("Atrás", callback_data="conference_back")],
]

STUDENT_MAIN_MENU = [["Opciones", "Inventario"], ["..."]]
STUDENT_INVENTORY = [["Medallas", "Atrás"]]

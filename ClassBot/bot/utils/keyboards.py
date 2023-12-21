from telegram import InlineKeyboardButton


CANCEL = [["/cancel"]]
NEW_USER = [["Crear cuenta", "/cancel"]]
SELECT_ROLE = [["Estudiante", "Profesor"]]
TEACHER_LOGIN = [["Ingresar al aula", "Crear"]]
TEACHER_CREATE = [["Crear curso", "Crear aula"]]

TEACHER_MAIN_MENU = [["Conferencias del aula", "Opciones"], ["Pendientes", "Gremios"], ["Actividades 📖", "Atrás"]]
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
TEACHER_PENDING_OPTIONS = [
    [
        InlineKeyboardButton("Aprobar", callback_data="pending_approve"),
        InlineKeyboardButton("Denegar", callback_data="pending_reject"),
    ],
    [
        InlineKeyboardButton("Asignar a otro profesor", callback_data="pending_assign"),
        InlineKeyboardButton("Pedir más información", callback_data="pending_ask_info"),
    ],
    [InlineKeyboardButton("Atrás", callback_data="back")],
]
TEACHER_FILTER_PENDING = [
    [
        InlineKeyboardButton("Intervención en clase", callback_data="filter_default:Intervención en clase"),
        InlineKeyboardButton("Propuesta de título", callback_data="filter_default:Propuesta de título"),
    ],
    [
        InlineKeyboardButton("Rectificación al profesor", callback_data="filter_default:Rectificación al profesor"),
        InlineKeyboardButton("Frase de estado", callback_data="filter_default:Frase de estado"),
    ],
    [
        InlineKeyboardButton("Meme", callback_data="filter_default:Meme"),
        InlineKeyboardButton("Chiste", callback_data="filter_default:Chiste"),
    ],
    [
        InlineKeyboardButton("Actualización de diario", callback_data="filter_default:Actualización de diario"),
        InlineKeyboardButton("Miscelánea", callback_data="filter_default:Miscelaneo"),
    ],
    [
        InlineKeyboardButton("Otras actividades", callback_data="filter_other_activities"),
        InlineKeyboardButton("Atrás", callback_data="back"),
    ]
]
TEACHER_GUILD = [
    [
        InlineKeyboardButton("Crear gremio", callback_data="create_guild"),
        InlineKeyboardButton("Atrás", callback_data="back"),
    ],
]
TEACHER_GUILD_OPTIONS = [
    [
        InlineKeyboardButton("Añadir estudiante", callback_data="guild_add_student"),
        InlineKeyboardButton("Eliminar estudiante", callback_data="guild_remove_student"),
    ],
    [
        InlineKeyboardButton("Cambiar nombre", callback_data="guild_change_name"),
        InlineKeyboardButton("Eliminar gremio", callback_data="guild_delete"),
    ],
    [
        InlineKeyboardButton("Detalles de los créditos", callback_data="guild_credits_details"),
        InlineKeyboardButton("Atrás", callback_data="back")
    ],
]
TEACHER_ACTIVITY_TYPE_OPTIONS = [
    [
        InlineKeyboardButton("Cambiar descripción" , callback_data="activity_type_change_description"),
        InlineKeyboardButton("Enviar otro archivo", callback_data="activity_type_change_file"),
    ],
    [
        InlineKeyboardButton("Ocultar actividad", callback_data="activity_type_hide"),
        InlineKeyboardButton("Atrás", callback_data="back")
    ]
]
TEACHER_ACTIVITY_OPTIONS =[
    [
        InlineKeyboardButton("Revisar actividad", callback_data="activity_review"),
    ],
    [
        InlineKeyboardButton("Cambiar nombre", callback_data="activity_change_name"),
        InlineKeyboardButton("Cambiar descripción", callback_data="activity_change_description"),
    ],
    [
        InlineKeyboardButton("Enviar otro archivo", callback_data="activity_change_file"),
        InlineKeyboardButton("Cambiar fecha de entrega", callback_data="activity_change_deadline"),
    ],
    [
        InlineKeyboardButton("Atrás", callback_data="back"),
    ],
]

STUDENT_MAIN_MENU = [["Conferencias", "Inventario"], ["Acciones", "Gremio"], ["Opciones", "Actividades 📝"], ["Atrás"]]
STUDENT_INVENTORY = [["Medallas", "Atrás"]]
STUDENT_CONFERENCE_SELECTED = [
    [
        InlineKeyboardButton("Proponer nuevo título", callback_data="new_title_proposal"),
        InlineKeyboardButton("Atrás", callback_data="back"),
    ],
]
STUDENT_ACTIONS = [
    [
        InlineKeyboardButton("Intervención en clase", callback_data="action_class_intervention"),
        InlineKeyboardButton("Rectificar a un profesor", callback_data="action_teacher_correction"),
    ],
    [
        InlineKeyboardButton("Frase de estado", callback_data="action_status_phrase"),
        InlineKeyboardButton("Actualizar diario", callback_data="action_diary_update"),
    ],
    [
        InlineKeyboardButton("Meme", callback_data="action_meme"),
        InlineKeyboardButton("Chiste", callback_data="action_joke"),
    ],
    [
        InlineKeyboardButton("Miscelánea", callback_data="action_misc"),
        InlineKeyboardButton("Atrás", callback_data="back"),
    ]
]


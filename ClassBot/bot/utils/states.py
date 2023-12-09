""" This file contains the states for the bot's conversation handlers. """

# user_login_conv states
NEW_USER, USER_ROLE, ROLE_SELECTED, TEACHER_LOGIN, TEACHER_CREATE, NEW_COURSE, SELECT_COURSE, NEW_CLASSROOM, STUDENT_LOGIN, TEACHER_ENTER = range(10)

# edit_course_conv states
EDIT_COURSE_CHOOSE_OPTION, EDIT_COURSE_SELECT_COURSE, EDIT_COURSE_NAME, DELETE_COURSE_CONFIRM, EDIT_COURSE_TRANSFER = range(5)
# edit_classroom_conv states
EDIT_CLASSROOM_CHOOSE_OPTION, EDIT_CLASSROOM_NAME, EDIT_CLASSROOM_PASSWORD, EDIT_CLASSROOM_CHANGE, EDIT_CLASSROOM_REMOVE_STUDENT, EDIT_CLASSROOM_REMOVE_TEACHER, EDIT_CLASSROOM_DELETE_CONFIRM = range(7)
# teacher_conference states
T_CREATE_CONFERENCE, T_SELECT_CONFERENCE, T_CREATE_CONFERENCE_NAME, T_CREATE_CONFERENCE_DATE, T_CREATE_CONFERENCE_FILE, T_CONFERENCE_EDIT_OPTION, T_EDIT_CONFERENCE_NAME, T_EDIT_CONFERENCE_DATE, T_EDIT_CONFERENCE_FILE = range(9)
# teacher_pending states
T_PENDING_SELECT, T_PENDING_OPTIONS, T_PENDING_ASSIGN_TEACHER = range(3)

# student_inventory medal_conv states
SI_SELECT_MEDAL = range(1)
# student_conference states
S_SELECT_CONFERENCE, S_NEW_TITLE_PROPOSAL = range(2)

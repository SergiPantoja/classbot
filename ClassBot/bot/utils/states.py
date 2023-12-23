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
T_PENDING_SELECT, T_PENDING_OPTIONS, T_PENDING_ASSIGN_TEACHER, T_PENDING_REJECT, T_PENDING_APPROVE, T_PENDING_MORE_INFO, T_PENDING_FILTER_ACTIVITY = range(7)
# teacher_guilds states
T_GUILD_CREATE, T_GUILD_SELECT, T_GUILD_CREATE_NAME, T_GUILD_OPTIONS, T_GUILD_OPTIONS_EDIT_NAME, T_GUILD_SELECT_STUDENT_TO_ADD, T_GUILD_SELECT_STUDENT_TO_REMOVE = range(7)
# teacher_activities states
T_ACTIVITIES_CREATE_TYPE, T_ACTIVITIES_TYPE_SEND_NAME, T_ACTIVITIES_TYPE_SEND_DESCRIPTION, T_ACTIVITIES_TYPE_SEND_GUILD_ACTIVITY, T_ACTIVITIES_TYPE_SEND_SINGLE_SUBMISSION, T_ACTIVITIES_TYPE_SEND_FILE, T_ACTIVITIES_TYPE_INFO, T_ACTIVITIES_TYPE_EDIT_DESCRIPTION, T_ACTIVITIES_TYPE_EDIT_FILE, T_ACTIVITIES_TYPE_HIDE, T_ACTIVITY_SEND_NAME, T_ACTIVITY_SEND_DESCRIPTION, T_ACTIVITY_SEND_FILE, T_ACTIVITY_SEND_DEADLINE, T_ACTIVITY_INFO, T_ACTIVITY_EDIT_NAME, T_ACTIVITY_EDIT_DESCRIPTION, T_ACTIVITY_EDIT_FILE, T_ACTIVITY_EDIT_DEADLINE, T_ACTIVITY_REVIEW, T_ACTIVITY_REVIEW_SELECT_REVIEWED, T_ACTIVITY_REVIEW_SEND_CREDITS = range(22)
# teacher_practic_classes states
T_CP_CREATE, T_CP_CREATE_STRING, T_CP_CREATE_DATE, T_CP_CREATE_DESCRIPTION, T_CP_CREATE_FILE, T_CP_INFO, T_CP_EDIT_DATE, T_CP_EDIT_DESCRIPTION, T_CP_EDIT_FILE, T_CP_DELETE, T_CP_CREATE_EXERCISE_NAME, T_CP_CREATE_EXERCISE_VALUE, T_CP_CREATE_EXERCISE_DESCRIPTION, T_CP_CREATE_EXERCISE_FILE, T_CP_CREATE_EXERCISE_PARTIAL_CREDITS = range(15)


# student_inventory medal_conv states
SI_SELECT_MEDAL = range(1)
# student_conference states
S_SELECT_CONFERENCE, S_NEW_TITLE_PROPOSAL = range(2)
# answer_pending states
S_SEND_ANSWER = range(1)
# student_actions states
S_ACTIONS_SELECT_ACTION, S_ACTIONS_SEND_MISC, S_ACTIONS_SELECT_INTERVENTION, S_ACTIONS_SEND_INTERVENTION, S_ACTIONS_SEND_RECTIFICATION, S_ACTIONS_SEND_STATUS_PHRASE, S_ACTIONS_SEND_MEME, S_ACTIONS_SEND_JOKE, S_ACTIONS_SEND_DIARY_UPDATE = range(9)
# student_activities states
S_ACTIVITY_TYPE_SELECT, S_ACTIVITY_TYPE_SEND_SUBMISSION, S_ACTIVITY_SELECT, S_ACTIVITY_SEND_SUBMISSION, S_ACTIVITY_TYPE_SEND_SUBMISSION_DONE, S_ACTIVITY_SEND_SUBMISSION_DONE = range(6)


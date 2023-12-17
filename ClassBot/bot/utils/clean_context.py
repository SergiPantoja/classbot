def clean_teacher_context(context):
    if "edit_course" in context.user_data:
        context.user_data.pop("edit_course")
    if "edit_classroom" in context.user_data:
        context.user_data.pop("edit_classroom")
    if "conference" in context.user_data:
        context.user_data.pop("conference")
    if "paginator" in context.user_data:
        context.user_data.pop("paginator")
    if "pending" in context.user_data:
        context.user_data.pop("pending")

def clean_student_context(context):
    if "pending_answer" in context.user_data:
        context.user_data.pop("pending_answer")
    if "conference" in context.user_data:
        context.user_data.pop("conference")
    if "actions" in context.user_data:
        context.user_data.pop("actions")
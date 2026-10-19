import oracledb

connection = oracledb.connect(
    user="MOC_project",
    password="chandan",
    dsn="localhost/xepdb1"
)

TRANSITIONS = {
    ("Registered", "pay_fee"): "FeePaid",
    ("Registered", "cancel_registration"): "Cancelled",
    ("FeePaid", "generate_hall_ticket"): "HallTicketIssued",
    ("FeePaid", "request_refund"): "Registered",
    ("HallTicketIssued", "mark_attendance"): "ExamTaken",
    ("HallTicketIssued", "mark_absent"): "Absent",
    ("ExamTaken", "submit_evaluation"): "Evaluated",
    ("Evaluated", "flag_discrepancy"): "UnderReview",
    ("Evaluated", "publish_result"): "ResultPublished",
    ("UnderReview", "revert_evaluation"): "ExamTaken",
    ("UnderReview", "confirm_evaluation"): "Evaluated",
}
def has_permission(cursor, role, event):
    cursor.execute(
        "SELECT COUNT(*) FROM permissions WHERE role = :role AND event = :event",
        role=role, event=event
    )
    return cursor.fetchone()[0] > 0

def transition(connection, student_id, event, actor_role, actor_user_id):
    cursor = connection.cursor()

    # 1. Get current state
    cursor.execute(
        "SELECT exam_status FROM students WHERE student_id = :sid",
        sid=student_id
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"No such student: {student_id}")
    current_state = row[0]

    # 2. Check the move is valid in the FSM
    key = (current_state, event)
    if key not in TRANSITIONS:
        raise ValueError(f"Invalid transition: cannot '{event}' from '{current_state}'")
    next_state = TRANSITIONS[key]

    # 3. Check role permission (skip for system-triggered events)
    if event != "payment_failed":
        if not has_permission(cursor, actor_role, event):
            raise PermissionError(f"Role '{actor_role}' cannot trigger '{event}'")

    # 4. Apply the transition
    cursor.execute(
        "UPDATE students SET exam_status = :next_state WHERE student_id = :sid",
        next_state=next_state, sid=student_id
    )

    # 5. Log it
    cursor.execute(
    	"""INSERT INTO audit_log
       	   (user_id, student_id, event, old_state, new_state)
       	   VALUES (:1, :2, :3, :4, :5)""",
        [actor_user_id, student_id, event, current_state, next_state]
    )

    connection.commit()
    return next_state

# test it
new_state = transition(connection, "S000123", "pay_fee", "Student", 1)
print(new_state)
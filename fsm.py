import logging
from db import get_db

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Formal DFA components
# ------------------------------------------------------------------

Q = frozenset({
    'Registered', 'FeePaid', 'HallTicketIssued',
    'ExamTaken', 'Evaluated', 'UnderReview',
    'ResultPublished', 'Cancelled', 'Absent'
})

SIGMA = frozenset({
    'pay_fee', 'payment_failed', 'cancel_registration',
    'generate_hall_ticket', 'request_refund',
    'mark_attendance', 'mark_absent',
    'submit_evaluation', 'flag_discrepancy',
    'publish_result', 'revert_evaluation',
    'confirm_evaluation'
})

q0 = 'Registered'

F = frozenset({'ResultPublished', 'Cancelled', 'Absent'})

# δ: Q × Σ → Q  (partial function — undefined transitions are rejected)
DELTA = {
    ('Registered',        'pay_fee'):               'FeePaid',
    ('Registered',        'payment_failed'):         'Registered',
    ('Registered',        'cancel_registration'):    'Cancelled',
    ('FeePaid',           'generate_hall_ticket'):   'HallTicketIssued',
    ('FeePaid',           'request_refund'):         'Registered',
    ('HallTicketIssued',  'mark_attendance'):        'ExamTaken',
    ('HallTicketIssued',  'mark_absent'):            'Absent',
    ('ExamTaken',         'submit_evaluation'):      'Evaluated',
    ('Evaluated',         'flag_discrepancy'):       'UnderReview',
    ('Evaluated',         'publish_result'):         'ResultPublished',
    ('UnderReview',       'revert_evaluation'):      'ExamTaken',
    ('UnderReview',       'confirm_evaluation'):     'Evaluated',
}

# Role-based permission map (also enforced at DB level via PERMISSIONS table)
ROLE_PERMISSIONS = {
    'Student':   {'pay_fee', 'cancel_registration'},
    'Admin':     {'cancel_registration', 'request_refund'},
    'Faculty':   {'mark_attendance', 'mark_absent', 'submit_evaluation', 'flag_discrepancy'},
    'ExamCell':  {'generate_hall_ticket', 'confirm_evaluation', 'revert_evaluation', 'publish_result'},
    'HOD':       set(),  # retained as a read-only account role
    'SYSTEM':    {'payment_failed'},   # triggered by payment gateway callback
}


class ExamFSM:
    """
    DFA-based exam lifecycle controller.

    Implements M = (Q, Σ, δ, q0, F) where the transition relation δ is
    enforced both in-memory (Python dict) and at the Oracle DB layer via
    CHECK constraints on the exam_status column.
    """

    def __init__(self):
        self.Q = Q
        self.Sigma = SIGMA
        self.delta = DELTA
        self.q0 = q0
        self.F = F
        self.role_permissions = ROLE_PERMISSIONS

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_available_events(self, current_state, role):
        """Return events valid from current_state AND allowed for role."""
        allowed_by_role = self.role_permissions.get(role, set())
        return [
            event for (state, event) in self.delta.keys()
            if state == current_state and event in allowed_by_role
        ]

    # Alias used in some route files
    def available_events(self, current_state, role):
        return self.get_available_events(current_state, role)

    def validate_transition(self, current_state, event, role):
        """
        Validate a proposed transition.

        Raises:
            ValueError       – unknown state/event, undefined δ, or terminal state
            PermissionError  – role not authorised for event

        Returns:
            str – the next state
        """
        if current_state not in self.Q:
            raise ValueError(f"Unknown state: {current_state!r}")
        if event not in self.Sigma:
            raise ValueError(f"Unknown event: {event!r}")
        if current_state in self.F:
            raise ValueError(
                f"Terminal state {current_state!r} — no outgoing transitions"
            )

        # Role permission check (SYSTEM events bypass)
        if role != 'SYSTEM':
            allowed = self.role_permissions.get(role, set())
            if event not in allowed:
                raise PermissionError(
                    f"Role '{role}' is not permitted to trigger '{event}'"
                )

        # Transition function δ
        key = (current_state, event)
        if key not in self.delta:
            raise ValueError(
                f"No transition defined: δ({current_state!r}, {event!r}) is undefined"
            )

        return self.delta[key]

    # ------------------------------------------------------------------
    # Core operation — two calling conventions supported
    # ------------------------------------------------------------------

    def transition(self, student_id, event, role, user_id,
                   current_state=None, conn=None):
        """
        Execute a state transition atomically.

        Parameters
        ----------
        student_id    : str   – PK in STUDENTS table  (e.g. 'S001')
        event         : str   – symbol ∈ Σ
        role          : str   – role of the actor
        user_id       : int   – user_id of the actor (for audit log)
        current_state : str   – optional pre-fetched state (avoids extra DB round-trip)
        conn          : conn  – optional existing connection (caller manages commit)

        Returns
        -------
        (old_state, new_state) : tuple[str, str]
        """
        # Convert student_id to string always (routes may pass ints from URL)
        student_id = str(student_id)

        def _do_transition(conn_inner):
            cur = conn_inner.cursor()

            # Lock and trust the row value, never a stale value from a form or
            # an earlier unlocked SELECT.
            cur.execute(
                "SELECT exam_status FROM students WHERE student_id = :sid FOR UPDATE",
                sid=student_id,
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Student not found: {student_id}")
            cs = row[0]

            # 2. Validate via DFA
            ns = self.validate_transition(cs, event, role)

            # Oracle's transition relation is the authoritative persisted
            # definition. The Python DFA independently checks that both
            # representations agree before a state change is committed.
            cur.execute(
                "SELECT to_state FROM fsm_transitions WHERE from_state = :src AND event = :ev",
                src=cs, ev=event,
            )
            db_transition = cur.fetchone()
            if not db_transition:
                raise ValueError(f"Oracle transition table has no move for {cs} / {event}")
            if db_transition[0] != ns:
                raise RuntimeError("Python DFA and Oracle transition table disagree")

            if role != 'SYSTEM':
                cur.execute(
                    "SELECT 1 FROM permissions WHERE role = :role AND event = :ev",
                    role=role, ev=event,
                )
                if not cur.fetchone():
                    raise PermissionError(f"Role '{role}' is not authorised for '{event}' in Oracle")
            elif event != 'payment_failed':
                raise PermissionError("SYSTEM is authorised only for the payment_failed callback")

            # 3. Persist new state
            cur.execute(
                "UPDATE students SET exam_status = :ns WHERE student_id = :sid",
                ns=ns, sid=student_id
            )

            # 4. Audit log  (user_id=0 for SYSTEM events)
            # NULL is valid for the external gateway actor; zero would violate
            # the AUDIT_LOG foreign key to USERS.
            uid = user_id if user_id else None
            cur.execute(
                """INSERT INTO audit_log (user_id, student_id, event, old_state, new_state)
                   VALUES (:actor_user_id, :student_key, :event_key, :old_status, :new_status)""",
                actor_user_id=uid, student_key=student_id,
                event_key=event, old_status=cs, new_status=ns
            )

            logger.info(
                "FSM: student=%s | %s --%s--> %s | actor=%s role=%s",
                student_id, cs, event, ns, user_id, role
            )
            return cs, ns

        if conn is not None:
            # Caller owns the connection and commit
            return _do_transition(conn)
        else:
            # Own the connection ourselves
            with get_db() as c:
                return _do_transition(c)

    # ------------------------------------------------------------------
    # Serialisation for frontend FSM diagram
    # ------------------------------------------------------------------

    def to_dict(self):
        """Serialise the DFA definition for the /api/fsm endpoint."""
        return {
            'states': list(self.Q),
            'alphabet': list(self.Sigma),
            'initial': self.q0,
            'accepting': list(self.F),
            'transitions': [
                {'from': s, 'event': e, 'to': t}
                for (s, e), t in self.delta.items()
            ]
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
fsm = ExamFSM()

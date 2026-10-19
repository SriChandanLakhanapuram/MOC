# A DFA-Governed University Examination Workflow with Oracle Persistence

**Project report — implementation and design study**  
Author: *[Student name]*  
Department: *[Department / institution]*  
Course: *[Course code and title]*  
Date: *[Submission date]*

## Abstract

This project develops a browser-based university examination workflow in which each student's examination record moves through a finite set of explicitly defined states. A deterministic finite automaton (DFA) models the lifecycle from registration to result publication, cancellation, or absence. Events are restricted by both their source state and the role that requests them. The prototype uses Python and Flask for the web application, Oracle Database for relational persistence, and an Oracle transition relation that is checked against the Python DFA before a state change is committed. State changes and audit records are written in one database transaction. Student, faculty, administrator, and examination-cell screens expose the actions appropriate to their roles, while a DFA page presents the formal model. The report describes the model, database design, implementation decisions, known limitations, and a verification plan. Performance figures and claims of measured correctness are intentionally omitted: they must be collected from a reproducible run before submission.

**Keywords:** deterministic finite automaton, examination workflow, Oracle Database, Flask, RBAC, transaction, audit trail

## 1. Introduction

An examination lifecycle involves multiple people, records, and decisions. A payment may be accepted or declined; a ticket may be issued; attendance may be recorded; marks may be evaluated, reviewed, and published. When these steps are implemented as unrelated forms and direct updates, it is difficult to see which actions are valid at each stage or to reconstruct why a record changed.

This project makes the lifecycle explicit. The current state and requested event determine one next state, or the request is rejected. A role policy constrains who may request an event. Oracle stores the student record, permissions, DFA transition relation, and event history. This is a course project prototype, not a production payment or examination platform.

### 1.1 Objectives

1. Specify examination progress as a DFA from the supplied transition table.
2. Give students, faculty, administrators, and examination-cell staff role-specific browser workflows.
3. Persist state, payments, hall tickets, marks, and audit entries in Oracle.
4. Demonstrate relational constraints, transactions, and a database-resident transition relation.
5. Make the automaton inspectable through a state diagram and transition table.

### 1.2 Contributions and boundaries

The project's main contribution is the direct connection between a Theory of Computation model and a DBMS-backed workflow: one transition definition is visible in Python and Oracle, and the application checks that both representations agree before it updates a student. The prototype also keeps an actor-permission relation and writes an audit record with each transition.

The work does not claim new automata theory, measured production performance, formal proof by an external model checker, or integration with a real payment gateway. The local callback is a demonstration mechanism and must not be treated as payment verification.

## 2. Related work and design basis

Finite automata provide a well-established model for systems whose next control state depends on a finite current state and an input symbol [1–5]. A DFA transition function is deterministic: a state/event pair has at most one next state. This property gives the project a simple basis for accepting or rejecting proposed lifecycle actions. The system is a workflow application of this formalism rather than an extension of automata theory.

Role-based access control (RBAC) associates permissions with roles and assigns users to roles, which supports centrally understandable authorization policies [6–9]. This project applies that separation to event permissions: for example, `mark_attendance` is assigned to Faculty and `publish_result` to ExamCell. The authorization check is distinct from the DFA check. An event can be structurally valid and still be denied to the requesting role.

Workflow research includes richer formalisms such as Petri nets, which can represent concurrency and synchronization [10–11]. The per-student examination path in this project is modelled as a sequential state machine. Institution-wide parallel activity comes from multiple student records progressing independently. If a future workflow needs concurrent approvals or parallel examination components within one student record, a Petri-net or another concurrent model may be more suitable.

Relational database transactions provide the atomic boundary needed to update the student state and append an audit row together [12–14]. A failed operation should leave neither partial result behind. Oracle constraints and keys also express data integrity rules declaratively. The application uses parameterized SQL and a row lock around transitions, while the database transition table provides a persistent copy of the workflow relation.

## 3. Requirements and workflow

### 3.1 States

Let the state set be:

`Q = {Registered, FeePaid, HallTicketIssued, ExamTaken, Evaluated, UnderReview, ResultPublished, Cancelled, Absent}`.

`Registered` is the initial state. The terminal states are `ResultPublished`, `Cancelled`, and `Absent`. A terminal state has no outgoing transition. `payment_failed` is a self-transition on `Registered`; it records a failed attempt without advancing the registration.

### 3.2 Events and transition relation

The event alphabet is:

`Σ = {pay_fee, payment_failed, cancel_registration, generate_hall_ticket, request_refund, mark_attendance, mark_absent, submit_evaluation, flag_discrepancy, publish_result, revert_evaluation, confirm_evaluation}`.

The partial transition function `δ: Q × Σ ⇀ Q` is:

| Current state | Event | Next state |
|---|---|---|
| Registered | pay_fee | FeePaid |
| Registered | payment_failed | Registered |
| Registered | cancel_registration | Cancelled |
| FeePaid | generate_hall_ticket | HallTicketIssued |
| FeePaid | request_refund | Registered |
| HallTicketIssued | mark_attendance | ExamTaken |
| HallTicketIssued | mark_absent | Absent |
| ExamTaken | submit_evaluation | Evaluated |
| Evaluated | flag_discrepancy | UnderReview |
| Evaluated | publish_result | ResultPublished |
| UnderReview | revert_evaluation | ExamTaken |
| UnderReview | confirm_evaluation | Evaluated |

For any pair absent from the table, `δ` is undefined and the application rejects the event. In particular, no transition can leave an exit state.

### 3.3 Role/event policy

| Event | Authorized role |
|---|---|
| pay_fee | Student |
| payment_failed | Payment gateway callback (system actor) |
| cancel_registration | Student, Admin |
| generate_hall_ticket | ExamCell |
| request_refund | Admin |
| mark_attendance | Faculty (invigilator) |
| mark_absent | Faculty |
| submit_evaluation | Faculty |
| flag_discrepancy | Faculty |
| confirm_evaluation | ExamCell |
| revert_evaluation | ExamCell |
| publish_result | ExamCell |

`HOD` exists as a recognized account role in the prototype but receives no workflow-event permission in the supplied policy. It may be removed from the role list if it is not needed.

## 4. Formal model

The workflow automaton is `M = (Q, Σ, δ, q₀, F)`, where `q₀ = Registered` and `F = {ResultPublished, Cancelled, Absent}`. It is a partial DFA transition function because not every state/event pair is defined. A run over a finite event sequence is the sequence of states obtained by repeatedly applying `δ`; if a pair is undefined, the run rejects at that point.

The language accepted by the lifecycle model consists of event sequences that begin at `Registered`, follow only defined transitions, and end in a terminal state. `payment_failed` may repeat in `Registered`; the remaining normal path proceeds through fee payment, ticket issue, attendance, evaluation, and publication, with review and cancellation branches as shown in the transition table.

The program enforces transition validity and authorization as separate predicates:

`Allowed(current_state, event, role) = Definedδ(current_state, event) ∧ Authorized(role, event)`.

The next state exists only if both predicates hold. This extended guard is an application-level policy around the DFA; role membership is not itself part of the classical DFA tuple.

## 5. System design

### 5.1 Components

The browser sends requests to Flask routes grouped by role. A route verifies the session role, collects the requested event, and calls the transition engine. The engine locks the student row, reads the actual persisted state, checks the in-memory model, checks the Oracle transition relation and role/event permission, updates the record, and appends an audit entry. Related records such as a payment, ticket, or mark are written in the same connection scope.

The Oracle schema contains `USERS`, `STUDENTS`, `COURSES`, `PERMISSIONS`, `FEE_PAYMENTS`, `HALL_TICKETS`, `MARKS`, and `AUDIT_LOG`. The added `FSM_STATES` and `FSM_TRANSITIONS` tables represent the automaton. `STUDENTS.EXAM_STATUS` has a check constraint restricting values to the nine defined states. Primary and foreign keys connect the student, user, course, payment, ticket, marks, and audit records.

### 5.2 Transaction and concurrency handling

The transition engine selects a student row `FOR UPDATE`, so two concurrent requests for the same student do not both make a decision from the same unlocked value. It reads the locked row's current status and validates against that value. Updating `STUDENTS` and inserting `AUDIT_LOG` occur on the same connection. The `get_db` context manager commits on normal exit and rolls back on exception. This follows the atomicity goal of transaction processing [12–14].

This implementation does not yet provide an Oracle PL/SQL transition procedure. The database contributes relational constraints, the persisted transition relation, locking, and transaction control; the Python engine orchestrates the operation. A future iteration could move the transition and audit operation into a stored procedure and compare the two approaches.

### 5.3 Audit trace

Each accepted event records the student, actor when available, event symbol, old state, new state, and database timestamp. A failed gateway callback has no local user identity and is stored with a null user reference. Rejected requests are not state transitions and are not currently written to a separate security log. The audit table is an operational trace, not a tamper-proof ledger; database administrators can modify ordinary rows.

### 5.4 Web roles

- **Student:** view own state and payment/ticket/result data, pay the fee, or request cancellation.
- **Faculty:** record attendance/absence and submit marks for eligible students.
- **Admin:** inspect the cohort, request refunds, cancel eligible registrations, inspect audit events, and manage accounts.
- **ExamCell:** issue hall tickets, resolve review outcomes, publish results, and inspect aggregate state counts.

Route decorators restrict pages, while the DFA engine checks each event's role. Hiding a button in the browser is not authorization; the server performs the decisive checks.

## 6. Implementation

The prototype is implemented in Python with Flask blueprints and Jinja templates. `fsm.py` defines `Q`, `Σ`, `δ`, the initial and terminal states, and role permissions. `db.py` provides a lazily initialized `python-oracledb` connection pool. Route modules implement login and the four role workflows. The `/fsm` page and `/api/fsm` endpoint expose the automaton for presentation. The SQL files define the base schema, demo data, and an additive compatibility patch for columns used by the web screens and the database-resident transition relation.

Passwords in the original prototype were SHA-256 digests. The revised login path accepts those legacy rows once and upgrades a successfully verified password to Werkzeug's salted password-hash format. Newly added users use the stronger format directly. The clean-database demo account hash can therefore be used for the first login, after which it is upgraded on successful authentication.

The local `payment_callback` endpoint is a classroom simulation. It does not validate a provider signature, reconcile a signed order, or prevent replay. A real payment integration must authenticate the provider callback, bind it to a pending payment record, and make callback processing idempotent before it can be used for actual payments.

## 7. Database and Theory of Computation demonstration

The DFA is represented in three connected ways:

1. A formal transition table in this report.
2. Python constants used for quick validation, serialization, and the browser visualization.
3. Oracle `FSM_STATES` and `FSM_TRANSITIONS` rows checked before each persisted change.

The third representation makes the DBMS role visible: workflow rules are queryable data with keys and references, while the student row is the current automaton configuration. The application compares the Oracle next state with the Python next state and stops if they differ. `PERMISSIONS` stores the event/role relation. This makes a policy change reviewable as data, though the application code and database seed must still be kept in sync.

For a viva or demonstration, select a student in `Registered`, show the student dashboard, pay the fee, and inspect the changed `EXAM_STATUS` and `AUDIT_LOG` row. Then show the newly enabled ExamCell ticket action. Try an illegal event or a wrong-role action and show that the row remains unchanged. Finally, inspect `FSM_TRANSITIONS` and the `/fsm` visualization. Repeat with `payment_failed` to show that a valid self-transition is logged without changing the state.

## 8. Verification and observed results

The project was run locally with Python 3.12, Flask 3.1.2, python-oracledb 26.0.1, and the supplied Oracle XE service. A read-only inventory showed that the original database had the base tables and records, but no persisted DFA tables or route-specific columns. The additive migration created nine state rows and twelve transition rows, added the columns used by the application, and aligned the ExamCell grants. The existing records were preserved. Two fresh demo student records and demo accounts for all four application roles were added with the repeatable `demo_accounts.sql` seed.

The Flask test client exercised a complete record lifecycle for the isolated demo student `SDEMO03`: `Registered → FeePaid → HallTicketIssued → ExamTaken → Evaluated → UnderReview → Evaluated → ResultPublished`. The run created seven transition audit records and verified the published mark from the student result route. A forced failed payment callback on the separate demo student `SDEMO02` left it in `Registered`, created a `Failed` payment row, and logged the self-transition. A Faculty attendance request from `Registered` was rejected and left that record unchanged. Unit-level checks also rejected a wrong-role event and a request to leave a terminal state. Public routes, the DFA JSON endpoint, the report page, and all role templates were rendered successfully; the DFA browser page was opened locally.

These checks cover representative valid, invalid, role, persistence, and reporting paths. They do not exhaustively execute all 108 state/event combinations, verify duplicate real-provider callbacks, perform load testing, or measure production performance. No latency, throughput, or generalized correctness percentage is claimed.

## 9. Limitations and next steps

1. **Oracle migration:** `schema_patch.sql` is a one-time patch for the base schema in `MOC_PROJECT.sql`; it should first be checked against the tables already installed in the user's database.
2. **Security hardening:** configure a strong Flask secret, serve only over HTTPS outside local demo, add CSRF protection, rate limiting, account recovery, and least-privilege Oracle grants.
3. **Payment integration:** replace the demonstration callback with an authenticated, signed, idempotent provider webhook.
4. **Identity and faculty assignment:** add explicit course/exam assignment so faculty see only students in their invigilation/evaluation scope.
5. **Result correction:** specify a controlled post-publication correction or revaluation process; published results are terminal in the current model.
6. **Automated verification:** add unit and integration tests generated from the transition and permission tables, then record repeatable environment details and outcomes.
7. **Stored procedure:** implement and test a PL/SQL operation that performs transition lookup, authorization, state update, and audit insert atomically.

## 10. Conclusion

This project turns a university examination lifecycle into an explicit partial DFA and connects that model to an Oracle-backed web application. Its useful distinction is between a permitted transition and a permitted actor: both must agree before the student record changes. Persisting the transition relation, locking the current student row, and writing an audit record in the same transaction provides a concrete bridge between Theory of Computation and DBMS topics. The prototype provides role-specific browser workflows and a visual state-machine explanation, while its database connection, route/schema compatibility, security, and test evidence still need to be verified in the target environment before the work is described as complete.

## References

1. Hopcroft, J. E., Motwani, R., and Ullman, J. D. *Introduction to Automata Theory, Languages, and Computation*, 3rd ed. Pearson/Addison-Wesley, 2006.
2. Sipser, M. *Introduction to the Theory of Computation*, 3rd ed. Cengage Learning, 2013.
3. Rabin, M. O., and Scott, D. “Finite Automata and Their Decision Problems.” *IBM Journal of Research and Development*, 3(2), 114–125, 1959. https://doi.org/10.1147/rd.32.0114
4. Hopcroft, J. E. “An n log n Algorithm for Minimizing States in a Finite Automaton.” In *Theory of Machines and Computations*, 189–196, 1971.
5. Moore, E. F. “Gedanken-Experiments on Sequential Machines.” In *Automata Studies*, 129–153. Princeton University Press, 1956.
6. Sandhu, R. S., Coyne, E. J., Feinstein, H. L., and Youman, C. E. “Role-Based Access Control Models.” *Computer*, 29(2), 38–47, 1996. https://doi.org/10.1109/2.485845
7. Ferraiolo, D. F., Sandhu, R., Gavrila, S., Kuhn, D. R., and Chandramouli, R. “Proposed NIST Standard for Role-Based Access Control.” *ACM Transactions on Information and System Security*, 4(3), 224–274, 2001. https://doi.org/10.1145/501978.501980
8. Sandhu, R., Ferraiolo, D., and Kuhn, R. “The NIST Model for Role-Based Access Control: Towards a Unified Standard.” In *Proceedings of the Fifth ACM Workshop on Role-Based Access Control*, 2000. https://doi.org/10.1145/344287.344301
9. Ferraiolo, D. F., and Kuhn, D. R. “Role-Based Access Controls.” In *15th National Computer Security Conference*, 1992.
10. van der Aalst, W. M. P. “The Application of Petri Nets to Workflow Management.” *Journal of Circuits, Systems, and Computers*, 8(1), 21–66, 1998. https://doi.org/10.1142/S0218126698000043
11. van der Aalst, W. M. P., and van Hee, K. M. *Workflow Management: Models, Methods, and Systems*. MIT Press, 2002.
12. Gray, J., and Reuter, A. *Transaction Processing: Concepts and Techniques*. Morgan Kaufmann, 1992.
13. Bernstein, P. A., Hadzilacos, V., and Goodman, N. *Concurrency Control and Recovery in Database Systems*. Addison-Wesley, 1987.
14. Date, C. J. *An Introduction to Database Systems*, 8th ed. Pearson, 2003.
15. Saltzer, J. H., and Schroeder, M. D. “The Protection of Information in Computer Systems.” *Proceedings of the IEEE*, 63(9), 1278–1308, 1975. https://doi.org/10.1109/PROC.1975.9939
16. Workflow Management Coalition. *Terminology & Glossary*, Document WFMC-TC-1011, Issue 3, 1999.
17. Object Management Group. *Business Process Model and Notation (BPMN), Version 2.0*, 2011.
18. National Institute of Standards and Technology. *Digital Identity Guidelines: Authentication and Lifecycle Management*, NIST SP 800-63B, 2017 (and current revision).
19. Oracle. *Oracle Database Concepts* and *PL/SQL Language Reference*, documentation for the installed Oracle Database release.
20. Oracle. *python-oracledb Documentation*, connection pooling, transactions, and SQL execution, https://python-oracledb.readthedocs.io/.
21. Pallets Projects. *Flask Documentation*, sessions, request handling, and security, https://flask.palletsprojects.com/.
22. ISO/IEC. *ISO/IEC 25010:2011 Systems and Software Engineering — Systems and Software Quality Requirements and Evaluation (SQuaRE) — System and Software Quality Models*, 2011.

---

**Submission note:** Replace the bracketed front matter with your actual details, confirm your institution's citation format, and append the verified test results and screenshots from your own Oracle installation. The bibliography provides background sources; it does not imply that each source was experimentally evaluated in this project.

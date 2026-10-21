from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'ExamFlow_Project_Report.docx'
TMP = ROOT / '_report_figures'
TMP.mkdir(exist_ok=True)

FOREST = '#285345'
DEEP = '#1f4338'
MINT = '#d9ebe3'
PAPER = '#fbf5df'
SUN = '#f1cf62'
CORAL = '#e8846d'
INK = '#233b3a'
MUTED = '#607573'
LINE = '#bfd3ca'

def font(size, bold=False):
    candidates = [
        r'C:\Windows\Fonts\arialbd.ttf' if bold else r'C:\Windows\Fonts\arial.ttf',
        r'C:\Windows\Fonts\calibrib.ttf' if bold else r'C:\Windows\Fonts\calibri.ttf',
    ]
    for name in candidates:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()

def draw_arrow(draw, a, b, color=FOREST, width=4, head=14):
    draw.line([a, b], fill=color, width=width)
    import math
    angle = math.atan2(b[1]-a[1], b[0]-a[0])
    p1 = (b[0]-head*math.cos(angle-0.48), b[1]-head*math.sin(angle-0.48))
    p2 = (b[0]-head*math.cos(angle+0.48), b[1]-head*math.sin(angle+0.48))
    draw.polygon([b, p1, p2], fill=color)

def make_architecture():
    w, h = 1750, 790
    im = Image.new('RGB', (w, h), '#fffdf5')
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((22, 22, w-22, h-22), radius=24, fill='#f2f6ef', outline=LINE, width=3)
    d.text((55, 45), 'REQUEST PATH AND DATABASE RESPONSIBILITIES', font=font(28, True), fill=DEEP)
    boxes = [
        (55, 155, 400, 385, 'Browser', 'Role workspace\nForms and navigation\nSigned-in session'),
        (480, 155, 825, 385, 'Flask routes', 'Blueprints by role\nInput and CSRF checks\nHTML responses'),
        (905, 155, 1250, 385, 'Python workflow', 'Role authorization\nDFA transition checks\nTransaction orchestration'),
        (1330, 155, 1695, 385, 'Oracle Database', 'Domain tables and keys\nFSM transitions and roles\nAudit and history records'),
    ]
    for x1,y1,x2,y2,title,body in boxes:
        d.rounded_rectangle((x1,y1,x2,y2), radius=20, fill=PAPER, outline=FOREST, width=3)
        d.rounded_rectangle((x1,y1,x2,y1+58), radius=18, fill=MINT, outline=FOREST, width=2)
        d.rectangle((x1,y1+38,x2,y1+60), fill=MINT)
        d.text((x1+18,y1+14),title,font=font(23,True),fill=DEEP)
        d.multiline_text((x1+20,y1+82),body,font=font(18),fill=INK,spacing=15)
    for x in [400,825,1250]:
        draw_arrow(d,(x+8,270),(x+70,270),FOREST,5,16)
    d.rounded_rectangle((210, 490, 1540, 710), radius=24, fill='#e9efe4', outline=LINE, width=3)
    d.text((250, 515), 'One protected state change', font=font(25,True), fill=DEEP)
    steps = ['lock enrollment row', 'validate Python DFA', 'compare Oracle rule', 'write state and audit', 'commit or roll back']
    start, gap = 255, 255
    for i, s in enumerate(steps):
        x = start + i*gap
        d.ellipse((x, 590, x+46, 636), fill=SUN, outline=FOREST, width=2)
        d.text((x+15,598),str(i+1),font=font(18,True),fill=DEEP)
        d.multiline_text((x+58,586),s,font=font(16,True),fill=INK,spacing=5)
    im.save(TMP/'architecture.png')

def make_state_diagram():
    w, h = 1840, 760
    im = Image.new('RGB', (w,h), '#fffdf5')
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((18,18,w-18,h-18),radius=24,fill='#f2f6ef',outline=LINE,width=3)
    d.text((48,38),'EXAM ENROLLMENT STATE MACHINE',font=font(28,True),fill=DEEP)
    nodes = {
        'Registered':(65,180,290,265), 'FeePaid':(365,180,590,265),
        'HallTicketIssued':(665,180,910,265), 'ExamTaken':(985,180,1210,265),
        'Evaluated':(1285,180,1510,265), 'ResultPublished':(1585,180,1810,265),
        'Cancelled':(65,555,290,640), 'Absent':(665,555,910,640),
        'UnderReview':(1285,555,1510,640),
    }
    terminal={'ResultPublished','Cancelled','Absent'}
    for name,(x1,y1,x2,y2) in nodes.items():
        fill = '#e7edd8' if name in terminal else PAPER
        d.rounded_rectangle((x1,y1,x2,y2),radius=23,fill=fill,outline=FOREST,width=3)
        f=font(18 if len(name)>13 else 20,True)
        bb=d.textbbox((0,0),name,font=f)
        d.text((x1+(x2-x1-(bb[2]-bb[0]))/2,y1+30),name,font=f,fill=DEEP)
        if name in terminal:
            d.ellipse((x2-16,y2-16,x2+10,y2+10),fill=CORAL,outline=DEEP,width=2)
    def label(x,y,text):
        bb=d.textbbox((0,0),text,font=font(15,True)); tw=bb[2]-bb[0]
        d.rounded_rectangle((x-tw/2-7,y-2,x+tw/2+7,y+25),radius=6,fill='#f2f6ef')
        d.text((x-tw/2,y),text,font=font(15,True),fill=DEEP)
    main=[('Registered','FeePaid','pay_fee'),('FeePaid','HallTicketIssued','generate_hall_ticket'),('HallTicketIssued','ExamTaken','mark_attendance'),('ExamTaken','Evaluated','submit_evaluation'),('Evaluated','ResultPublished','publish_result')]
    for a,b,lbl in main:
        ax1,ay1,ax2,ay2=nodes[a]; bx1,by1,bx2,by2=nodes[b]
        draw_arrow(d,(ax2,222),(bx1,222),FOREST,4,13); label((ax2+bx1)/2,190,lbl)
    draw_arrow(d,(30,222),(65,222),FOREST,4,12); d.text((32,193),'q0',font=font(14,True),fill=DEEP)
    # branches and refund return route
    draw_arrow(d,(177,265),(177,555),CORAL,4,13); label(260,405,'cancel_registration')
    draw_arrow(d,(790,265),(790,555),CORAL,4,13); label(885,405,'mark_absent')
    draw_arrow(d,(1398,265),(1398,555),CORAL,4,13); label(1505,405,'flag_discrepancy')
    draw_arrow(d,(1290,575),(1210,300),FOREST,4,13); label(1190,435,'revert_evaluation')
    draw_arrow(d,(1505,575),(1580,300),FOREST,4,13); label(1630,435,'confirm_evaluation')
    # payment failure self-loop above Registered
    d.arc((112,95,245,205),180,350,fill=FOREST,width=4); draw_arrow(d,(231,138),(225,153),FOREST,4,12); label(180,108,'payment_failed')
    # refund path from FeePaid back to Registered, routed below the main row
    d.line([(477,265),(477,350),(290,350),(177,350),(177,265)],fill=FOREST,width=4)
    draw_arrow(d,(178,286),(178,265),FOREST,4,12); label(360,320,'request_refund')
    d.text((52,690),'Terminal states are shown with a coral marker. The web app rejects undefined moves instead of persisting an error state.',font=font(16),fill=MUTED)
    im.save(TMP/'fsm.png')

make_architecture()
make_state_diagram()

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
sec.top_margin = Inches(.72); sec.bottom_margin = Inches(.68)
sec.left_margin = Inches(.78); sec.right_margin = Inches(.78)
sec.header_distance = Inches(.32); sec.footer_distance = Inches(.34)

def set_font(style, name='Times New Roman', size=10.5, color='000000', bold=None):
    style.font.name=name; style.font.size=Pt(size); style.font.color.rgb=RGBColor.from_string(color)
    style._element.rPr.rFonts.set(qn('w:ascii'),name); style._element.rPr.rFonts.set(qn('w:hAnsi'),name)
    if bold is not None: style.font.bold=bold

normal=doc.styles['Normal']; set_font(normal,size=10.5)
normal.paragraph_format.space_after=Pt(6); normal.paragraph_format.line_spacing=1.13
normal.paragraph_format.widow_control=True
for key,size in [('Title',25),('Subtitle',13),('Heading 1',16),('Heading 2',12),('Heading 3',10.5)]:
    st=doc.styles[key]; set_font(st,size=size,color='000000',bold=(key!='Subtitle'))
    st.paragraph_format.space_before=Pt(8 if key!='Title' else 0); st.paragraph_format.space_after=Pt(6)
    st.paragraph_format.keep_with_next=True
doc.styles['Heading 1'].paragraph_format.page_break_before=False

header=sec.header.paragraphs[0]
header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
r=header.add_run('EXAMFLOW  |  MODEL OF COMPUTATION PROJECT REPORT'); r.font.name='Arial'; r.font.size=Pt(8); r.font.color.rgb=RGBColor.from_string(MUTED.replace('#',''))
footer=sec.footer.paragraphs[0]
footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=footer.add_run('University Examination Management System  |  '); r.font.name='Arial'; r.font.size=Pt(8); r.font.color.rgb=RGBColor.from_string(MUTED.replace('#',''))
fld=OxmlElement('w:fldSimple'); fld.set(qn('w:instr'),'PAGE'); footer._p.append(fld)

def shade(cell, fill):
    tcPr=cell._tc.get_or_add_tcPr(); shd=OxmlElement('w:shd'); shd.set(qn('w:fill'),fill.replace('#','')); tcPr.append(shd)

def set_cell_text(cell,text,bold=False,color='233B3A',size=9):
    cell.text=''; p=cell.paragraphs[0]; p.paragraph_format.space_after=Pt(1); p.paragraph_format.space_before=Pt(1)
    r=p.add_run(str(text)); r.bold=bold; r.font.name='Arial'; r.font.size=Pt(size); r.font.color.rgb=RGBColor.from_string(color)
    cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER

def table(headers, rows, widths=None, size=8.6):
    t=doc.add_table(rows=1,cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.style='Table Grid'
    t.autofit=False
    for i,h in enumerate(headers):
        set_cell_text(t.rows[0].cells[i],h,True,'1F4338',size); shade(t.rows[0].cells[i],MINT)
    trPr=t.rows[0]._tr.get_or_add_trPr(); rep=OxmlElement('w:tblHeader'); rep.set(qn('w:val'),'true'); trPr.append(rep)
    for ri,row in enumerate(rows):
        cells=t.add_row().cells
        for i,val in enumerate(row):
            set_cell_text(cells[i],val,False,'233B3A',size)
            if ri%2: shade(cells[i],'F6F7EF')
    if widths:
        for row in t.rows:
            for i,w in enumerate(widths): row.cells[i].width=Inches(w)
    doc.add_paragraph().paragraph_format.space_after=Pt(1)
    return t

def para(text, boldlead=None, italic=False):
    p=doc.add_paragraph()
    if boldlead and text.startswith(boldlead):
        r=p.add_run(boldlead); r.bold=True; p.add_run(text[len(boldlead):])
    else:
        r=p.add_run(text); r.italic=italic
    return p

def bullet(text):
    p=doc.add_paragraph(style='List Bullet'); p.paragraph_format.space_after=Pt(3); p.add_run(text); return p

def numbered(text):
    p=doc.add_paragraph(style='List Number'); p.paragraph_format.space_after=Pt(3); p.add_run(text); return p

def caption(text):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(2); p.paragraph_format.space_after=Pt(5)
    r=p.add_run(text); r.italic=True; r.font.name='Arial'; r.font.size=Pt(8.5); r.font.color.rgb=RGBColor.from_string(MUTED.replace('#',''))

def page(title, kicker=None):
    doc.add_page_break()
    if kicker:
        p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(2)
        r=p.add_run(kicker.upper()); r.bold=True; r.font.name='Arial'; r.font.size=Pt(8); r.font.color.rgb=RGBColor.from_string(FOREST.replace('#',''))
    doc.add_heading(title,level=1)

# 1 Cover
p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(72); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=p.add_run('MODEL OF COMPUTATION  |  DATABASE SYSTEMS'); r.bold=True; r.font.name='Arial'; r.font.size=Pt(10); r.font.color.rgb=RGBColor.from_string(FOREST.replace('#',''))
p=doc.add_paragraph(style='Title'); p.paragraph_format.space_before=Pt(64); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=p.add_run('ExamFlow University\nExamination Management System'); r.bold=True; r.font.name='Times New Roman'; r.font.size=Pt(26); r.font.color.rgb=RGBColor.from_string('000000')
p=doc.add_paragraph(style='Subtitle'); p.paragraph_format.space_before=Pt(13); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=p.add_run('Formal Model Database Design and Web Implementation'); r.font.name='Times New Roman'; r.font.size=Pt(14); r.font.color.rgb=RGBColor.from_string('000000')
doc.add_paragraph().paragraph_format.space_after=Pt(50)
table(['PROJECT DETAILS',''],[
    ('Submitted by','________________________________'),
    ('Programme / Department','________________________________'),
    ('Institution','________________________________'),
    ('Project guide','________________________________'),
    ('Academic session','2026–2027'),
],widths=[2.25,4.2],size=10)
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(44)
r=p.add_run('A project report on deterministic finite-state modeling and relational workflow management'); r.italic=True; r.font.size=Pt(10); r.font.color.rgb=RGBColor.from_string(MUTED.replace('#',''))

# 2 Abstract
page('Abstract and Keywords','Project summary')
abstract=("University exam administration coordinates course offerings, fees, attendance, evaluation, refunds, and result publication. When records are handled as independent flags, staff may apply actions in the wrong order or lose responsibility history. This project presents ExamFlow, a browser-based prototype that formalizes the lifecycle of each exam enrollment and connects it to relational persistence.\n\n"
"The computational model is a deterministic finite-state workflow with nine states, twelve event transitions, an initial state, and three terminal outcomes. The transition relation is partial: events undefined for the current state are rejected. A role permission check further restricts who may request each transition. Python and Oracle both represent the allowed edges and role-event rules.\n\n"
"Flask routes and templates provide Student, Faculty, Examination Cell, HOD, and Admin workspaces. Oracle stores accounts, courses, exams, per-exam enrollments, payments, tickets, marks, refunds, evaluation history, transition definitions, permissions, and audit records. Each workflow change locks the enrollment, validates the transition and role, updates the state, and writes an audit event in one transaction.\n\n"
"A local functional check covered sign-in and all 21 role-specific menu pages; each rendered successfully. This establishes page-level operation, not performance or production readiness. Payment is simulated, the gateway callback is not exposed, and deployment beyond a classroom demonstration requires further security hardening. The project’s value is the explicit connection between a formal model, durable records, and role-specific actions.")
wc=len(abstract.replace('\n',' ').split())
assert 200 <= wc <= 250, f'Abstract must be 200-250 words, found {wc}'
for chunk in abstract.split('\n\n'): para(chunk)
p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(12)
r=p.add_run('Keywords: '); r.bold=True
p.add_run('Theory of Computation, Deterministic Finite Automaton, Partial Transition System, University Examinations, Oracle Database, Role-Based Access Control, Audit Trail')

# 3 Contents
page('Contents','Report structure')
contents=[
('1 Introduction','4'),('1.1 Background','4'),('1.2 Problem Statement and Objectives','5'),('1.3 Scope of the Project','6'),
('2 Theoretical Background','7'),('2.1 Fundamentals of Finite-State Models','7'),('2.2 Formal Definition and Transition Relation','8–9'),('2.3 Properties of the Model','10'),('2.4 Relevance to Examination Workflows','11'),
('3 Proposed Model and Methodology','12'),('3.1 Problem Formulation','12'),('3.2 System Architecture and Workflow','13–14'),('3.3 Design of the Computational Model','15'),
('4 Implementation and Results','16'),('4.1 Tools and Technologies','16'),('4.2 Database Design','17'),('4.3 Routes and Role Workspaces','18'),('4.4 Transaction, Concurrency, and Audit','19'),('4.5 Browser Interface','20'),('4.6 Functional Verification Results','21'),
('5 Applications Discussion and Limitations','22'),('5.1 Practical Applications','22'),('5.2 Comparative Discussion','23'),('5.3 Limitations and Challenges','24'),
('6 Conclusion and Future Scope','25'),('6.1 Conclusion','25'),('6.2 Future Enhancements','26'),('References','27–28')]
for label,pnum in contents:
    p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(3)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(6.2))
    p.add_run(label); p.add_run('\t'+pnum)
para('The sequence follows the supplied Model of Computation project-report outline. Section numbers in the body distinguish the conceptual model from its implementation and evaluation.')

# 4 Introduction background
page('1 Introduction','Background')
para('A university examination process is a coordinated sequence of decisions made by different people. A student registers for an offering and pays a fee. The Examination Cell issues a hall ticket. An invigilator records attendance. Faculty evaluate the attempt. The Examination Cell reviews the evaluation and publishes a result. Separate routes are needed for absence, cancellation, failed payment, refund requests, and disputed marks. The work is not simply a collection of forms: each action changes what actions are valid next.')
para('A basic web application can store a status string, but a status alone does not explain the event that produced it, whether the event was allowed from the previous state, or which role performed it. If pages implement these rules independently, they can drift. One screen might allow a refund after a ticket has already been issued; another might still show the student as eligible for payment. The design problem is therefore to represent the process in a reusable model and preserve each transition together with the affected examination record.')
para('ExamFlow uses a finite-state model for the lifecycle of one student’s enrollment in one exam. The relational database stores the enrollment and its current state. The Flask application presents role-specific screens, validates requests, and calls the model before it changes that state. Oracle stores a second copy of the transition relation and event permissions. This arrangement gives the project a direct connection to both Theory of Computation and Database Management Systems: the automaton gives a precise order of operations, while the database makes those operations durable and auditable.')
para('The report is written as a project study rather than a claim that the prototype is a production examination platform. It explains the mathematical abstraction, maps it to application code and tables, and evaluates the working browser paths. It distinguishes implemented behavior from future integrations, including live payment processing and external gateway callbacks.')

# 5 problem/objectives
page('1.2 Problem Statement and Objectives','Introduction')
doc.add_heading('Problem statement',level=2)
para('The project investigates how an examination lifecycle with multiple stakeholders can be represented as a deterministic finite-state workflow and enforced consistently by a web application and a relational DBMS. The central question is: how can the system prevent an event from changing an enrollment unless that event is valid for its current state and is initiated by an authorized role?')
doc.add_heading('Objectives',level=2)
for t in [
    'Define the examination lifecycle as a finite set of states, events, an initial state, terminal states, and a deterministic transition relation.',
    'Represent the same transition edges and role-event permissions in Python and Oracle, then reject mismatches and undefined transitions.',
    'Use enrollment-level records so a student can hold different states in different exam offerings.',
    'Connect Student, Faculty, Examination Cell, HOD, and Admin actions to role-specific pages and route guards.',
    'Persist related changes, state transitions, and audit entries within an explicit transaction boundary.',
    'Evaluate the implementation through role-based page checks and identify limitations that require further engineering.'
]: bullet(t)
para('These objectives are scoped to a classroom prototype. They prioritize traceable behavior and a demonstrable relationship between formal rules, SQL data, and visible user actions. They do not claim complete institutional policy coverage, payment-provider certification, or operational readiness at university scale.')

# 6 scope
page('1.3 Scope of the Project','Introduction')
para('The application supports five role types. Students browse eligible exams, enroll, record a simulated fee payment, follow their exam states, request refunds for paid exams that have not started, and view tickets and published results. Faculty see exams assigned to them, record attendance, evaluate an attempt, flag a discrepancy, and make a reasoned correction to unpublished marks. The Examination Cell creates and closes exam offerings, selects faculty who may see a particular exam, issues tickets, reviews refund requests, confirms or returns evaluations, and publishes results.')
para('The HOD workspace extends the original lifecycle application into course administration. An HOD may add courses within an assigned department, update course name and credits, assign faculty by academic year and term, and end an active assignment while retaining its history. The HOD role is not permitted to trigger examination-state events. Admin manages accounts, department assignment, and audit review; it can cancel registrations where policy allows.')
para('The technical scope includes Flask routing and templates, session-based sign-in, CSRF checks for state-changing form requests, Oracle SQL schema and migrations, a Python DFA controller, and a local browser experience. The project exposes a JSON representation of the formal model at `GET /api/fsm`; most operational endpoints are HTML form routes rather than a JSON REST API. The UI is intended for a demonstration and the documentation explains how the routes can be explored with Postman.')
para('Out of scope are a real payment-provider integration, production identity management, university-wide timetable generation, exam paper delivery, appeals adjudication beyond the basic review path, mobile applications, and measured large-scale performance. These exclusions matter: the code demonstrates transaction recording and workflow control, not external financial settlement or regulatory compliance.')

# 7 fundamentals
page('2.1 Fundamentals of Finite-State Models','Theoretical background')
para('A finite automaton is a mathematical machine whose memory is represented by one of a finite number of states. It reads symbols from an alphabet and changes state according to a transition function. The machine does not need to remember the full history of the input; the current state summarizes the information needed to decide which next symbols are valid. This makes finite-state models useful for protocols, parsers, device controllers, and business workflows with a bounded set of lifecycle conditions [1, 2].')
para('In ExamFlow, the symbols are business events rather than characters. An event sequence is a word over the event alphabet Σ. For instance, the sequence `pay_fee, generate_hall_ticket, mark_attendance, submit_evaluation, publish_result` describes a successful path to a published outcome. The path is accepted when every event has a defined transition from the state reached so far and the final state is a designated terminal outcome. A request for `publish_result` while the record is still `Registered` is rejected because that pair has no transition.')
para('The distinction between state and event is useful. `FeePaid` is a condition of the enrollment; `pay_fee` is an event that can cause the machine to enter that condition. The next state is a result of applying the transition function, not a value chosen by the form. A page may display the available action, but the server must recompute validity from the stored state when the request arrives.')
para('A classical DFA is commonly defined with a total transition function δ: Q × Σ → Q. ExamFlow implements a partial transition function: some state-event pairs have no edge, and the controller rejects them. Mathematically, this partial machine can be completed with a non-accepting error sink state for missing pairs. The running application does not persist that sink; it treats an undefined move as a validation failure. This distinction preserves the formal meaning while accurately describing the implementation [1, 2].')

# 8 formal model
page('2.2 Formal Definition and Mathematical Representation','Theoretical background')
para('Let the workflow be M = (Q, Σ, δ, q₀, F), with the implementation’s partial δ defined only for permitted state-event pairs. The components are:')
table(['Symbol','Project definition'],[
    ('Q','{Registered, FeePaid, HallTicketIssued, ExamTaken, Evaluated, UnderReview, ResultPublished, Cancelled, Absent}'),
    ('Σ','{pay_fee, payment_failed, cancel_registration, generate_hall_ticket, request_refund, mark_attendance, mark_absent, submit_evaluation, flag_discrepancy, publish_result, revert_evaluation, confirm_evaluation}'),
    ('δ','The transition relation implemented as the DELTA mapping in fsm.py and stored in FSM_TRANSITIONS.'),
    ('q₀','Registered, the initial state of a new enrollment.'),
    ('F','{ResultPublished, Cancelled, Absent}, terminal states for the modeled lifecycle.')
],widths=[.8,5.7],size=8.1)
para('The transition is deterministic because each defined pair (q, e) maps to exactly one next state. Determinism does not mean every event is available from every state; it means the result is unique wherever the transition is defined. The implementation checks the stored enrollment value and computes δ(q,e). If there is no edge, it raises a validation error rather than guessing a next state.')
para('The automaton is applied independently to each row in EXAM_ENROLLMENTS. A student taking two exams therefore has two machine instances, each with its own current state. This is a product of identical lifecycle machines indexed by enrollment identity, not one global state for the whole student. The database key `(STUDENT_ID, EXAM_ID)` prevents duplicate enrollments for the same pair.')

# 9 transition table + figure
page('2.2 Transition Table','Theoretical background')
pic=doc.add_picture(str(TMP/'fsm.png'),width=Inches(6.75)); pic._inline.docPr.set('descr','Finite-state diagram of the nine examination enrollment states, twelve transitions, and three terminal outcomes.'); pic._inline.docPr.set('title','ExamFlow enrollment automaton'); caption('Figure 1. ExamFlow enrollment automaton. Coral-marked states are terminal outcomes.')
table(['Current state','Event','Next state'],[
    ('Registered','pay_fee','FeePaid'),('Registered','payment_failed','Registered'),('Registered','cancel_registration','Cancelled'),
    ('FeePaid','generate_hall_ticket','HallTicketIssued'),('FeePaid','request_refund','Registered'),
    ('HallTicketIssued','mark_attendance','ExamTaken'),('HallTicketIssued','mark_absent','Absent'),
    ('ExamTaken','submit_evaluation','Evaluated'),('Evaluated','flag_discrepancy','UnderReview'),
    ('Evaluated','publish_result','ResultPublished'),('UnderReview','revert_evaluation','ExamTaken'),
    ('UnderReview','confirm_evaluation','Evaluated')
],widths=[1.7,2.25,2.0],size=7.8)
para('The error sink is a mathematical completion only. A rejected request leaves the enrollment unchanged and returns a validation message to the caller.')

# 10 properties
page('2.3 Relevant Properties of the Model','Theoretical background')
doc.add_heading('Determinism and bounded memory',level=2)
para('The model has nine states, twelve event labels, and a finite transition relation. Given a current state and an event that has an edge, the next state is unambiguous. The machine needs only the current enrollment state to decide whether a lifecycle event can be applied. Details such as marks, payment transaction identifiers, refund reasons, and dates are stored in the database; they are not encoded into additional automaton states.')
doc.add_heading('Terminal outcomes and partiality',level=2)
para('ResultPublished, Cancelled, and Absent are marked terminal. The controller explicitly rejects outgoing events from any member of F. The partial transition relation also means that the workflow cannot skip prerequisites: there is no direct transition from Registered to HallTicketIssued or from ExamTaken to ResultPublished. A terminal outcome is not necessarily an institution-wide record lock in every table, but it is an exit from this modeled lifecycle.')
doc.add_heading('Transition traces',level=2)
para('A trace is a sequence of events that follows defined edges. The successful trace `pay_fee → generate_hall_ticket → mark_attendance → submit_evaluation → publish_result` ends in F. A review trace can include `flag_discrepancy → confirm_evaluation → publish_result`, while a returned evaluation can use `flag_discrepancy → revert_evaluation → submit_evaluation`. The second trace revisits ExamTaken, showing why the system records transitions rather than assuming a one-way linear path.')
para('For a complete DFA, add an error state ⊥ and send every undefined pair to ⊥, with δ(⊥,e)=⊥ for all e. If acceptance means reaching one of the three named terminal states, ⊥ is non-accepting. This conventional completion is useful in proofs; the application-level rejection behavior is more suitable for preserving valid database data [1, 2].')

# 11 relevance
page('2.4 Relevance to the Selected Application','Theoretical background')
para('A registration has a naturally bounded lifecycle. Policy decisions are based on its current stage, and only a finite set of events can move it forward or into an alternate outcome. A finite-state model is therefore a close fit: it exposes prerequisites, makes unreachable paths visible, and gives the application a finite transition table that can be inspected and checked against the database.')
para('The model also gives a shared vocabulary to the people using the system. Students see whether an exam is Registered, FeePaid, or awaiting a result. Faculty see the attendance and evaluation stages. The Examination Cell sees which enrollments are ready for a ticket, review, or publication. The state is not merely a label; it indicates which next steps may be meaningful. The role permission check adds an organizational rule to the state rule: being at the correct stage is necessary but not sufficient if the actor is not authorized.')
para('The distinction between a pending refund request and the enrollment state is intentional. A student’s request is a separate record in REFUND_REQUESTS. It does not immediately take the enrollment out of FeePaid. The Examination Cell reviews the request, and approval triggers the `request_refund` transition back to Registered while the fee payment is marked Refunded. A rejected request leaves the exam enrollment at FeePaid. This models the human review queue without inventing another exam lifecycle state.')
para('The approach is similar to protocol verification: the system validates not only the requested operation but also the context in which it is sent. The Myhill–Nerode perspective explains why states represent distinguishable futures of a language; here, the engineering choice is pragmatic rather than a proof of a minimal automaton. The project does not establish that nine states are mathematically minimal. It establishes a finite, deterministic model that matches the stated business rules [1, 3].')

# 12 methodology problem
page('3.1 Problem Formulation','Proposed model and methodology')
para('The input to the workflow controller is the tuple (enrollment, event, actor role, actor identity). The enrollment row provides the trusted current state. The event is supplied by a route or system callback. The actor role is associated with the authenticated session, while actor identity is used for ownership checks and audit attribution. The output is either a unique next state and committed set of related records, or a rejection with no partial change.')
table(['Condition','Required result'],[
    ('Enrollment does not exist or is not owned by actor','Reject request; do not update state.'),
    ('Event is not in the event alphabet','Reject as unknown event.'),
    ('No edge exists from current state for event','Reject undefined transition.'),
    ('Role is not permitted for event','Reject authorization failure.'),
    ('Python and Oracle edge values differ','Reject and surface consistency failure.'),
    ('All checks pass','Update workflow and related rows, append audit evidence, commit.')
],widths=[3.3,3.15],size=8.2)
para('The outcome is designed around a single persistence boundary. The route should not commit a state change and then fail before creating the required payment, ticket, refund decision, evaluation, or audit row. The connection context manager rolls back if an exception escapes before commit. This is the primary DBMS mechanism that keeps one event’s related writes together.')
para('Methodologically, the project proceeds from requirements to a state/event model, then maps that model to SQL tables and route guards. The transition mapping is defined in Python first and mirrored in Oracle. Browser forms are then built around valid actions. Finally, route-level checks verify that each role can load its menu pages against the live Oracle-backed application.')

# 13 architecture
page('3.2 System Architecture','Proposed model and methodology')
pic=doc.add_picture(str(TMP/'architecture.png'),width=Inches(6.75)); pic._inline.docPr.set('descr','Architecture diagram showing a browser, Flask routes, Python workflow validation, and Oracle Database, followed by the protected transition transaction steps.'); pic._inline.docPr.set('title','ExamFlow request architecture'); caption('Figure 2. A browser request reaches Oracle only after routing, role checks, and transition validation.')
para('The browser renders Jinja templates supplied by Flask. `app.py` creates the Flask application, registers the blueprints, injects the session-backed user context, checks CSRF tokens on POST requests, and maps `/` to a role-specific dashboard. A blueprint groups related route functions; for example, the student blueprint is registered under `/student`. Flask’s documented blueprint mechanism provides this modular organization [8].')
para('The route invokes business logic and uses `db.py` to acquire an Oracle connection from a python-oracledb pool. The state-machine controller validates the transition and compares the corresponding Oracle edge and permission. Domain records are stored in relational tables; the workflow definition is data in FSM_STATES, FSM_TRANSITIONS, and PERMISSIONS. Audit and correction history are persistent records rather than browser-only messages.')
para('The diagram illustrates an application-centered architecture. This project does not implement its transition logic as an Oracle PL/SQL package or trigger; Python coordinates the operation using SQL against Oracle. That is a deliberate boundary to describe accurately. Oracle remains central to durable state, relational constraints, row locking, and transaction commit or rollback.')

# 14 workflow / role matrix
page('3.2 Workflow and Role Responsibilities','Proposed model and methodology')
para('The role model separates the person who performs an action from the data record whose state changes. A role guard protects route families, while an event permission row is checked at the point of transition. Faculty are additionally restricted to exams assigned to their account; HODs are restricted to departments assigned to them. Exam Cell’s exam-faculty selection defines which faculty members can view and evaluate a particular exam.')
table(['Role','Typical actions','Workflow authority'],[
    ('Student','Enroll, pay, cancel own registration, request refund, view own records','pay_fee; cancel_registration'),
    ('Faculty','Attendance, absent status, evaluate, flag discrepancy, correct own unpublished mark','mark_attendance; mark_absent; submit_evaluation; flag_discrepancy'),
    ('Exam Cell','Create exams, issue tickets, review refunds, resolve evaluation review, publish results','generate_hall_ticket; request_refund; confirm_evaluation; revert_evaluation; publish_result'),
    ('HOD','Create department courses; assign and end teaching assignments','No FSM events; department-scoped management'),
    ('Admin','Accounts, department mapping, audit review, permitted cancellation','cancel_registration')
],widths=[1.0,3.0,2.45],size=7.6)
para('A refund illustrates separation of duties. The student submits a reason and creates a Pending request. Only Examination Cell can approve or reject it. Approval applies the state transition and marks successful payment records Refunded in the same transaction. The request record retains its reviewer, timestamp, and note. This makes the decision reviewable and follows the later project requirement that the refund decision belongs to Examination Cell.')
para('A role-specific sidebar is a navigation aid rather than the security boundary. A hidden link does not protect a URL. Every protected route still performs a server-side role check, and the transition function checks event permission against both Python policy and Oracle data [7].')

# 15 computational model design
page('3.3 Design of the Computational Model','Proposed model and methodology')
para('The implementation stores the state set Q and event set Σ as frozen sets in `fsm.py`. The transition function δ is represented by a Python dictionary whose keys are `(current_state, event)` pairs. The start state is the string Registered. The set F contains ResultPublished, Cancelled, and Absent. `validate_transition()` checks state membership, event membership, terminal status, role authorization, and finally edge existence. This order produces understandable errors while rejecting the request before persistence.')
para('The dictionary provides direct lookup by state-event pair, so the edge lookup is expected O(1) on average. Listing all available events scans the finite transition map, O(|δ|); this operation is small for a twelve-edge prototype. Database access, network latency, and transaction locking dominate end-to-end response time in realistic use, so dictionary complexity alone is not a performance result.')
para('Authorization is a second relation P ⊆ Roles × Σ. An event is executable only if the state machine defines δ(q,e) and the role is in P for that event. A compact decision rule is:')
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=p.add_run('accept(q, e, r) iff (q,e) ∈ dom(δ) and (r,e) ∈ P'); r.bold=True; r.font.name='Consolas'; r.font.size=Pt(10)
para('The database applies the same relation as persisted reference data. Python computes the expected next state; Oracle supplies the configured destination. A missing Oracle row or disagreement between the two values is an error, not a silent fallback. This is a cross-representation consistency check. It does not constitute a formal proof that no future code path can bypass the controller; route reviews and negative tests remain necessary.')
para('For a more complete formal verification, the system could define a labeled transition system with state predicates for payment, ticket, marks, and refund status, then check invariants such as “a result cannot be published before evaluation is confirmed.” The current model keeps the lifecycle state compact and stores those details as relational facts.')

# 16 tools
page('4.1 Tools and Technologies Used','Implementation and results')
table(['Layer','Technology','Use in this project'],[
    ('Web application','Python 3; Flask','Application factory, request handling, route dispatch, sessions, and rendering.'),
    ('Route organization','Flask Blueprints','Separate Student, Faculty, Exam Cell, HOD, and Admin route groups.'),
    ('Presentation','HTML, Jinja templates, CSS, local Tailwind runtime','Role sidebars, forms, tables, responsive page layout, and green visual system.'),
    ('Database','Oracle Database at XEPDB1','Relational storage, SQL constraints, row locking, identity keys, and transactions.'),
    ('Driver','python-oracledb','Connection pool, cursor execution, bind variables, commit, rollback.'),
    ('Formal model','Python finite-state controller + Oracle tables','Transition validation and stored state/event and role/event relations.'),
    ('Browser/API inspection','Browser and Postman-compatible form routes','End-user verification and manual HTTP exploration.')
],widths=[1.2,2.0,3.25],size=8.0)
para('The driver follows Python’s database API conventions and supports connection pools. In this repository, `db.py` creates a pool lazily and returns a connection through a context manager. Pooling avoids building a new database connection for every page request; python-oracledb documentation recommends pools where applications repeatedly connect and disconnect [10, 11].')
para('The visible operational pages are server-rendered. Most actions submit HTML forms using POST; they are not a JSON REST interface. The public `GET /api/fsm` endpoint returns the automaton model as JSON and is a convenient Postman demonstration. Flask’s routing and blueprint documentation describes the URL-to-view mapping used by this architecture [8, 9].')
para('The local browser runs on a development server. The green and cream interface uses locally served styling for its utility classes, avoiding a runtime dependency on the Tailwind CDN. A production deployment would still need a production WSGI server, secure configuration, TLS, and deployment-specific monitoring.')

# 17 database schema
page('4.2 Database Design','Implementation and results')
para('The schema separates people, academic offerings, workflow instances, and evidence. USERS stores identity and role. STUDENTS and FACULTY connect a person to institution-specific records. COURSES describes the academic catalog. EXAMS represents a dated, fee-bearing offering for a course. EXAM_ENROLLMENTS identifies the student-exam pair and its current lifecycle state. The unique constraint on `(STUDENT_ID, EXAM_ID)` prevents duplicate registration for one offering.')
table(['Table group','Key responsibility','Integrity mechanisms'],[
    ('USERS / STUDENTS / FACULTY','Accounts and role-specific identities','Primary keys; user and course foreign keys.'),
    ('COURSES / HOD_DEPARTMENTS / COURSE_FACULTY','Department catalog and term assignments','Foreign keys; assignment role checks; function-based unique indexes.'),
    ('EXAMS / EXAM_FACULTY','Exam offering and faculty visibility','Unique exam code; course and faculty foreign keys; status check.'),
    ('EXAM_ENROLLMENTS','Per-exam workflow instance','Unique student-exam pair; allowed-state CHECK constraint.'),
    ('FEE_PAYMENTS / HALL_TICKETS / MARKS','Payment, logistics, and evaluation data','Enrollment references; amount/score validation in application and selected DB constraints.'),
    ('REFUND_REQUESTS / EVALUATION_HISTORY','Review decisions and mark corrections','Reviewer/actor references; status checks; required correction reason.'),
    ('FSM_STATES / FSM_TRANSITIONS / PERMISSIONS','Stored formal state model and event policy','Primary/foreign keys; unique source-state/event edge.'),
    ('AUDIT_LOG','Actor, event, old/new state, timestamp','Identity key; foreign keys to actor and enrollment where available.')
],widths=[1.65,2.45,2.35],size=7.3)
para('The schema uses normalization principles to keep entities and relationships identifiable; the relational model was introduced as a way to separate logical data descriptions from storage representation [4]. The migrations also retain the original STUDENTS.EXAM_STATUS field for compatibility. The application’s newer lifecycle is enrollment-centered, so maintaining both fields creates a synchronization risk if older routes update only one. The report treats EXAM_ENROLLMENTS.EXAM_STATUS as the workflow value used by the exam-feature routes.')
para('Foreign keys and check constraints push several integrity rules into Oracle, reducing dependence on one form. Oracle recommends database constraints for rules that can be expressed declaratively [12]. Not every business rule is a check constraint: for example, verifying faculty assignment and event permissions requires application queries and transaction logic.')

# 18 routes
page('4.3 Routes and Role Workspaces','Implementation and results')
para("A route is a mapping from an HTTP method and URL pattern to a Python view function. A blueprint adds a namespace and may be registered under a shared prefix. For example, a view decorated with `@student_bp.route('/pay_fee', methods=['POST'])` becomes `POST /student/pay_fee` when the blueprint is mounted with `/student`. A request first passes through shared application checks, then the matching route guard, then the view and database work.")
table(['Workspace','Representative GET pages','Representative state-changing POST'],[
    ('Student','/student/dashboard, /exams, /my-exams, /refunds, /hall-tickets, /results','enroll, pay_fee, cancel, request refund'),
    ('Faculty','/faculty/dashboard, /exams, /evaluations','attendance, absent, evaluate, flag, correction'),
    ('Exam Cell','/examcell/dashboard, /exams, /refunds, /hall-tickets, /evaluations, /reports','create/close exam, review refund, issue ticket, review/publish'),
    ('HOD','/hod/dashboard, /courses, /faculty','create/update course, assign/end faculty assignment'),
    ('Admin','/admin/dashboard, /users, /audit','create account, permitted cancellation')
],widths=[1.15,3.05,2.25],size=7.5)
para('Authentication populates a signed Flask session with user identity and role. The `*_required` decorators reject requests from the wrong role before the view performs its database queries. Object-level checks add another layer: students can act only on their own enrollment; faculty can work only on exams assigned to them; HOD course operations are limited to assigned departments. The sidebar is built from role-specific URL endpoints in `templates/base.html`.')
para('All POST requests pass a CSRF token check in `app.py`. The token is kept in session and compared using a constant-time comparison before route execution. The login page includes its token directly; authenticated forms receive it through the base template script. OWASP describes the synchronizer-token pattern as a common defense for state-changing requests [14].')
para('For Postman, the client must retain the session cookie, retrieve the current CSRF token from page HTML, and send the relevant fields as `application/x-www-form-urlencoded`. This is a useful route exercise, but it does not turn the HTML application into a fully specified JSON API.')

# 19 transaction/concurrency
page('4.4 Transaction Atomicity Concurrency and Audit','Implementation and results')
para('A transition begins by locking the relevant enrollment row with `SELECT … FOR UPDATE`. The controller reads the current state from this locked row rather than trusting a value sent by the browser or a stale earlier query. It then validates δ and the role policy, reads the Oracle transition destination, compares the two implementations, updates the enrollment, and inserts an audit row. The caller commits after related domain writes succeed; an exception causes rollback through `get_db()`.')
para('This sequencing addresses a race. If two staff actions target the same enrollment concurrently, the row lock serializes the critical transition. The later request sees the newly committed state and must validate from that value. Oracle documents row-level locking for `SELECT FOR UPDATE` and describes how locking prevents concurrent modifications of the same row [13]. This does not eliminate every race in the entire application; all changes to the modeled lifecycle should pass through the same transaction discipline.')
para('Atomicity is visible in workflow examples. A successful payment action must not leave a FeePaid enrollment without its payment row. An approved refund must not move the enrollment back to Registered while leaving the payment marked Success. Evaluation submission must not change state without storing marks. The application groups these related writes before commit. Audit entries record event, actor, enrollment, and old/new states so a reviewer can reconstruct the lifecycle.')
para('The database context manager commits on normal exit and rolls back on an exception; routes that explicitly commit do so before exiting the context. This convention needs careful maintenance: a swallowed exception or an early commit can weaken the all-or-nothing guarantee. Future refactoring could centralize transition commands into a service object or stored procedure and ensure that every caller uses a single transaction boundary [6, 11].')

# 20 interface
page('4.5 Browser Interface and User Journey','Implementation and results')
para('The browser interface is organized around the task a role performs, rather than around the internal class or table structure. The Student sidebar groups Overview, Browse exams, My exams, Refunds, Hall tickets, and Results. The Examination Cell workspace groups the exam catalog, refund queue, hall-ticket issuance, evaluation review, and reports. Faculty see assigned exam work and evaluation history. HODs see courses and faculty assignments. Admins see account and audit management.')
para('The verified Student dashboard presents a welcome panel with a direct exam-catalog action, compact registration/payment/result counts, and a recent-exam table. The recent table shows the exam name and code, course, date, and lifecycle state. It demonstrates a useful separation between a summary view and a detailed list. The companion figures document the state machine and request architecture, while the functional-verification table records the role-specific pages checked in the running application.')
para('A typical user journey is: sign in, follow the role sidebar to a work queue, open the record, submit a form for an allowed action, receive a success or validation message, and return to a refreshed screen whose state comes from Oracle. Links use the forest-green palette and a visible hover shadow; keyboard focus is marked so a user navigating with Tab can see the active control.')
para('Postman complements the browser for route learning. The browser provides the rendered workflow and session state; Postman makes the HTTP method, URL, form body, cookie, CSRF token, response status, and redirect visible. Because most action routes are designed as form submissions, tests should preserve the session cookie and use the correct form encoding. The JSON automaton endpoint is the simplest endpoint for inspecting the model without changing records.')

# 21 results/tests
page('4.6 Experimental Results and Functional Verification','Implementation and results')
para('The evaluation reported here is a functional smoke check against the local Flask application and Oracle-backed demo schema. Each role signed in through the browser-style form flow, then requested the pages exposed by that role’s sidebar. The check recorded HTTP 200 responses and confirmed that the response contained the authenticated application shell. It verifies route rendering for the listed destinations; it is not a concurrency stress test, security audit, or performance benchmark.')
table(['Role','Pages checked','Count','Observed result'],[
    ('Student','Dashboard, exams, my exams, refunds, hall tickets, results','6','All returned HTTP 200.'),
    ('Faculty','Dashboard, assigned exams, evaluations','3','All returned HTTP 200.'),
    ('Exam Cell','Dashboard, exam catalog, refunds, tickets, evaluations, reports','6','All returned HTTP 200.'),
    ('HOD','Dashboard, courses, faculty assignments','3','All returned HTTP 200.'),
    ('Admin','Dashboard, users, audit','3','All returned HTTP 200.'),
    ('Total','Five role workspaces','21','All tested pages rendered the role sidebar.')
],widths=[1.0,2.65,.55,2.25],size=7.8)
para('Separate read-only browser inspection of the Student dashboard confirmed that the active page contained the expected role menu, overview link, exam-catalog call to action, summary cards, and recent-exam table. The application’s form guards and database transaction code were reviewed to establish how POST actions are protected; the verification run did not execute a live payment, refund decision, ticket issuance, or grade publication.')
para('No throughput, latency, availability, or error-rate figures are reported. A reproducible quantitative evaluation would define a test dataset, specify hardware and Oracle configuration, run repeatable workloads, and record response-time percentiles and transaction outcomes. Functional page success supports the claim that all five role areas render; it does not prove performance under institutional-scale load.')

# 22 practical applications
page('5.1 Practical Applications','Applications discussion and limitations')
para('The model can support a university’s examination administration by making prerequisites and hand-offs explicit. A student can see an enrollment move from registration to payment and ticket issuance. Faculty receive assigned work rather than a global queue. Examination Cell staff can focus on requests that require central review. The HOD can manage the course catalog and term-based teaching assignments before an exam is scheduled. Admin can manage accounts and inspect the event trail.')
para('The same state-machine pattern can be adapted to scholarship applications, library lending, laboratory equipment reservations, document approvals, or internship placement. Such adaptations are appropriate when a process has a finite set of stages, named events, and role-controlled decisions. The data model would need to change to represent each domain’s entities and exception paths; reusing the code without re-evaluating the event alphabet would be unsafe.')
para('For teaching, the project provides a concrete bridge from a mathematical transition diagram to a database-backed web feature. Students can compare the state table in `fsm.py` with FSM_TRANSITIONS in Oracle, call `/api/fsm`, inspect role permissions, and trace a request from a form to a transaction. SQL*Plus can be used to inspect the relational tables and constraints, while Postman can display the HTTP request and response mechanics.')
para('The design is most useful as a transparent workflow prototype. It gives each transition a named event, preserves records for refund requests and evaluation changes, and shows which user groups own which tasks. These are structural design benefits. The project has not yet measured whether the interface reduces processing time or errors compared with a manual institution-wide process.')

# 23 discussion
page('5.2 Discussion and Design Comparison','Applications discussion and limitations')
table(['Approach','Strength','Weakness relative to ExamFlow'],[
    ('Spreadsheet status column','Low setup effort and familiar editing.','Rules are implicit; concurrent changes, role separation, and audit consistency are difficult to enforce.'),
    ('Independent pages with ad hoc status updates','Simple to build individual features.','Transition logic can diverge across routes; event history may be missing.'),
    ('Single finite-state workflow + DBMS','Explicit transition relation, role checks, row-level persistence, audit records.','Requires careful synchronization of formal rules, database data, and application routes.')
],widths=[1.75,2.2,2.5],size=7.8)
para('The main design difference is that the state transition is a domain operation rather than a direct form assignment. A route requests an event; it does not trust the browser to set an arbitrary destination status. The controller derives the next state from the current state and event. The database then commits that transition together with its audit and related records. This makes the allowed behavior easier to review than repeated `UPDATE ... SET status = ...` statements embedded in several view functions.')
para('The integration also makes the Theory of Computation contribution substantive. The automaton is not only a static diagram: its transition map participates in request validation, the API representation, and a comparison with the Oracle relation. At the same time, the implementation is an application of finite-state ideas rather than a proof assistant. There is no model checker or exhaustive proof over all possible database values.')
para('The DBMS contribution is likewise concrete but bounded. Oracle enforces keys, referential integrity, state/status checks, uniqueness, and transaction behavior. Python-oracledb handles pooled connections and transaction calls. The project does not implement a PL/SQL state-machine package, DB triggers for every transition, or a full recovery/performance study. Those distinctions make the evaluation more credible and identify useful next steps.')

# 24 limitations
page('5.3 Limitations and Challenges','Applications discussion and limitations')
para('Payment processing is simulated. The Student payment form records a successful payment and a transaction identifier generated by the application. The `payment_failed` event is defined for a SYSTEM actor in the automaton, but the current browser application does not expose a payment-gateway callback endpoint. A real integration would require provider-side signature verification, idempotency keys, duplicate-callback handling, reconciliation, and a clear refund settlement state.')
para('Security is appropriate to a local coursework prototype, not a public production service. Flask’s default session is a signed client-side cookie; its integrity depends on a secret key, and the repository has a development fallback secret. Session data should be kept non-sensitive and deployments must use a strong externally configured secret [9]. The code upgrades legacy SHA-256 demo password hashes when accounts sign in, but SHA-256 alone is too fast for password storage; OWASP recommends adaptive password-hashing algorithms such as Argon2id, scrypt, bcrypt, or PBKDF2 [15]. New password hashes use Werkzeug’s password hashing utilities. A production rollout should migrate all legacy records and enforce modern password policy.')
para('The application has CSRF tokens and role checks, but it has no documented rate-limiting policy, MFA, production TLS setup, centralized monitoring, backup/restore runbook, or independent security review. The local development server is not a production WSGI deployment. Database credentials must be supplied securely outside source files, and the DB account should receive only the privileges the application needs.')
para('Some lifecycle data remains for compatibility with the original schema, including STUDENTS.EXAM_STATUS alongside per-exam EXAM_ENROLLMENTS.EXAM_STATUS. Duplicated representations need migration discipline and clear ownership. The UI is English-only and the project has no accessibility conformance audit. Finally, functional smoke checks cover page rendering, not every business rule, race, malformed input, or failure mode.')

# 25 conclusion
page('6.1 Conclusion','Conclusion and future scope')
para('ExamFlow models university exam administration as a finite, deterministic set of lifecycle transitions and connects that model to a relational workflow application. Nine states and twelve event edges describe registration, payment, ticketing, attendance, evaluation, review, result publication, cancellation, and absence. The implementation rejects missing state-event pairs, treats terminal states as exits, and checks actor roles before allowing sensitive transitions.')
para('The project’s central contribution is the mapping across layers. Python represents the formal transition relation. Oracle stores the transition and permission relations alongside enrollment records. Flask routes expose the actions through role-specific workspaces. Row locking and transaction boundaries protect the current state from stale or conflicting updates, while audit and history tables retain a record of decisions. The HOD course catalog and teaching assignments add realistic academic setup work around the examination lifecycle.')
para('The local verification checked all 21 menu pages across five roles and confirmed that each loaded successfully. This supports a functional demonstration claim. It does not establish that every business action has been exhaustively tested, that a real payment provider is connected, or that the application is ready for deployment to a university. The model is a strong foundation for classroom demonstration because a reviewer can follow a state edge from theory to Python, Oracle, and browser behavior.')

# 26 future
page('6.2 Future Enhancements','Conclusion and future scope')
for lead,text in [
    ('Complete the payment boundary. ','Add a verified gateway callback, idempotent event processing, failure-state persistence, reconciliation, and a refund settlement record.'),
    ('Move invariants closer to the database. ','Evaluate a PL/SQL package or carefully designed stored procedure for the transition command, and prevent direct application updates that bypass it.'),
    ('Add automated transition tests. ','Generate tests from the transition table for valid edges, undefined pairs, terminal-state rejection, role denials, duplicate callbacks, rollback, and concurrent updates.'),
    ('Strengthen account security. ','Remove legacy fast hashes, use a modern adaptive password hash, rotate the development secret, add rate limits and MFA, and configure secure cookies and TLS.'),
    ('Improve the API boundary. ','Provide documented JSON endpoints, stable response schemas, OpenAPI descriptions, and a Postman collection with login and CSRF setup.'),
    ('Measure realistic behavior. ','Benchmark page and transaction latency under defined workloads; report throughput, percentiles, lock waits, and database resource use.'),
    ('Improve accessibility and deployment. ','Audit keyboard flow and screen-reader labels, add localization, backups and restore tests, monitoring, and production WSGI deployment guidance.')
]:
    p=doc.add_paragraph(style='List Bullet'); p.paragraph_format.space_after=Pt(6)
    r=p.add_run(lead); r.bold=True; p.add_run(text)
para('These enhancements follow from the prototype’s observed boundaries. They preserve the finite-state model while making its external integrations, persistence guarantees, security posture, and operational evidence more complete.')

# 27-28 references
page('References','Selected theory and database sources')
refs1=[
    '[1] M. Sipser, Introduction to the Theory of Computation, 3rd ed. Boston, MA: Cengage Learning, 2013. Publisher: https://www.cengage.com/c/student/9781133187790/',
    '[2] J. E. Hopcroft, R. Motwani, and J. D. Ullman, Introduction to Automata Theory, Languages, and Computation, 3rd ed. Boston, MA: Pearson, 2006. https://www.pearson.com/en-us/subject-catalog/p/introduction-to-automata-theory-languages-and-computation/P200000003517/9780321455369',
    '[3] A. Nerode, “Linear automaton transformations,” Proceedings of the American Mathematical Society, vol. 9, no. 4, pp. 541–544, 1958. doi:10.2307/2271612.',
    '[4] E. F. Codd, “A relational model of data for large shared data banks,” Communications of the ACM, vol. 13, no. 6, pp. 377–387, 1970. doi:10.1145/362384.362685.',
    '[5] P. P. Chen, “The entity-relationship model—Toward a unified view of data,” ACM Transactions on Database Systems, vol. 1, no. 1, pp. 9–36, 1976. doi:10.1145/320434.320440.',
    '[6] T. Härder and A. Reuter, “Principles of transaction-oriented database recovery,” ACM Computing Surveys, vol. 15, no. 4, pp. 287–317, 1983. doi:10.1145/289.291.',
    '[7] R. Sandhu, D. Ferraiolo, and D. R. Kuhn, “The NIST model for role-based access control: Towards a unified standard,” in Proceedings of the Fifth ACM Workshop on Role-Based Access Control, 2000. doi:10.1145/344287.344301.',
    '[8] Pallets Projects, “Modular Applications with Blueprints,” Flask 3.1 Documentation. https://flask.palletsprojects.com/en/stable/blueprints/',
    '[9] Pallets Projects, “Quickstart: Sessions and request handling,” Flask 3.1 Documentation. https://flask.palletsprojects.com/en/stable/quickstart/',
]
for x in refs1: para(x)

page('References continued','Implementation and security sources')
refs2=[
    '[10] Oracle, “Connecting to Oracle Database,” python-oracledb User Guide. https://python-oracledb.readthedocs.io/en/latest/user_guide/connection_handling.html',
    '[11] Oracle, “Managing Transactions,” python-oracledb User Guide. https://python-oracledb.readthedocs.io/en/stable/user_guide/txn_management.html',
    '[12] Oracle, “Maintaining Data Integrity in Database Applications,” Oracle Database Documentation. https://docs.oracle.com/en/database/oracle/oracle-database/18/adfns/data-integrity.html',
    '[13] Oracle, “Data Concurrency and Consistency,” Oracle Database Concepts. https://docs.oracle.com/en/database/oracle/oracle-database/18/cncpt/data-concurrency-and-consistency.html',
    '[14] OWASP Foundation, “Cross-Site Request Forgery Prevention Cheat Sheet.” https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html',
    '[15] OWASP Foundation, “Password Storage Cheat Sheet.” https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html',
    '[16] M.-A. Lemburg, “PEP 249 – Python Database API Specification v2.0,” Python Enhancement Proposals, 1999. https://peps.python.org/pep-0249/',
    '[17] ExamFlow project source, MOC_PROJECT.sql, schema_patch.sql, schema_exam_features.sql, schema_hod_courses.sql, fsm.py, app.py, db.py, routes/, and templates/. Local project files, accessed 22 October 2026.',
]
for x in refs2: para(x)
para('Web documentation was consulted for definitions and implementation guidance. Project-specific behavior is described from the application source and local verification; no external source is used to claim measured performance.')

# Set metadata, enforce the first page style and save.
doc.core_properties.title='ExamFlow University Examination Management System'
doc.core_properties.subject='Formal state-machine model, Oracle database design, and web implementation'
doc.core_properties.author=''
doc.core_properties.keywords='Theory of Computation; DFA; Oracle; examination workflow; DBMS'
doc.save(OUT)
print(f'created={OUT}')
print(f'abstract_word_count={wc}')
print(f'planned_pages=28')

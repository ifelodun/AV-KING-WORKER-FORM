from flask import Flask, render_template, request, redirect, url_for
from flask import flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_login import UserMixin
from flask_login import login_user
from flask_login import logout_user
from flask_login import login_required
from flask_login import current_user

from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import os
import random


# ====================================
# CONFIG
# ====================================

import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail

app = Flask(__name__)

app.config["SECRET_KEY"] = "AVKING_SECRET_KEY"

import os

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL"
)

app.config[
    "SQLALCHEMY_TRACK_MODIFICATIONS"
] = False

app.config["UPLOAD_FOLDER"] = "uploads"

# Mail Settings
app.config["MAIL_SERVER"] = "smtp.gmail.com"

app.config["MAIL_PORT"] = 587

app.config["MAIL_USE_TLS"] = True

app.config["MAIL_USERNAME"] = os.getenv(
    "MAIL_USERNAME"
)

app.config["MAIL_PASSWORD"] = os.getenv(
    "MAIL_PASSWORD"
)

# Initialize Extensions
db = SQLAlchemy(app)

mail = Mail(app)

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"

# ====================================
# NIGERIA TIME
# ====================================

def nigeria_time():
    return datetime.now(
        ZoneInfo("Africa/Lagos")
    )

# ====================================
# EMPLOYEE ID GENERATOR
# ====================================

def generate_employee_id():

    last_user = User.query.order_by(
        User.id.desc()
    ).first()

    if not last_user:
        return "AVKV001"

    try:
        number = int(
            last_user.employee_id.replace(
                "AVKV",
                ""
            )
        ) + 1

    except:
        number = 1

    return f"AVKV{str(number).zfill(3)}"

class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    employee_id = db.Column(
        db.String(20),
        unique=True
    )

    fullname = db.Column(
        db.String(200),
        nullable=False
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        default="worker"
    )

    department = db.Column(
        db.String(100)
    )

    profile_photo = db.Column(
        db.String(255)
    )

    phone = db.Column(
        db.String(20)
    )

    address = db.Column(
        db.Text
    )

    gender = db.Column(
        db.String(20)
    )

    theme = db.Column(
        db.String(20),
        default="light"
    )

    status = db.Column(
        db.String(20),
        default="active"
    )

    failed_attempts = db.Column(
        db.Integer,
        default=0
    )

    locked_until = db.Column(
        db.DateTime
    )

    created_at = db.Column(
        db.DateTime,
        default=nigeria_time
    )

    def __repr__(self):
        return f"<User {self.username}>"

class CompanySettings(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    company_name = db.Column(
        db.String(255)
    )

    address = db.Column(
        db.Text
    )

    phone = db.Column(
        db.String(100)
    )

    email = db.Column(
        db.String(150)
    )

    logo = db.Column(
        db.String(255)
  )

class AuditLog(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100)
    )

    action = db.Column(
        db.String(255)
    )

    created_at = db.Column(
        db.DateTime,
        default=nigeria_time
    )

class PasswordReset(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    email = db.Column(
        db.String(150)
    )

    otp = db.Column(
        db.String(6)
    )

    expires_at = db.Column(
        db.DateTime
    )

@login_manager.user_loader
def load_user(user_id):

    return User.query.get(
        int(user_id)
    )

@app.before_request
def create_super_admin():

    admin = User.query.filter_by(
        role="super_admin"
    ).first()

    if not admin:

        admin = User(

            employee_id="AVKV000",

            fullname="Super Admin",

            username="superadmin",

            email="admin@avking.com",

            password=generate_password_hash(
                "Admin@123"
            ),

            role="super_admin"
        )

        db.session.add(admin)

        db.session.commit()
      
def log_action(username, action):

    log = AuditLog(
        username=username,
        action=action
    )

    db.session.add(log)
    db.session.commit()

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(
            username=username
        ).first()

        if not user:

            flash("Invalid username or password")
            return redirect("/login")

        # Account Lock Check

        if user.locked_until:

            if user.locked_until > nigeria_time():

                flash(
                    "Account temporarily locked."
                )

                return redirect("/login")

        # Password Check

        if check_password_hash(
            user.password,
            password
        ):

            user.failed_attempts = 0

            db.session.commit()

            login_user(user)

            log_action(
                user.username,
                "User Logged In"
            )

            return redirect("/dashboard")

        else:

            user.failed_attempts += 1

            if user.failed_attempts >= 5:

                user.locked_until = (
                    nigeria_time()
                    + timedelta(minutes=15)
                )

            db.session.commit()

            flash(
                "Invalid username or password"
            )

            return redirect("/login")

    return render_template(
        "login.html"
    )


@app.route("/logout")
@login_required
def logout():

    log_action(
        current_user.username,
        "User Logged Out"
    )

    logout_user()

    return redirect("/login")

@app.route(
    "/forgot-password",
    methods=["GET", "POST"]
)
def forgot_password():

    if request.method == "POST":

        email = request.form["email"]

        user = User.query.filter_by(
            email=email
        ).first()

        if not user:

            flash(
                "Email not found"
            )

            return redirect(
                "/forgot-password"
            )

        otp = str(
            random.randint(
                100000,
                999999
            )
        )

        expires = (
            nigeria_time()
            + timedelta(minutes=10)
        )

        reset = PasswordReset(

            email=email,

            otp=otp,

            expires_at=expires
        )

        db.session.add(reset)
        db.session.commit()

        print(
            f"OTP for {email}: {otp}"
        )

        flash(
            "OTP sent successfully"
        )

        return redirect(
            f"/reset-password/{email}"
        )

    return render_template(
        "forgot_password.html"
    )

@app.route(
    "/reset-password/<email>",
    methods=["GET", "POST"]
)
def reset_password(email):

    if request.method == "POST":

        otp = request.form["otp"]

        password = request.form["password"]

        confirm = request.form[
            "confirm_password"
        ]

        if password != confirm:

            flash(
                "Passwords do not match"
            )

            return redirect(
                request.url
            )

        reset = PasswordReset.query.filter_by(
            email=email,
            otp=otp
        ).first()

        if not reset:

            flash(
                "Invalid OTP"
            )

            return redirect(
                request.url
            )

        if reset.expires_at < nigeria_time():

            flash(
                "OTP Expired"
            )

            return redirect(
                request.url
            )

        user = User.query.filter_by(
            email=email
        ).first()

        user.password = generate_password_hash(
            password
        )

        db.session.commit()

        flash(
            "Password Updated Successfully"
        )

        return redirect("/login")

    return render_template(
        "reset_password.html"
    )

@app.route("/dashboard")
@login_required
def dashboard():

    total_users = User.query.count()

    total_admins = User.query.filter_by(
        role="admin"
    ).count()

    total_workers = User.query.filter_by(
        role="worker"
    ).count()

    total_logs = AuditLog.query.count()

    return render_template(

        "dashboard.html",

        total_users=total_users,

        total_admins=total_admins,

        total_workers=total_workers,

        total_logs=total_logs
    )


def admin_required():

    if current_user.role not in [
        "admin",
        "super_admin"
    ]:

        flash(
            "Access Denied"
        )

        return False

    return True

@app.route(
    "/create-admin",
    methods=["GET", "POST"]
)
@login_required
def create_admin():

    if current_user.role != "super_admin":

        flash("Access Denied")

        return redirect("/dashboard")

    if request.method == "POST":

        fullname = request.form[
            "fullname"
        ]

        username = request.form[
            "username"
        ]

        email = request.form[
            "email"
        ]

        password = request.form[
            "password"
        ]

        admin = User(

            employee_id=
            generate_employee_id(),

            fullname=fullname,

            username=username,

            email=email,

            password=
            generate_password_hash(
                password
            ),

            role="admin"
        )

        db.session.add(admin)

        db.session.commit()

        log_action(
            current_user.username,
            f"Created Admin {username}"
        )

        flash(
            "Admin Created Successfully"
        )

        return redirect(
            "/dashboard"
        )

    return render_template(
        "create_admin.html"
    )

@app.route("/dashboard_home")
def dashboard_home():

    settings = CompanySettings.query.first()

    return render_template(
        "home.html",
        settings=settings
    )

with app.app_context():

    db.create_all()

    settings = CompanySettings.query.first()

    if not settings:

        settings = CompanySettings(

            company_name=
            "AV KING VET DRUG VENTURE",

            phone=
            "08087981439",

            address=
            "NO 11 HALLELUJAH SHOPPING COMPLEX OPPOSITE POULTRY ASSOCIATION IYANA AJIA EGBEDA IBADAN"
        )

        db.session.add(settings)

        db.session.commit()

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp",
    "svg"
}

def allowed_file(filename):

    return "." in filename and \
    filename.rsplit(
        ".",
        1
    )[1].lower() in ALLOWED_EXTENSIONS

@app.route(
    "/admin/settings",
    methods=["GET", "POST"]
)
@login_required
def admin_settings():

    if not admin_required():
        return redirect(
            "/dashboard"
        )

    settings = CompanySettings.query.first()

    if request.method == "POST":

        settings.company_name = request.form[
            "company_name"
        ]

        settings.address = request.form[
            "address"
        ]

        settings.phone = request.form[
            "phone"
        ]

        settings.email = request.form[
            "email"
        ]

        db.session.commit()

        log_action(
            current_user.username,
            "Updated Company Settings"
        )

        flash(
            "Settings Updated"
        )

        return redirect(
            "/admin/settings"
        )

    return render_template(
        "admin_settings.html",
        settings=settings
    )
  
@app.route(
    "/upload-logo",
    methods=["POST"]
)
@login_required
def upload_logo():

    if not admin_required():

        return redirect(
            "/dashboard"
        )

    file = request.files.get(
        "logo"
    )

    if not file:

        flash(
            "No file selected"
        )

        return redirect(
            "/admin/settings"
        )

    if not allowed_file(
        file.filename
    ):

        flash(
            "Invalid file type"
        )

        return redirect(
            "/admin/settings"
        )

    filename = secure_filename(
        file.filename
    )

    os.makedirs(
        "uploads/logos",
        exist_ok=True
    )

    filepath = os.path.join(
        "uploads/logos",
        filename
    )

    file.save(filepath)

    settings = CompanySettings.query.first()

    settings.logo = filepath

    db.session.commit()

    log_action(
        current_user.username,
        "Uploaded Company Logo"
    )

    flash(
        "Logo Uploaded"
    )

    return redirect(
        "/admin/settings"
)

@app.route(
    "/profile",
    methods=["GET"]
)
@login_required
def profile():

    return render_template(
        "profile.html",
        user=current_user
  )

@app.route(
    "/change-username",
    methods=["POST"]
)
@login_required
def change_username():

    username = request.form[
        "username"
    ]

    current_user.username = username

    db.session.commit()

    log_action(
        current_user.username,
        "Changed Username"
    )

    flash(
        "Username Updated"
    )

    return redirect(
        "/profile"
    )

@app.route(
    "/change-password",
    methods=["POST"]
)
@login_required
def change_password():

    old_password = request.form[
        "old_password"
    ]

    new_password = request.form[
        "new_password"
    ]

    if not check_password_hash(
        current_user.password,
        old_password
    ):

        flash(
            "Wrong Password"
        )

        return redirect(
            "/profile"
        )

    current_user.password = \
    generate_password_hash(
        new_password
    )

    db.session.commit()

    log_action(
        current_user.username,
        "Changed Password"
    )

    flash(
        "Password Updated"
    )

    return redirect(
        "/profile"
    )

@app.route("/workers")
@login_required
def workers():

    if not admin_required():

        return redirect(
            "/dashboard"
        )

    workers = User.query.filter_by(
        role="worker"
    ).all()

    return render_template(
        "workers.html",
        workers=workers
    )

@app.route(
    "/edit-worker/<int:id>",
    methods=["GET", "POST"]
)
@login_required
def edit_worker(id):

    if not admin_required():

        return redirect(
            "/dashboard"
        )

    worker = User.query.get_or_404(
        id
    )

    if request.method == "POST":

        worker.username = request.form[
            "username"
        ]

        worker.email = request.form[
            "email"
        ]

        db.session.commit()

        log_action(
            current_user.username,
            f"Edited Worker {worker.username}"
        )

        flash(
            "Worker Updated"
        )

        return redirect(
            "/workers"
        )

    return render_template(
        "edit_worker.html",
        worker=worker
    )


@app.route(
    "/reset-worker-password/<int:id>"
)
@login_required
def reset_worker_password(id):

    if not admin_required():

        return redirect(
            "/dashboard"
        )

    worker = User.query.get_or_404(
        id
    )

    worker.password = \
    generate_password_hash(
        "Password@123"
    )

    db.session.commit()

    log_action(
        current_user.username,
        f"Reset Password For {worker.username}"
    )

    flash(
        "Password Reset"
    )

    return redirect(
        "/workers"
    )

@app.route(
    "/disable-worker/<int:id>"
)
@login_required
def disable_worker(id):

    if not admin_required():

        return redirect(
            "/dashboard"
        )

    worker = User.query.get_or_404(
        id
    )

    worker.status = "disabled"

    db.session.commit()

    log_action(
        current_user.username,
        f"Disabled {worker.username}"
    )

    flash(
        "Worker Disabled"
    )

    return redirect(
        "/workers"
    )

@app.route(
    "/activate-worker/<int:id>"
)
@login_required
def activate_worker(id):

    if not admin_required():

        return redirect(
            "/dashboard"
        )

    worker = User.query.get_or_404(
        id
    )

    worker.status = "active"

    db.session.commit()

    log_action(
        current_user.username,
        f"Activated {worker.username}"
    )

    flash(
        "Worker Activated"
    )

    return redirect(
        "/workers"
    )

@app.route("/audit-logs")
@login_required
def audit_logs():

    if not admin_required():

        return redirect(
            "/dashboard"
        )

    logs = AuditLog.query.order_by(
        AuditLog.id.desc()
    ).all()

    return render_template(
        "audit_logs.html",
        logs=logs
    )

@app.route(
    "/delete-worker/<int:id>"
)
@login_required
def delete_worker(id):

    if current_user.role != \
    "super_admin":

        flash(
            "Access Denied"
        )

        return redirect(
            "/workers"
        )

    worker = User.query.get_or_404(
        id
    )

    db.session.delete(
        worker
    )

    db.session.commit()

    log_action(
        current_user.username,
        f"Deleted Worker {worker.username}"
    )

    flash(
        "Worker Deleted"
    )

    return redirect(
        "/workers"
    )
class Job(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(255)
    )

    department = db.Column(
        db.String(255)
    )

    description = db.Column(
        db.Text
    )

    requirements = db.Column(
        db.Text
    )

    closing_date = db.Column(
        db.Date
    )

    status = db.Column(
        db.String(20),
        default="open"
    )

    created_at = db.Column(
        db.DateTime,
        default=nigeria_time
  )

class Application(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    application_number = db.Column(
        db.String(50),
        unique=True
    )

    fullname = db.Column(
        db.String(255)
    )

    email = db.Column(
        db.String(255)
    )

    phone = db.Column(
        db.String(50)
    )

    gender = db.Column(
        db.String(20)
    )

    address = db.Column(
        db.Text
    )

    state_of_origin = db.Column(
        db.String(100)
    )

    position = db.Column(
        db.String(255)
    )

    passport = db.Column(
        db.String(255)
    )

    cv = db.Column(
        db.String(255)
    )

    status = db.Column(
        db.String(50),
        default="pending"
    )

    created_at = db.Column(
        db.DateTime,
        default=nigeria_time
    )

class Interview(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    application_id = db.Column(
        db.Integer
    )

    interview_date = db.Column(
        db.Date
    )

    interview_time = db.Column(
        db.String(50)
    )

    venue = db.Column(
        db.Text
    )

    interviewer = db.Column(
        db.String(255)
    )

    status = db.Column(
        db.String(20),
        default="scheduled"
    )

    created_at = db.Column(
        db.DateTime,
        default=nigeria_time
    )

def generate_application_number():

    last = Application.query.order_by(
        Application.id.desc()
    ).first()

    if not last:

        return "APP001"

    number = last.id + 1

    return f"APP{str(number).zfill(3)}"

@app.route("/careers")
def careers():

    jobs = Job.query.filter_by(
        status="open"
    ).all()

    return render_template(
        "careers.html",
        jobs=jobs
    )

@app.route(
    "/create-job",
    methods=["GET", "POST"]
)
@login_required
def create_job():

    if not admin_required():

        return redirect("/dashboard")

    if request.method == "POST":

        job = Job(

            title=request.form["title"],

            department=request.form[
                "department"
            ],

            description=request.form[
                "description"
            ],

            requirements=request.form[
                "requirements"
            ],

            closing_date=datetime.strptime(
                request.form[
                    "closing_date"
                ],
                "%Y-%m-%d"
            )
        )

        db.session.add(job)

        db.session.commit()

        log_action(
            current_user.username,
            f"Created Job {job.title}"
        )

        flash("Job Created")

        return redirect("/jobs")

    return render_template(
        "create_job.html"
    )

@app.route("/jobs")
@login_required
def jobs():

    jobs = Job.query.all()

    return render_template(
        "jobs.html",
        jobs=jobs
  )

@app.route(
    "/apply/<int:job_id>",
    methods=["GET", "POST"]
)
def apply(job_id):

    job = Job.query.get_or_404(
        job_id
    )

    if request.method == "POST":

        application = Application(

            application_number=
            generate_application_number(),

            fullname=request.form[
                "fullname"
            ],

            email=request.form[
                "email"
            ],

            phone=request.form[
                "phone"
            ],

            gender=request.form[
                "gender"
            ],

            address=request.form[
                "address"
            ],

            state_of_origin=
            request.form[
                "state_of_origin"
            ],

            position=job.title
        )

        db.session.add(
            application
        )

        db.session.commit()

        flash(
            "Application Submitted"
        )

        return redirect(
            "/application-status"
        )

    return render_template(
        "apply.html",
        job=job
    )

@app.route("/applications")
@login_required
def applications():

    if not admin_required():

        return redirect("/dashboard")

    applications = Application.query.order_by(
        Application.id.desc()
    ).all()

    return render_template(
        "applications.html",
        applications=applications
    )

@app.route(
    "/schedule-interview/<int:id>",
    methods=["GET", "POST"]
)
@login_required
def schedule_interview(id):

    application = Application.query.get_or_404(id)

    if request.method == "POST":

        interview = Interview(
            application_id=application.id,
            interview_date=request.form["interview_date"],
            interview_time=request.form["interview_time"],
            interviewer=request.form["interviewer"],
            venue=request.form["venue"]
        )

        application.status = "interview_scheduled"

        db.session.add(interview)
        db.session.commit()

        send_email(
            application.email,
            "Interview Invitation",
            f"""
Dear {application.fullname},

You have been invited for an interview.

Date: {interview.interview_date}

Time: {interview.interview_time}

Venue: {interview.venue}

AV KING VET DRUG VENTURE
"""
        )

        flash("Interview Scheduled Successfully")

        return redirect("/applications")

    return render_template(
        "schedule_interview.html",
        application=application
    )

@app.route("/interviews")
@login_required
def interviews():

    interviews = Interview.query.order_by(
        Interview.interview_date.asc()
    ).all()

    return render_template(
        "interviews.html",
        interviews=interviews
    )



@app.route(
    "/worker-register",
    methods=["GET", "POST"]
)
def worker_register():

    if request.method == "POST":

        application_number = \
        request.form[
            "application_number"
        ]

        application = \
        Application.query.filter_by(
            application_number=
            application_number,
            status="approved"
        ).first()

        if not application:

            flash(
                "Application Not Approved"
            )

            return redirect(
                "/worker-register"
            )

        worker = User(

            employee_id=
            generate_employee_id(),

            fullname=
            application.fullname,

            username=
            request.form[
                "username"
            ],

            email=
            application.email,

            password=
            generate_password_hash(
                request.form[
                    "password"
                ]
            ),

            role="worker"
        )

        db.session.add(worker)

        db.session.commit()

        flash(
            "Account Created"
        )

        return redirect("/login")

    return render_template(
        "worker_register.html"
    )

class Department(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(255),
        unique=True
    )

    description = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=nigeria_time
    )

class Attendance(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    employee_id = db.Column(
        db.String(20)
    )

    username = db.Column(
        db.String(100)
    )

    attendance_date = db.Column(
        db.Date
    )

    clock_in = db.Column(
        db.DateTime
    )

    clock_out = db.Column(
        db.DateTime
    )

    status = db.Column(
        db.String(20),
        default="Present"
    )

    created_at = db.Column(
        db.DateTime,
        default=nigeria_time
    )

class LeaveRequest(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    employee_id = db.Column(
        db.String(20)
    )

    fullname = db.Column(
        db.String(255)
    )

    leave_type = db.Column(
        db.String(100)
    )

    start_date = db.Column(
        db.Date
    )

    end_date = db.Column(
        db.Date
    )

    reason = db.Column(
        db.Text
    )

    status = db.Column(
        db.String(20),
        default="Pending"
    )

    created_at = db.Column(
        db.DateTime,
        default=nigeria_time
    )

@app.route(
    "/create-department",
    methods=["GET","POST"]
)
@login_required
def create_department():

    if not admin_required():
        return redirect("/dashboard")

    if request.method == "POST":

        department = Department(

            name=request.form["name"],

            description=request.form[
                "description"
            ]
        )

        db.session.add(department)

        db.session.commit()

        flash(
            "Department Created"
        )

        return redirect(
            "/departments"
        )

    return render_template(
        "create_department.html"
    )


@app.route("/departments")
@login_required
def departments():

    departments = Department.query.all()

    return render_template(
        "departments.html",
        departments=departments
  )

@app.route("/worker-dashboard")
@login_required
def worker_dashboard():

    attendance_count = \
    Attendance.query.filter_by(
        employee_id=
        current_user.employee_id
    ).count()

    leave_count = \
    LeaveRequest.query.filter_by(
        employee_id=
        current_user.employee_id
    ).count()

    return render_template(

        "worker_dashboard.html",

        attendance_count=
        attendance_count,

        leave_count=
        leave_count
    )

@app.route("/clock-in")
@login_required
def clock_in():

    today = nigeria_time().date()

    existing = \
    Attendance.query.filter_by(

        employee_id=
        current_user.employee_id,

        attendance_date=today

    ).first()

    if existing:

        flash(
            "Already Clocked In"
        )

        return redirect(
            "/worker-dashboard"
        )

    now = nigeria_time()

    status = "Present"

    official_time = now.replace(
        hour=8,
        minute=0,
        second=0
    )

    if now > official_time:

        status = "Late"

    attendance = Attendance(

        employee_id=
        current_user.employee_id,

        username=
        current_user.username,

        attendance_date=today,

        clock_in=now,

        status=status
    )

    db.session.add(
        attendance
    )

    db.session.commit()

    flash(
        f"Clocked In ({status})"
    )

    return redirect(
        "/worker-dashboard"
    )

@app.route("/clock-out")
@login_required
def clock_out():

    today = nigeria_time().date()

    attendance = \
    Attendance.query.filter_by(

        employee_id=
        current_user.employee_id,

        attendance_date=today

    ).first()

    if not attendance:

        flash(
            "Clock In First"
        )

        return redirect(
            "/worker-dashboard"
        )

    attendance.clock_out = \
    nigeria_time()

    db.session.commit()

    flash(
        "Clocked Out"
    )

    return redirect(
        "/worker-dashboard"
    )

@app.route("/attendance-history")
@login_required
def attendance_history():

    records = \
    Attendance.query.filter_by(

        employee_id=
        current_user.employee_id

    ).order_by(
        Attendance.id.desc()
    ).all()

    return render_template(

        "attendance_history.html",

        records=records
    )

def attendance_percentage(
    employee_id
):

    total = \
    Attendance.query.filter_by(
        employee_id=
        employee_id
    ).count()

    present = \
    Attendance.query.filter(
        Attendance.employee_id
        == employee_id,

        Attendance.status.in_(
            ["Present","Late"]
        )
    ).count()

    if total == 0:
        return 0

    return round(
        (present / total) * 100,
        2
    )

@app.route(
    "/apply-leave",
    methods=["GET","POST"]
)
@login_required
def apply_leave():

    if request.method == "POST":

        leave = LeaveRequest(

            employee_id=
            current_user.employee_id,

            fullname=
            current_user.fullname,

            leave_type=
            request.form[
                "leave_type"
            ],

            start_date=
            datetime.strptime(
                request.form[
                    "start_date"
                ],
                "%Y-%m-%d"
            ),

            end_date=
            datetime.strptime(
                request.form[
                    "end_date"
                ],
                "%Y-%m-%d"
            ),

            reason=
            request.form[
                "reason"
            ]
        )

        db.session.add(
            leave
        )

        db.session.commit()

        flash(
            "Leave Submitted"
        )

        return redirect(
            "/worker-dashboard"
        )

    return render_template(
        "apply_leave.html"
    )

@app.route("/leave-requests")
@login_required
def leave_requests():

    requests = \
    LeaveRequest.query.order_by(
        LeaveRequest.id.desc()
    ).all()

    return render_template(

        "leave_requests.html",

        requests=requests
    )

@app.route(
    "/approve-leave/<int:id>"
)
@login_required
def approve_leave(id):

    leave = \
    LeaveRequest.query.get_or_404(
        id
    )

    leave.status = "Approved"

    db.session.commit()

    flash(
        "Leave Approved"
    )

    return redirect(
        "/leave-requests"
    )

@app.route(
    "/reject-leave/<int:id>"
)
@login_required
def reject_leave(id):

    leave = \
    LeaveRequest.query.get_or_404(
        id
    )

    leave.status = "Rejected"

    db.session.commit()

    flash(
        "Leave Rejected"
    )

    return redirect(
        "/leave-requests"
    )

@app.route("/attendance-dashboard")
@login_required
def attendance_dashboard():

    total_attendance = \
    Attendance.query.count()

    late_workers = \
    Attendance.query.filter_by(
        status="Late"
    ).count()

    today = nigeria_time().date()

    today_attendance = \
    Attendance.query.filter_by(
        attendance_date=today
    ).count()

    return render_template(

        "attendance_dashboard.html",

        total_attendance=
        total_attendance,

        late_workers=
        late_workers,

        today_attendance=
        today_attendance
    )

class Announcement(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(255)
    )

    message = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=nigeria_time
  )

class Notification(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    employee_id = db.Column(
        db.String(20)
    )

    title = db.Column(
        db.String(255)
    )

    message = db.Column(
        db.Text
    )

    status = db.Column(
        db.String(20),
        default="Unread"
    )

    created_at = db.Column(
        db.DateTime,
        default=nigeria_time
    )

class WebsiteContent(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    page = db.Column(
        db.String(50)
    )

    title = db.Column(
        db.String(255)
    )

    content = db.Column(
        db.Text
    )

@app.route(
    "/upload-profile-photo",
    methods=["POST"]
)
@login_required
def upload_profile_photo():

    file = request.files["photo"]

    if file:

        filename = secure_filename(
            file.filename
        )

        os.makedirs(
            "uploads/profile",
            exist_ok=True
        )

        path = os.path.join(
            "uploads/profile",
            filename
        )

        file.save(path)

        current_user.profile_photo = path

        db.session.commit()

        flash(
            "Profile Updated"
        )

    return redirect("/profile")
@app.route(
    "/create-announcement",
    methods=["GET","POST"]
)
@login_required
def create_announcement():

    if not admin_required():
        return redirect("/dashboard")

    if request.method == "POST":

        announcement = Announcement(

            title=request.form["title"],

            message=request.form[
                "message"
            ]
        )

        db.session.add(
            announcement
        )

        db.session.commit()

        flash(
            "Announcement Published"
        )

        return redirect(
            "/announcements"
        )

    return render_template(
        "create_announcement.html"
    )

@app.route("/announcements")
@login_required
def announcements():

    announcements = \
    Announcement.query.order_by(
        Announcement.id.desc()
    ).all()

    return render_template(
        "announcements.html",
        announcements=announcements
    )

@app.route("/notifications")
@login_required
def notifications():

    notifications = \
    Notification.query.filter_by(
        employee_id=
        current_user.employee_id
    ).all()

    return render_template(
        "notifications.html",
        notifications=notifications
    )

def send_notification(
    employee_id,
    title,
    message
):

    notice = Notification(

        employee_id=
        employee_id,

        title=title,

        message=message
    )

    db.session.add(notice)

    db.session.commit()

qr_token = db.Column(
    db.String(255)
)

import uuid

def generate_qr_token():

    return str(
        uuid.uuid4()
    )

@app.route(
    "/export-attendance-excel"
)
@login_required
def export_attendance_excel():

    import pandas as pd

    data = []

    records = Attendance.query.all()

    for record in records:

        data.append({

            "Employee ID":
            record.employee_id,

            "Username":
            record.username,

            "Date":
            record.attendance_date,

            "Status":
            record.status
        })

    df = pd.DataFrame(data)

    filename = "attendance.xlsx"

    df.to_excel(
        filename,
        index=False
    )

    return send_file(
        filename,
        as_attachment=True
  )

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph
)

from reportlab.lib.styles import \
getSampleStyleSheet

@app.route(
    "/export-attendance-pdf"
)
@login_required
def export_attendance_pdf():

    pdf = SimpleDocTemplate(
        "attendance.pdf"
    )

    styles = getSampleStyleSheet()

    content = []

    records = Attendance.query.all()

    for record in records:

        content.append(

            Paragraph(

                f"{record.employee_id} "
                f"{record.username} "
                f"{record.status}",

                styles["BodyText"]
            )
        )

    pdf.build(content)

    return send_file(
        "attendance.pdf",
        as_attachment=True
    )
@app.route(
    "/toggle-theme"
)
@login_required
def toggle_theme():

    if current_user.theme == "light":

        current_user.theme = "dark"

    else:

        current_user.theme = "light"

    db.session.commit()

    return redirect(
        request.referrer
  )

@app.route(
    "/cms/<page>",
    methods=["GET","POST"]
)
@login_required
def cms(page):

    if not admin_required():
        return redirect("/dashboard")

    content = \
    WebsiteContent.query.filter_by(
        page=page
    ).first()

    if not content:

        content = WebsiteContent(
            page=page
        )

        db.session.add(content)

        db.session.commit()

    if request.method == "POST":

        content.title = request.form[
            "title"
        ]

        content.content = request.form[
            "content"
        ]

        db.session.commit()

        flash("Updated")

    return render_template(
        "cms.html",
        content=content
      )

@app.route("/")
def home():

    page = \
    WebsiteContent.query.filter_by(
        page="home"
    ).first()

    return render_template(
        "public_home.html",
        page=page
    )

@app.route("/about")
def about():

    page = \
    WebsiteContent.query.filter_by(
        page="about"
    ).first()

    return render_template(
        "about.html",
        page=page
    )

@app.route("/contact")
def contact():

    page = \
    WebsiteContent.query.filter_by(
        page="contact"
    ).first()

    return render_template(
        "contact.html",
        page=page
    )

def send_email(
    recipient,
    subject,
    body
):

    try:

        msg = Message(

            subject,

            sender=
            app.config[
                "MAIL_USERNAME"
            ],

            recipients=[
                recipient
            ]
        )

        msg.body = body

        mail.send(msg)

    except Exception as e:

        print(e)



@app.route(
    "/approve-application/<int:id>"
)
@login_required
def approve_application(id):

    application = Application.query.get_or_404(id)

    application.status = "Approved"

    db.session.commit()

    send_email(

        application.email,

        "Application Approved",

        f"""
Congratulations.

Your application has been approved.

Application Number:
{application.application_number}

You may now create your worker account.

AV KING VET DRUG VENTURE
"""
    )

    flash("Application Approved")

    return redirect("/applications")



@app.route(
    "/reject-application/<int:id>"
)
@login_required
def reject_application(id):

    application = Application.query.get_or_404(id)

    application.status = "Rejected"

    db.session.commit()

    send_email(

        application.email,

        "Application Update",

        f"""
Thank you for applying.

Unfortunately your application
was not successful.

AV KING VET DRUG VENTURE
"""
    )

    flash("Application Rejected")

    return redirect("/applications")
    

class Payroll(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    employee_id = db.Column(
        db.String(20)
    )

    fullname = db.Column(
        db.String(255)
    )

    basic_salary = db.Column(
        db.Float
    )

    allowance = db.Column(
        db.Float
    )

    deduction = db.Column(
        db.Float
    )

    net_salary = db.Column(
        db.Float
    )

    month = db.Column(
        db.String(20)
    )

    year = db.Column(
        db.String(10)
    )

    created_at = db.Column(
        db.DateTime,
        default=nigeria_time
    )

@app.route(
    "/create-payroll",
    methods=["GET","POST"]
)
@login_required
def create_payroll():

    if not admin_required():

        return redirect(
            "/dashboard"
        )

    if request.method == "POST":

        basic_salary = float(
            request.form[
                "basic_salary"
            ]
        )

        allowance = float(
            request.form[
                "allowance"
            ]
        )

        deduction = float(
            request.form[
                "deduction"
            ]
        )

        payroll = Payroll(

            employee_id=
            request.form[
                "employee_id"
            ],

            fullname=
            request.form[
                "fullname"
            ],

            basic_salary=
            basic_salary,

            allowance=
            allowance,

            deduction=
            deduction,

            net_salary=
            basic_salary
            + allowance
            - deduction,

            month=
            request.form[
                "month"
            ],

            year=
            request.form[
                "year"
            ]
        )

        db.session.add(
            payroll
        )

        db.session.commit()

        flash(
            "Payroll Created"
        )

        return redirect(
            "/payrolls"
        )

    return render_template(
        "create_payroll.html"
    )

@app.route("/payrolls")
@login_required
def payrolls():

    payrolls = Payroll.query.all()

    return render_template(
        "payrolls.html",
        payrolls=payrolls
    )

@app.route(
    "/payslip/<int:id>"
)
@login_required
def payslip(id):

    payroll = Payroll.query.get_or_404(
        id
    )

    pdf = SimpleDocTemplate(
        "payslip.pdf"
    )

    styles = getSampleStyleSheet()

    content = [

        Paragraph(
            "AV KING VET DRUG VENTURE",
            styles["Title"]
        ),

        Paragraph(
            payroll.fullname,
            styles["BodyText"]
        ),

        Paragraph(
            f"Employee ID: "
            f"{payroll.employee_id}",
            styles["BodyText"]
        ),

        Paragraph(
            f"Net Salary: ₦"
            f"{payroll.net_salary}",
            styles["BodyText"]
        )
    ]

    pdf.build(content)

    return send_file(
        "payslip.pdf",
        as_attachment=True
  )

class Performance(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    employee_id = db.Column(
        db.String(20)
    )

    score = db.Column(
        db.Integer
    )

    remarks = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=nigeria_time
    )

@app.route("/analytics")
@login_required
def analytics():

    total_workers = User.query.filter_by(
        role="worker"
    ).count()

    total_departments = \
    Department.query.count()

    total_attendance = \
    Attendance.query.count()

    return render_template(

        "analytics.html",

        total_workers=
        total_workers,

        total_departments=
        total_departments,

        total_attendance=
        total_attendance
    )

@app.route("/backup")
@login_required
def backup():

    os.system(

        "mysqldump "
        "-u root "
        "-pPASSWORD "
        "avking_hrms "
        "> backup.sql"
    )

    return send_file(
        "backup.sql",
        as_attachment=True
    )

import re

def strong_password(password):

    pattern = r"""
    ^(?=.*[A-Z])
    (?=.*[a-z])
    (?=.*\d)
    (?=.*[@$!%*?&])
    .{8,}
    """

    return re.match(
        pattern,
        password,
        re.VERBOSE
    )
if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
  )

  

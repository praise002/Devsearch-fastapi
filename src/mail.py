from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, MessageType

from src.config import conf


def get_email_template_data(email_type: str, **kwargs) -> dict:
    """
    Returns the appropriate template file and subject based on email type.

    Args:
        email_type: Type of email ('activate', 'reset', 'reset-success', 'welcome')
        **kwargs: Additional data like 'otp' that may be needed

    Returns:
        dict: Contains 'template_name' and 'subject'
    """
    email_templates = {
        "activate": {
            "template_name": "verify_email_request.html",
            "subject": "Verify your email",
        },
        "reset": {
            "template_name": "password_reset_email.html",
            "subject": "Reset Your Password",
        },
        "reset-success": {
            "template_name": "password_reset_success.html",
            "subject": "Password Reset Successful",
        },
        "welcome": {
            "template_name": "welcome_message.html",
            "subject": "Account Verified",
        },
    }

    return email_templates.get(email_type, email_templates["welcome"])


def send_email(
    background_tasks: BackgroundTasks,
    subject: str,
    email_to: str,
    template_context: dict,
    template_name: str,
):
    """
    Send an email using FastMail with a template.

    Args:
        background_tasks: FastAPI BackgroundTasks instance
        subject: Email subject line
        email_to: Recipient email address
        template_context: Dictionary of variables for the template
        template_name: Name of the HTML template file
    """
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        template_body=template_context,
        subtype=MessageType.html,
    )
    fm = FastMail(conf)
    background_tasks.add_task(
        fm.send_message,
        message,
        template_name=template_name,
    )


def send_email_by_type(
    background_tasks: BackgroundTasks,
    email_type: str,
    email_to: str,
    name: str,
    otp: str = None,
):
    """
    Simplified email sending function that uses email type to determine template and subject.
    
    Args:
        background_tasks: FastAPI BackgroundTasks instance
        email_type: Type of email ('activate', 'reset', 'reset-success', 'welcome')
        email_to: Recipient email address
        name: Recipient's first name
        otp: Optional OTP code for verification emails
    """
    email_data = get_email_template_data(email_type)
    
    # Build template context
    template_context = {"name": name}
    if otp:
        template_context["otp"] = str(otp)
    
    send_email(
        background_tasks,
        email_data["subject"],
        email_to,
        template_context,
        email_data["template_name"],
    )
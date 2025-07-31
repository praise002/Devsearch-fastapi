from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, MessageType

from src.config import conf


def send_email(
    background_tasks: BackgroundTasks,
    subject: str,
    email_to: str,
    template_context: dict,
    template_name: str,
):
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

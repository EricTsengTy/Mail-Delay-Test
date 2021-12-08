import smtplib
from getpass import getpass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Send to gmail with specific content
def send_from_smtp(
        send_addr, 
        send_pass, 
        recv_addr,
        smtp_server: tuple,     # (ip: str, port: int)
        subject='Test mail',
        content='Test mail'
    ):
    # Setup Headers
    message = MIMEMultipart()
    message['From'] = send_addr
    message['To'] = recv_addr
    message['Subject'] = subject

    # The body and the attachments for the mail
    message.attach(MIMEText(content, 'plain'))

    # Create SMTP session for sending the mail
    session = smtplib.SMTP(smtp_server[0], smtp_server[1]) # use gmail with port
    # session.set_debuglevel(1)
    session.starttls() # enable security
    session.login(send_addr, send_pass) # login with mail_id and password
    text = message.as_string()
    session.sendmail(send_addr, recv_addr, text)
    session.quit()
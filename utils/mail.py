import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

def send_status_email(enquiry, status, notes=''):
    """
    Sends a status update email to the student with their enquiry details.
    Falls back to logging/console if SMTP settings are not configured.
    """
    # 1. Gather school/SMTP configuration
    smtp_server   = os.getenv('SMTP_SERVER', '')
    smtp_port     = int(os.getenv('SMTP_PORT', '587'))
    smtp_username = os.getenv('SMTP_USERNAME', 'demoa4447@gmail.com')
    smtp_password = os.getenv('SMTP_PASSWORD', '')
    
    school_name   = os.getenv('SCHOOL_NAME', 'Vivekanand Vidya Mandir Dharampur')
    school_address = os.getenv('SCHOOL_ADDRESS', 'Dharampur, Tatijhariya Hazaribagh, Jharkhand')
    school_phone   = os.getenv('SCHOOL_PHONE', '7070373801')
    school_email   = os.getenv('SCHOOL_EMAIL', 'demoa4447@gmail.com')
    
    recipient = enquiry.get('email')
    if not recipient:
        logger.warning(f"No email address found for enquiry ID {enquiry.get('id')}. Skipping email.")
        return False
        
    subject = f"Update on your Admission Enquiry - {school_name}"
    
    # Define color branding based on status
    status_colors = {
        'Accepted': '#10E87B', # Vibrant Green
        'Rejected': '#FF4D6D', # Rose Red
        'Contacted': '#F5C842', # Gold
        'Admitted': '#7C6FEF', # Purple
        'Not Interested': '#888888',
        'New': '#00D4FF' # Cyan
    }
    status_color = status_colors.get(status, '#00D4FF')

    # Define state-specific dynamic messages and instruction cards
    if status == 'Accepted':
        status_instructions = f"""
        <div style="background-color: rgba(16, 232, 123, 0.05); border: 1px solid rgba(16, 232, 123, 0.2); border-left: 4px solid #10E87B; border-radius: 8px; padding: 20px; margin-bottom: 25px; line-height: 1.6;">
            <div style="font-weight: 800; color: #10E87B; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">📋 Document Verification Process</div>
            <p style="margin: 0 0 12px 0; font-size: 14px; color: #cbd5e1;">
                Congratulations! Your admission enquiry has been <strong>Accepted</strong>. 
                You are kindly requested to visit the school campus to complete the document verification and finalize admission.
            </p>
            <div style="font-weight: 700; color: #ffffff; font-size: 13px; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.5px;">Required Documents to Bring:</div>
            <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #94a3b8; line-height: 1.8;">
                <li>Student's Aadhaar Card (Original & Photocopy)</li>
                <li>Birth Certificate (Original & Photocopy)</li>
                <li>School Leaving / Transfer Certificate (T.C.)</li>
                <li>Recent Passport-size Photograph of the Student</li>
                <li>Parents' Aadhaar Card (Original & Photocopy)</li>
            </ul>
        </div>
        """
    elif status == 'Rejected':
        status_instructions = """
        <div style="background-color: rgba(255, 77, 109, 0.05); border: 1px solid rgba(255, 77, 109, 0.2); border-left: 4px solid #FF4D6D; border-radius: 8px; padding: 20px; margin-bottom: 25px; line-height: 1.6;">
            <div style="font-weight: 800; color: #FF4D6D; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">Admission Notice</div>
            <p style="margin: 0; font-size: 14px; color: #cbd5e1;">
                We regret to inform you that we are unable to accept your admission enquiry at this time due to class size constraints or seat limitations. We appreciate your interest in our institution and wish you the best in your academic path.
            </p>
        </div>
        """
    elif status == 'Admitted':
        status_instructions = f"""
        <div style="background-color: rgba(124, 111, 239, 0.05); border: 1px solid rgba(124, 111, 239, 0.2); border-left: 4px solid #7C6FEF; border-radius: 8px; padding: 20px; margin-bottom: 25px; line-height: 1.6;">
            <div style="font-weight: 800; color: #7C6FEF; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">🎉 Welcome to our School Family!</div>
            <p style="margin: 0; font-size: 14px; color: #cbd5e1;">
                Congratulations! The student's admission has been successfully registered and they are now officially <strong>Admitted</strong> to {school_name}. 
                We are extremely excited to welcome you to our community and look forward to partnering with you for a brilliant learning journey.
            </p>
        </div>
        """
    else:
        status_instructions = ""
    
    # 2. Build the premium HTML email template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{subject}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                background-color: #0f111a;
                color: #e2e8f0;
                margin: 0;
                padding: 0;
                -webkit-font-smoothing: antialiased;
            }}
            .email-wrapper {{
                max-width: 600px;
                margin: 30px auto;
                background-color: #151926;
                border: 1px solid rgba(0, 212, 255, 0.15);
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            }}
            .header {{
                background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
                padding: 30px 40px;
                text-align: center;
                border-bottom: 1px solid rgba(0, 212, 255, 0.1);
            }}
            .logo-placeholder {{
                font-size: 32px;
                margin-bottom: 10px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 800;
                color: #ffffff;
                letter-spacing: -0.5px;
            }}
            .header p {{
                margin: 5px 0 0 0;
                font-size: 13px;
                color: #a5b4fc;
                text-transform: uppercase;
                letter-spacing: 1.5px;
            }}
            .content {{
                padding: 40px;
            }}
            .status-badge-container {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .status-badge {{
                display: inline-block;
                padding: 8px 24px;
                font-size: 14px;
                font-weight: 800;
                text-transform: uppercase;
                color: #0f111a;
                background-color: {status_color};
                border-radius: 99px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            }}
            .greeting {{
                font-size: 16px;
                line-height: 1.6;
                color: #e2e8f0;
                margin-bottom: 25px;
            }}
            .details-card {{
                background-color: #0f111a;
                border: 1px solid rgba(226, 232, 240, 0.08);
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 30px;
            }}
            .details-title {{
                font-size: 14px;
                font-weight: 700;
                color: #a5b4fc;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 15px;
                border-bottom: 1px solid rgba(226, 232, 240, 0.08);
                padding-bottom: 8px;
            }}
            .detail-row {{
                display: flex;
                margin-bottom: 10px;
                font-size: 14px;
            }}
            .detail-label {{
                width: 150px;
                color: #94a3b8;
                font-weight: 600;
            }}
            .detail-value {{
                flex: 1;
                color: #ffffff;
            }}
            .notes-section {{
                background-color: rgba(245, 200, 66, 0.05);
                border-left: 4px solid #f5c842;
                border-radius: 4px;
                padding: 16px;
                margin-bottom: 30px;
                font-size: 14px;
                color: #e2e8f0;
                line-height: 1.6;
            }}
            .notes-title {{
                font-weight: 700;
                color: #f5c842;
                margin-bottom: 6px;
            }}
            .footer {{
                background-color: #0c0e17;
                padding: 30px 40px;
                text-align: center;
                border-top: 1px solid rgba(226, 232, 240, 0.05);
                font-size: 12px;
                color: #64748b;
                line-height: 1.6;
            }}
            .footer a {{
                color: #7c6fef;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="email-wrapper">
            <div class="header">
                <div class="logo-placeholder">🏫</div>
                <h1>{school_name}</h1>
                <p>Admission & Enquiries</p>
            </div>
            
            <div class="content">
                <div class="greeting">
                    Dear <strong>{enquiry.get('student_name')}</strong>,
                    <br><br>
                    Thank you for your interest in <strong>{school_name}</strong>. We have updated the status of your admission enquiry. Please find the details below:
                </div>
                
                <div class="status-badge-container">
                    <span class="status-badge">{status}</span>
                </div>
                
                {status_instructions}
                
                <div class="details-card">
                    <div class="details-title">Enquiry Summary</div>
                    <div class="detail-row">
                        <div class="detail-label">Student Name:</div>
                        <div class="detail-value">{enquiry.get('student_name')}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">Father's Name:</div>
                        <div class="detail-value">{enquiry.get('father_name', '-')}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">Class Applying:</div>
                        <div class="detail-value">{enquiry.get('class_applying', '-')}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">Mobile Number:</div>
                        <div class="detail-value">{enquiry.get('mobile', '-')}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">Current School:</div>
                        <div class="detail-value">{enquiry.get('current_school', '-')}</div>
                    </div>
                </div>
                
                {f'''
                <div class="notes-section">
                    <div class="notes-title">Additional Remarks from school:</div>
                    <div>{notes}</div>
                </div>
                ''' if notes else ''}
                
                <div class="greeting">
                    If you have any further questions or would like to schedule a school tour, feel free to reply to this email or call our admissions office at <strong>{school_phone}</strong>.
                    <br><br>
                    Best regards,
                    <br>
                    <strong>Admissions Team</strong>
                    <br>
                    {school_name}
                </div>
            </div>
            
            <div class="footer">
                <strong>{school_name}</strong><br>
                {school_address}<br>
                Phone: {school_phone} | Email: <a href="mailto:{school_email}">{school_email}</a><br>
                <span style="font-size: 10px; color: #475569; display: block; margin-top: 10px;">This is an automated email regarding your admission enquiry. Please do not reply directly to this notification.</span>
            </div>
        </div>
    </body>
    </html>
    """

    # 3. Try sending email, fall back to console if SMTP not configured
    if not smtp_server or not smtp_username or not smtp_password:
        print("\n" + "="*80)
        print("  [WARNING] SMTP CONFIGURATION MISSING - FALLING BACK TO CONSOLE PRINTING")
        print("="*80)
        print(f"  To:       {recipient}")
        print(f"  Subject:  {subject}")
        print(f"  Status:   {status}")
        print(f"  Notes:    {notes}")
        print(f"  Student:  {enquiry.get('student_name')}")
        print("  --- HTML Content (Preview) ---")
        print(f"  Dear {enquiry.get('student_name')}, your enquiry status is now: {status}")
        print("="*80 + "\n")
        
        logger.info(f"SMTP not configured. Fallback logged status update '{status}' for {recipient}.")
        return True

    try:
        # Create message container
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{school_name} <{smtp_username}>"
        msg['To'] = recipient
        
        # Attach parts
        msg.attach(MIMEText(html_content, 'html'))
        
        # Connect & Send
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, recipient, msg.as_string())
        server.quit()
        
        logger.info(f"Status update email sent to {recipient} with status '{status}'")
        print(f"Success! Sent status update email to {recipient} with status '{status}'")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {e}")
        print(f"ERROR sending email to {recipient}: {e}")
        return False

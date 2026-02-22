"""
Notification Module for the Automated Book Generation System.
Supports Email (SMTP) and MS Teams Webhooks.
"""

import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from datetime import datetime
import requests

import config


# =============================================================================
# NOTIFICATION SERVICE
# =============================================================================

class NotificationService:
    """Service for sending notifications via Email and MS Teams."""
    
    def __init__(self):
        self.smtp_enabled = config.SMTP_ENABLED
        self.teams_enabled = config.TEAMS_WEBHOOK_ENABLED
    
    # =========================================================================
    # EMAIL NOTIFICATIONS
    # =========================================================================
    
    def send_email(
        self,
        subject: str,
        body: str,
        to_email: str = None,
        html_body: str = None
    ) -> bool:
        """Send email notification."""
        if not self.smtp_enabled:
            print("Email notifications are disabled")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = config.SMTP_FROM_EMAIL
            msg['To'] = to_email or config.SMTP_TO_EMAIL
            
            # Plain text version
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # HTML version (optional)
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Connect and send
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
                server.starttls()
                server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                server.send_message(msg)
            
            print(f"✓ Email sent: {subject}")
            return True
            
        except Exception as e:
            print(f"✗ Email error: {e}")
            return False
    
    # =========================================================================
    # MS TEAMS NOTIFICATIONS
    # =========================================================================
    
    def send_teams_message(
        self,
        title: str,
        message: str,
        color: str = "0076D7",
        facts: Dict[str, str] = None
    ) -> bool:
        """Send MS Teams webhook notification."""
        if not self.teams_enabled:
            print("Teams notifications are disabled")
            return False
        
        try:
            # Build adaptive card payload
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": color,
                "summary": title,
                "sections": [{
                    "activityTitle": title,
                    "facts": [],
                    "text": message,
                    "markdown": True
                }]
            }
            
            # Add facts if provided
            if facts:
                payload["sections"][0]["facts"] = [
                    {"name": k, "value": v} for k, v in facts.items()
                ]
            
            # Send webhook
            response = requests.post(
                config.TEAMS_WEBHOOK_URL,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload)
            )
            
            if response.status_code == 200:
                print(f"✓ Teams message sent: {title}")
                return True
            else:
                print(f"✗ Teams error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ Teams error: {e}")
            return False
    
    # =========================================================================
    # NOTIFICATION METHODS FOR BOOK EVENTS
    # =========================================================================
    
    def notify_outline_ready(self, book_id: int, book_title: str):
        """Notify that outline is ready for review."""
        subject = f"📚 Outline Ready for Review: {book_title}"
        message = f"""The outline for your book has been generated and is ready for review.

**Book:** {book_title}
**Book ID:** {book_id}
**Status:** Awaiting Review

Please review the outline and add your notes in the database.
Set `status_outline_notes` to 'yes' if you need more changes, or 'no_notes_needed' to proceed."""
        
        self._send_all(subject, message, "FFA500", {
            "Book": book_title,
            "ID": str(book_id),
            "Action Required": "Review Outline"
        })
    
    def notify_chapter_ready(self, book_id: int, book_title: str, chapter_num: int, chapter_title: str):
        """Notify that a chapter is ready for review."""
        subject = f"📖 Chapter {chapter_num} Ready: {book_title}"
        message = f"""Chapter {chapter_num} has been generated and is ready for review.

**Book:** {book_title}
**Chapter:** {chapter_num} - {chapter_title}
**Status:** Awaiting Review

Please review the chapter and add notes if needed."""
        
        self._send_all(subject, message, "0076D7", {
            "Book": book_title,
            "Chapter": f"{chapter_num} - {chapter_title}",
            "Action Required": "Review Chapter"
        })
    
    def notify_waiting_for_notes(self, book_id: int, book_title: str, stage: str):
        """Notify that system is waiting for notes."""
        subject = f"⏸️ Waiting for Notes: {book_title}"
        message = f"""The book generation system is paused waiting for your input.

**Book:** {book_title}
**Stage:** {stage}
**Status:** Paused - Waiting for Notes

Please add your notes in the database to continue the generation process."""
        
        self._send_all(subject, message, "FFA500", {
            "Book": book_title,
            "Stage": stage,
            "Status": "Waiting for Input"
        })
    
    def notify_final_draft_ready(self, book_id: int, book_title: str, output_path: str):
        """Notify that final draft is compiled."""
        subject = f"✅ Book Complete: {book_title}"
        message = f"""Congratulations! Your book has been successfully compiled.

**Book:** {book_title}
**Output File:** {output_path}
**Status:** Complete

The final draft has been generated and is ready for your review."""
        
        self._send_all(subject, message, "00FF00", {
            "Book": book_title,
            "Status": "Complete",
            "Output": output_path
        })
    
    def notify_error(self, book_id: int, book_title: str, error_message: str, stage: str):
        """Notify about an error."""
        subject = f"❌ Error in Book Generation: {book_title}"
        message = f"""An error occurred during book generation.

**Book:** {book_title}
**Stage:** {stage}
**Error:** {error_message}

Please check the system logs and resolve the issue."""
        
        self._send_all(subject, message, "FF0000", {
            "Book": book_title,
            "Stage": stage,
            "Error": error_message
        })
    
    def notify_all_chapters_complete(self, book_id: int, book_title: str, chapter_count: int):
        """Notify that all chapters are complete."""
        subject = f"📗 All Chapters Complete: {book_title}"
        message = f"""All {chapter_count} chapters have been generated and approved.

**Book:** {book_title}
**Total Chapters:** {chapter_count}
**Status:** Ready for Final Compilation

Please set `final_review_notes_status` to proceed with final compilation."""
        
        self._send_all(subject, message, "00FF00", {
            "Book": book_title,
            "Chapters": str(chapter_count),
            "Next Step": "Final Compilation"
        })
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _send_all(
        self,
        subject: str,
        message: str,
        color: str = "0076D7",
        facts: Dict[str, str] = None
    ):
        """Send notification via all enabled channels."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_with_time = f"{message}\n\n_Sent at: {timestamp}_"
        
        # Send email
        if self.smtp_enabled:
            self.send_email(subject, message_with_time.replace("**", "").replace("_", ""))
        
        # Send Teams message
        if self.teams_enabled:
            self.send_teams_message(subject, message_with_time, color, facts)
        
        # Console log if no notifications enabled
        if not self.smtp_enabled and not self.teams_enabled:
            print(f"\n{'='*60}")
            print(f"NOTIFICATION: {subject}")
            print(f"{'='*60}")
            print(message.replace("**", "").replace("_", ""))
            print(f"{'='*60}\n")


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def get_notification_service() -> NotificationService:
    """Get notification service instance."""
    return NotificationService()

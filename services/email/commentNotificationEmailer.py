"""
Comment Notification Emailer Service

This module monitors the 'notes' collection in Firebase Firestore for changes
to the 'comments' field and sends email notifications to note authors when
new comments are added.
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from firebase_admin import firestore
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr

# Load environment variables
load_dotenv()

# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
    MAIL_FROM=os.getenv("MAIL_FROM", "noreply@notionclone.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "true").lower() == "true",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "false").lower() == "true",
    USE_CREDENTIALS=os.getenv("USE_CREDENTIALS", "true").lower() == "true",
    VALIDATE_CERTS=os.getenv("VALIDATE_CERTS", "true").lower() == "true"
)

fast_mail = FastMail(conf)


def _extract_comment_info(comments: list, previous_comments: Optional[list] = None) -> Optional[Dict[str, Any]]:
    """
    Extract new comment information by comparing current and previous comments.

    Args:
        comments: Current list of comments
        previous_comments: Previous list of comments

    Returns:
        Dictionary with new comment info or None if no new comment
    """
    if not comments:
        return None

    # If no previous comments, the first comment is new
    if not previous_comments:
        latest_comment = comments[-1] if comments else None
        if latest_comment:
            return {
                "author": latest_comment.get("author", "Anonymous"),
                "author_email": latest_comment.get("author_email", ""),
                "content": latest_comment.get("content", ""),
                "created_at": latest_comment.get("created_at", datetime.now())
            }
        return None

    # Compare comment counts
    if len(comments) > len(previous_comments):
        # New comment added
        latest_comment = comments[-1]
        return {
            "author": latest_comment.get("author", "Anonymous"),
            "author_email": latest_comment.get("author_email", ""),
            "content": latest_comment.get("content", ""),
            "created_at": latest_comment.get("created_at", datetime.now())
        }

    return None


async def send_comment_notification(
    recipient_email: EmailStr,
    recipient_name: str,
    note_title: str,
    note_id: str,
    commenter_name: str,
    comment_content: str
) -> bool:
    """
    Send email notification for a new comment.

    Args:
        recipient_email: Email of the note author
        recipient_name: Name of the note author
        note_title: Title of the note
        note_id: ID of the note
        commenter_name: Name of the person who commented
        comment_content: Content of the comment

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Create HTML email body
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                    <h2 style="color: #4A5568; border-bottom: 2px solid #4A5568; padding-bottom: 10px;">
                        New Comment on Your Note
                    </h2>
                    <p>Hi <strong>{recipient_name}</strong>,</p>
                    <p><strong>{commenter_name}</strong> has commented on your note: <strong>"{note_title}"</strong></p>

                    <div style="background-color: #F7FAFC; padding: 15px; border-left: 4px solid #4299E1; margin: 20px 0;">
                        <p style="margin: 0; font-style: italic;">"{comment_content}"</p>
                    </div>

                    <p style="margin-top: 20px;">
                        <a href="https://your-app-url.com/notes/{note_id}"
                           style="display: inline-block; padding: 10px 20px; background-color: #4299E1; color: white;
                                  text-decoration: none; border-radius: 5px;">
                            View Comment
                        </a>
                    </p>

                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #E2E8F0;">

                    <p style="font-size: 12px; color: #718096;">
                        You're receiving this email because you have comment notifications enabled for your notes.
                        You can manage your notification settings in your account preferences.
                    </p>
                </div>
            </body>
        </html>
        """

        message = MessageSchema(
            subject=f"New comment on '{note_title}'",
            recipients=[recipient_email],
            body=html_body,
            subtype=MessageType.html
        )

        await fast_mail.send_message(message)
        print(f"✓ Comment notification sent to {recipient_email} for note '{note_title}'")
        return True

    except Exception as e:
        print(f"✗ Failed to send comment notification: {str(e)}")
        return False


def on_comment_snapshot(doc_snapshot, changes, read_time):
    """
    Callback function for Firestore snapshot listener on 'comments' field.

    This function is triggered whenever the 'comments' field changes in any
    document in the 'notes' collection.

    Args:
        doc_snapshot: List of document snapshots
        changes: List of document changes
        read_time: Timestamp of the read operation
    """
    import asyncio

    for change in changes:
        if change.type.name in ['ADDED', 'MODIFIED']:
            doc = change.document
            data = doc.to_dict()

            if not data:
                continue

            # Extract note information
            note_id = doc.id
            note_title = data.get("title", "Untitled Note")
            author_email = data.get("author_email")
            author_name = data.get("author_name", "User")
            comments = data.get("comments", [])

            # Check if author has email and comments exist
            if not author_email or not comments:
                continue

            # Get the latest comment
            latest_comment = comments[-1] if comments else None
            if not latest_comment:
                continue

            # Extract comment details
            commenter_name = latest_comment.get("author", "Anonymous")
            commenter_email = latest_comment.get("author_email", "")
            comment_content = latest_comment.get("content", "")

            # Don't send notification if the author commented on their own note
            if commenter_email == author_email:
                continue

            # Check if author has comment notifications enabled
            # This would require fetching user settings from a users collection
            # For now, we'll assume notifications are enabled

            # Send notification asynchronously
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            loop.run_until_complete(
                send_comment_notification(
                    recipient_email=author_email,
                    recipient_name=author_name,
                    note_title=note_title,
                    note_id=note_id,
                    commenter_name=commenter_name,
                    comment_content=comment_content
                )
            )


def start_comment_notification_listener(db):
    """
    Start listening to changes in the 'comments' field of the 'notes' collection.

    Args:
        db: Firestore database client

    Returns:
        The snapshot listener object (can be used to stop listening)
    """
    notes_ref = db.collection("notes")

    # Create a snapshot listener
    listener = notes_ref.on_snapshot(on_comment_snapshot)

    print("✓ Comment notification listener started")
    return listener


def stop_comment_notification_listener(listener):
    """
    Stop the comment notification listener.

    Args:
        listener: The snapshot listener object returned by start_comment_notification_listener
    """
    if listener:
        listener.unsubscribe()
        print("✓ Comment notification listener stopped")


# For testing purposes
if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from firestore import db

    print("Starting comment notification emailer...")
    listener = start_comment_notification_listener(db)

    try:
        print("Listening for comment changes... Press Ctrl+C to stop.")
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping listener...")
        stop_comment_notification_listener(listener)
        print("Listener stopped.")

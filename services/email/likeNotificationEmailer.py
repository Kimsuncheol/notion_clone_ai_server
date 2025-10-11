"""
Like Notification Emailer Service

This module monitors the 'notes' collection in Firebase Firestore for changes
to the 'likeUsers' field and sends email notifications to note authors when
new likes are received.
"""

import os
from typing import Optional, Dict, Any, List
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


def _extract_new_like_info(like_users: List[Dict], previous_like_users: Optional[List[Dict]] = None) -> Optional[Dict[str, Any]]:
    """
    Extract new like information by comparing current and previous like users.

    Args:
        like_users: Current list of like users
        previous_like_users: Previous list of like users

    Returns:
        Dictionary with new like info or None if no new like
    """
    if not like_users:
        return None

    # If no previous likes, the last like is new
    if not previous_like_users:
        latest_like = like_users[-1] if like_users else None
        if latest_like:
            return {
                "user_id": latest_like.get("id", ""),
                "uid": latest_like.get("uid", ""),
                "email": latest_like.get("email", ""),
                "display_name": latest_like.get("display_name", "Anonymous"),
                "photo_url": latest_like.get("photo_url", ""),
                "joined_at": latest_like.get("joined_at", datetime.now())
            }
        return None

    # Compare like counts
    if len(like_users) > len(previous_like_users):
        # New like added - get the most recent one
        latest_like = like_users[-1]
        return {
            "user_id": latest_like.get("id", ""),
            "uid": latest_like.get("uid", ""),
            "email": latest_like.get("email", ""),
            "display_name": latest_like.get("display_name", "Anonymous"),
            "photo_url": latest_like.get("photo_url", ""),
            "joined_at": latest_like.get("joined_at", datetime.now())
        }

    return None


async def send_like_notification(
    recipient_email: EmailStr,
    recipient_name: str,
    note_title: str,
    note_id: str,
    liker_name: str,
    liker_email: str,
    total_likes: int
) -> bool:
    """
    Send email notification for a new like.

    Args:
        recipient_email: Email of the note author
        recipient_name: Name of the note author
        note_title: Title of the note
        note_id: ID of the note
        liker_name: Name of the person who liked
        liker_email: Email of the person who liked
        total_likes: Total number of likes on the note

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Create HTML email body
        likes_text = "like" if total_likes == 1 else "likes"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                    <h2 style="color: #4A5568; border-bottom: 2px solid #4A5568; padding-bottom: 10px;">
                        Someone Liked Your Note! 👍
                    </h2>
                    <p>Hi <strong>{recipient_name}</strong>,</p>
                    <p><strong>{liker_name}</strong> liked your note: <strong>"{note_title}"</strong></p>

                    <div style="background-color: #F0FFF4; padding: 15px; border-left: 4px solid #48BB78; margin: 20px 0; text-align: center;">
                        <p style="margin: 0; font-size: 18px; color: #2D3748;">
                            <strong>🎉 {total_likes} {likes_text}</strong> on this note
                        </p>
                    </div>

                    <p style="margin-top: 20px;">
                        <a href="https://your-app-url.com/notes/{note_id}"
                           style="display: inline-block; padding: 10px 20px; background-color: #48BB78; color: white;
                                  text-decoration: none; border-radius: 5px;">
                            View Your Note
                        </a>
                    </p>

                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #E2E8F0;">

                    <p style="font-size: 12px; color: #718096;">
                        You're receiving this email because you have like notifications enabled for your notes.
                        You can manage your notification settings in your account preferences.
                    </p>
                </div>
            </body>
        </html>
        """

        message = MessageSchema(
            subject=f"🎉 {liker_name} liked your note: '{note_title}'",
            recipients=[recipient_email],
            body=html_body,
            subtype=MessageType.html
        )

        await fast_mail.send_message(message)
        print(f"✓ Like notification sent to {recipient_email} for note '{note_title}'")
        return True

    except Exception as e:
        print(f"✗ Failed to send like notification: {str(e)}")
        return False


def on_like_snapshot(doc_snapshot, changes, read_time):
    """
    Callback function for Firestore snapshot listener on 'likeUsers' field.

    This function is triggered whenever the 'likeUsers' field changes in any
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
            like_users = data.get("like_users", []) or data.get("likeUsers", [])
            like_count = data.get("like_count", 0) or data.get("likeCount", 0)

            # Check if author has email and likes exist
            if not author_email or not like_users:
                continue

            # Get the latest like user
            latest_like_user = like_users[-1] if like_users else None
            if not latest_like_user:
                continue

            # Extract like user details
            liker_name = latest_like_user.get("display_name") or latest_like_user.get("displayName", "Anonymous")
            liker_email = latest_like_user.get("email", "")
            liker_uid = latest_like_user.get("uid", "")

            # Don't send notification if the author liked their own note
            if liker_email == author_email or liker_uid == data.get("author_id"):
                continue

            # Check if author has like notifications enabled
            # This would require fetching user settings from a users collection
            # For now, we'll assume notifications are enabled

            # Use like_count if available, otherwise use length of like_users array
            total_likes = like_count if like_count > 0 else len(like_users)

            # Send notification asynchronously
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            loop.run_until_complete(
                send_like_notification(
                    recipient_email=author_email,
                    recipient_name=author_name,
                    note_title=note_title,
                    note_id=note_id,
                    liker_name=liker_name,
                    liker_email=liker_email,
                    total_likes=total_likes
                )
            )


def start_like_notification_listener(db):
    """
    Start listening to changes in the 'likeUsers' field of the 'notes' collection.

    Args:
        db: Firestore database client

    Returns:
        The snapshot listener object (can be used to stop listening)
    """
    notes_ref = db.collection("notes")

    # Create a snapshot listener
    listener = notes_ref.on_snapshot(on_like_snapshot)

    print("✓ Like notification listener started")
    return listener


def stop_like_notification_listener(listener):
    """
    Stop the like notification listener.

    Args:
        listener: The snapshot listener object returned by start_like_notification_listener
    """
    if listener:
        listener.unsubscribe()
        print("✓ Like notification listener stopped")


# For testing purposes
if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from firestore import db

    print("Starting like notification emailer...")
    listener = start_like_notification_listener(db)

    try:
        print("Listening for like changes... Press Ctrl+C to stop.")
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping listener...")
        stop_like_notification_listener(listener)
        print("Listener stopped.")

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from twilio.rest import Client
import os
import re
from typing import Dict, Any
from app.models import WhatsAppMessage, MessageStatus
from app.repositories.user import UserRepository
from app.core.processing import handle_analysis_request
from app.services.google_drive import GoogleDriveManager
from app.repositories.scheduler import SchedulerService
from uuid import uuid4

router = APIRouter()
drive_manager = GoogleDriveManager()
client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))

def normalize_whatsapp_number(raw_number: str) -> str:
    """Convert to E.164 format without 'whatsapp:' prefix"""
    cleaned = re.sub(r"[^+0-9]", "", raw_number.replace('whatsapp:', ''))
    return f"+{cleaned.lstrip('+')}"  # Ensure leading +

def format_response(result: Dict[str, Any]) -> str:
    """Convert analysis result to clean WhatsApp message with titles and links"""
    if result.get('status') != 'success':
        return "❌ Analysis failed. Please try again."

    response = []
    
    # Single video analysis
    if result.get('type') == 'single':
        title = result.get('metadata', {}).get('title', 'Your Video Analysis')
        response.append(f"*{title}*")
        
        # For single video analysis, we might not have drive_links
        # Instead, use file_path from metadata or content preview
        file_path = result.get('metadata', {}).get('file_path', '')
        if file_path:
            response.append(f"Analysis saved to: {file_path}")
        elif 'content' in result:
            # Add a preview of the content
            preview = result['content'][:200] + "..." if len(result['content']) > 200 else result['content']
            response.append(f"Analysis: {preview}")
        else:
            response.append("Analysis complete.")
    
    # Batch analysis - keep existing code for completeness
    elif result.get('type') == 'batch' and 'drive_links' in result:
        response.append("*Batch Analysis Results*")
        for summary in result['drive_links'].get('summaries', []):
            if isinstance(summary, dict) and 'title' in summary and 'link' in summary:
                response.append(f"- {summary['title']}: {summary['link']}")
            elif isinstance(summary, str):
                response.append(f"- {summary}")
        
        if 'final_report' in result['drive_links']:
            final_report = result['drive_links']['final_report']
            if isinstance(final_report, dict) and 'link' in final_report:
                response.append(f"\nFinal Report: {final_report['link']}")
            elif isinstance(final_report, str):
                response.append(f"\nFinal Report: {final_report}")
    
    # Scheduled jobs
    elif result.get('scheduled'):
        response.append(f"✅ Scheduled: {result.get('next_run', '')}")
    
    # Fallback for any other result type
    else:
        # Add a simple success message with any available info
        if 'content' in result:
            preview = result['content'][:200] + "..." if len(result['content']) > 200 else result['content']
            response.append(f"Analysis complete. Preview: {preview}")
        else:
            response.append("Analysis complete.")

    return "\n".join(response)

async def send_whatsapp_message(user_number: str, message: str):
    """Send message to user with error handling"""
    try:
        client.messages.create(
            body=message,
            from_=os.getenv('TWILIO_WHATSAPP_NUMBER'),
            to=f"whatsapp:{user_number}"
        )
    except Exception as e:
        print(f"Failed to send WhatsApp message: {str(e)}")

async def process_whatsapp_analysis(user_id: str, user_number: str, message: str, inbound_msg_id: str):
    """Background task to handle analysis and send result"""
    with UserRepository() as repo:
        try:
            # Process analysis
            result = handle_analysis_request({
                "text": message,
                "user_id": user_id,
                "platform": "whatsapp"
            })
            
            # Format response
            response_text = format_response(result)
            
            # Save outgoing message - without any context field
            outgoing_msg = WhatsAppMessage(
                user_id=user_id,
                direction='outbound',
                body=response_text,
                status=MessageStatus.SENT
            )
            repo.db.add(outgoing_msg)
            repo.db.commit()
            
            # Send response
            await send_whatsapp_message(user_number, response_text)

        except Exception as e:
            error_msg = f"⚠️ Analysis failed: {str(e)}"
            print(f"Analysis error: {str(e)}")
            
            # Save error message - without any context field
            outgoing_msg = WhatsAppMessage(
                user_id=user_id,
                direction='outbound',
                body=error_msg,
                status=MessageStatus.FAILED
            )
            repo.db.add(outgoing_msg)
            repo.db.commit()
            
            # Send error notification
            await send_whatsapp_message(user_number, error_msg)

@router.post("/webhook")
async def handle_whatsapp(request: Request, background_tasks: BackgroundTasks):
    form_data = await request.form()
    raw_number = form_data.get('From', '')
    message_body = form_data.get('Body', '').strip()
    
    # try:
    user_number = normalize_whatsapp_number(raw_number)
    
    with UserRepository() as repo:
        user = repo.get_or_create_user(user_number)
        
        # Save incoming message
        incoming_msg = WhatsAppMessage(
            user_id=user.id,
            direction='inbound',
            body=message_body,
            status=MessageStatus.RECEIVED
        )
        repo.db.add(incoming_msg)
        repo.db.commit()
        
        # Queue background task
        background_tasks.add_task(
            process_whatsapp_analysis,
            user.id,
            user_number,
            message_body,
            str(incoming_msg.id)
        )
        
        return {"status": "processing", "message": "Analysis started"}
            
    # except Exception as e:
    #     error_msg = "⚠️ Initial processing failed. Please try again."
    #     print(f"Webhook error: {str(e)}")
    #     await send_whatsapp_message(user_number, error_msg)
    #     raise HTTPException(status_code=500, detail=str(e))



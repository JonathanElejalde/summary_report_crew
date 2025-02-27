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
    if not isinstance(result, dict):
        return "❌ Invalid analysis result format"
    
    if result.get('status') != 'success':
        return f"❌ Analysis failed: {result.get('error', 'Unknown error')}"

    response = []
    
    # Debug log to see what's in the result
    print(f"Formatting response with result: {result}")
    
    # Single video analysis
    if result.get('type') == 'single':
        metadata = result.get('metadata', {})
        title = metadata.get('title', 'Video Analysis')
        response.append(f"*{title}*")
        
        if 'drive_links' in result:
            response.extend(_format_drive_links(result['drive_links']))
        elif metadata.get('file_path'):
            response.append(f"📎 Analysis saved to: {metadata['file_path']}")
    
    # Batch analysis
    elif result.get('type') == 'batch':
        response.append("*Batch Analysis Results*")
        
        if 'drive_links' in result:
            print(f"Drive links found: {result['drive_links']}")
            # Check specifically for final_report
            if 'final_report' in result['drive_links'] and result['drive_links']['final_report']:
                print(f"Final report found: {result['drive_links']['final_report']}")
            else:
                print("No final_report found in drive_links")
            
            response.extend(_format_batch_links(result['drive_links']))
        else:
            print("No drive_links found in result")
        
        if 'statistics' in result:
            response.extend(_format_statistics(result['statistics']))
    
    # Scheduled analysis
    elif result.get('scheduled'):
        response.append("✅ Analysis scheduled")
        if 'next_run' in result:
            response.append(f"⏰ Next run: {result['next_run']}")
    
    # Unknown type fallback
    else:
        response.append("✅ Analysis complete")
    
    return "\n".join(response) if response else "✅ Analysis complete"

def _format_drive_links(drive_links: Dict[str, list]) -> list:
    """Format drive links for single video analysis"""
    formatted = []
    
    for summary in drive_links.get('summaries', []):
        if isinstance(summary, dict):
            # Add Google Docs indicator if applicable
            doc_type = "Google Doc" if summary.get('is_gdoc', False) else "Summary"
            formatted.append(f"📄 {doc_type}: {summary.get('link', 'N/A')}")
        elif isinstance(summary, str):
            formatted.append(f"📄 Summary: {summary}")
    
    for report in drive_links.get('reports', []):
        if isinstance(report, dict):
            # Add Google Docs indicator if applicable
            doc_type = "Google Doc" if report.get('is_gdoc', False) else "Report"
            formatted.append(f"📊 {doc_type}: {report.get('link', 'N/A')}")
        elif isinstance(report, str):
            formatted.append(f"📊 Report: {report}")
            
    return formatted

def _format_batch_links(drive_links: Dict[str, Any]) -> list:
    """Format drive links for batch analysis"""
    formatted = []
    
    # Handle final report FIRST - make it the most prominent
    final_report = drive_links.get('final_report')
    if final_report:
        formatted.append("\n🌟 *FINAL ANALYSIS:*")
        if isinstance(final_report, dict):
            formatted.append(f"👉 {final_report.get('link', 'N/A')}")
        elif isinstance(final_report, str):
            formatted.append(f"👉 {final_report}")
        
        # Add a separator
        formatted.append("\n-------------------")
    
    # Handle summaries
    summaries = drive_links.get('summaries', [])
    if summaries:
        formatted.append("\n📄 *Individual Summaries:*")
        for summary in summaries:
            if isinstance(summary, dict):
                formatted.append(f"- {summary.get('title', 'Analysis')}: {summary.get('link', 'N/A')}")
            elif isinstance(summary, str):
                formatted.append(f"- {summary}")
    
    # Handle reports
    reports = drive_links.get('reports', [])
    if reports:
        formatted.append("\n📊 *Individual Reports:*")
        for report in reports:
            if isinstance(report, dict):
                formatted.append(f"- {report.get('title', 'Analysis')}: {report.get('link', 'N/A')}")
            elif isinstance(report, str):
                formatted.append(f"- {report}")
    
    return formatted

def _format_statistics(stats: Dict[str, Any]) -> list:
    """Format batch statistics"""
    return [
        f"\n📈 Processed {stats.get('total_videos', 0)} videos",
        f"✅ Success rate: {stats.get('success_rate', 0)*100:.0f}%"
    ]

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
        raise  # Re-raise to handle in caller

async def process_whatsapp_analysis(user_id: str, user_number: str, message: str, inbound_msg_id: str):
    """Background task to handle analysis and send result"""
    with UserRepository() as repo:
        # Process analysis
        try:
            result = handle_analysis_request({
                "text": message,
                "user_id": user_id,
                "platform": "whatsapp"
            })
        except Exception as e:
            await _handle_analysis_error(repo, user_id, user_number, str(e))
            return

        # Format and send response
        try:
            response_text = format_response(result)
            await send_whatsapp_message(user_number, response_text)
            
            # Save successful message
            outgoing_msg = WhatsAppMessage(
                user_id=user_id,
                direction='outbound',
                body=response_text,
                status=MessageStatus.SENT
            )
            repo.db.add(outgoing_msg)
            repo.db.commit()
            
        except Exception as e:
            await _handle_analysis_error(repo, user_id, user_number, str(e))

async def _handle_analysis_error(repo: UserRepository, user_id: str, user_number: str, error: str):
    """Handle errors in analysis process"""
    error_msg = f"⚠️ Analysis failed: {error}"
    print(f"Analysis error: {error}")
    
    # Save error message
    outgoing_msg = WhatsAppMessage(
        user_id=user_id,
        direction='outbound',
        body=error_msg,
        status=MessageStatus.FAILED
    )
    repo.db.add(outgoing_msg)
    repo.db.commit()
    
    # Attempt to send error notification
    try:
        await send_whatsapp_message(user_number, error_msg)
    except Exception as e:
        print(f"Failed to send error message: {e}")

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



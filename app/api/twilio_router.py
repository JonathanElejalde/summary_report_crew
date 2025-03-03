from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from twilio.rest import Client
import os
import re
import requests
from typing import Dict, Any
from app.models import WhatsAppMessage, MessageStatus
from app.repositories.user import UserRepository
from app.core.processing import handle_analysis_request

router = APIRouter()
client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))


async def _handle_analysis_error(repo: UserRepository, user_id: str, user_number: str, error: str, inbound_msg_id: str = None):
    """Handle errors in analysis process"""
    error_msg = f"⚠️ Analysis failed: {error}"
    print(f"Analysis error: {error}")
    
    if inbound_msg_id:
        # Try to update the original message
        message_to_update = repo.db.get(WhatsAppMessage, inbound_msg_id)
        if message_to_update:
            message_to_update.agent_message = error_msg
            message_to_update.status = MessageStatus.FAILED
            repo.db.commit()
            
            # Attempt to send error notification
            try:
                await send_whatsapp_message(user_number, error_msg)
            except Exception as e:
                print(f"Failed to send error message: {e}")
            return
    
    # If we couldn't find the original message or no ID was provided, create a new one
    outgoing_msg = WhatsAppMessage(
        user_id=user_id,
        agent_message=error_msg,
        status=MessageStatus.FAILED
    )
    repo.db.add(outgoing_msg)
    repo.db.commit()
    
    # Attempt to send error notification
    try:
        await send_whatsapp_message(user_number, error_msg)
    except Exception as e:
        print(f"Failed to send error message: {e}")


def normalize_whatsapp_number(raw_number: str) -> str:
    """Convert to E.164 format without 'whatsapp:' prefix"""
    cleaned = re.sub(r"[^+0-9]", "", raw_number.replace('whatsapp:', ''))
    return f"+{cleaned.lstrip('+')}"  # Ensure leading +

async def send_whatsapp_message(user_number: str, message: str):
    """Send message to user with error handling"""
    try:
        # Check if message exceeds Twilio's 1600 character limit
        if len(message) > 1600:
            print(f"Message exceeds 1600 characters ({len(message)} chars), splitting into multiple messages")
            
            # Split message into chunks of 1500 characters (leaving room for continuation indicators)
            chunks = []
            current_chunk = ""
            
            # Split by newlines to avoid breaking in the middle of a line
            lines = message.split('\n')
            
            for line in lines:
                # If adding this line would exceed our chunk size
                if len(current_chunk) + len(line) + 1 > 1500:  # +1 for newline
                    # If current chunk is not empty, add it to chunks
                    if current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = line + '\n'
                    else:
                        # If the line itself is too long, we need to split it
                        if len(line) > 1500:
                            # Split the line at 1500 chars
                            chunks.append(line[:1500])
                            current_chunk = line[1500:] + '\n'
                        else:
                            current_chunk = line + '\n'
                else:
                    current_chunk += line + '\n'
            
            # Add the last chunk if not empty
            if current_chunk:
                chunks.append(current_chunk)
            
            # Send each chunk with a continuation indicator
            for i, chunk in enumerate(chunks):
                continuation = f"({i+1}/{len(chunks)})"
                if i < len(chunks) - 1:
                    chunk += f"\n{continuation}"
                else:
                    chunk += f"\n{continuation} End of message."
                
                client.messages.create(
                    body=chunk,
                    from_=os.getenv('TWILIO_WHATSAPP_NUMBER'),
                    to=f"whatsapp:{user_number}"
                )
        else:
            # Send as a single message if under the limit
            client.messages.create(
                body=message,
                from_=os.getenv('TWILIO_WHATSAPP_NUMBER'),
                to=f"whatsapp:{user_number}"
            )
    except Exception as e:
        print(f"Failed to send WhatsApp message: {str(e)}")
        raise  # Re-raise to handle in caller

def shorten_url(url: str) -> str:
    """Shorten a URL using TinyURL's API"""
    try:
        response = requests.get(f"https://tinyurl.com/api-create.php?url={url}", timeout=5)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Failed to shorten URL: {url}, status code: {response.status_code}")
            return url
    except Exception as e:
        print(f"Error shortening URL: {str(e)}")
        return url

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
            # Get formatted titles with shortened URLs
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
            
            # Get formatted titles with shortened URLs
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
    
    # Join all response elements
    full_response = "\n".join(response)
    
    return full_response if full_response else "✅ Analysis complete"

def _format_drive_links(drive_links: Dict[str, list]) -> list:
    """Format drive links for single video analysis"""
    formatted = []
    
    for summary in drive_links.get('summaries', []):
        if isinstance(summary, dict):
            # Extract title or use a shorter label
            title = summary.get('title', 'Summary')
            link = summary.get('link', 'N/A')
            
            # Truncate title if too long
            if title and len(title) > 30:
                title = title[:27] + "..."
                
            # Shorten the URL
            short_url = shorten_url(link) if link != 'N/A' else 'N/A'
            
            formatted.append(f"📄 *{title}*: {short_url}")
        elif isinstance(summary, str):
            # If it's just a string, assume it's a URL
            short_url = shorten_url(summary)
            formatted.append(f"📄 *Summary*: {short_url}")
    
    for report in drive_links.get('reports', []):
        if isinstance(report, dict):
            # Extract title or use a shorter label
            title = report.get('title', 'Report')
            link = report.get('link', 'N/A')
            
            # Truncate title if too long
            if title and len(title) > 30:
                title = title[:27] + "..."
                
            # Shorten the URL
            short_url = shorten_url(link) if link != 'N/A' else 'N/A'
            
            formatted.append(f"📊 *{title}*: {short_url}")
        elif isinstance(report, str):
            # If it's just a string, assume it's a URL
            short_url = shorten_url(report)
            formatted.append(f"📊 *Report*: {short_url}")
            
    return formatted

def _format_batch_links(drive_links: Dict[str, Any]) -> list:
    """Format drive links for batch analysis"""
    formatted = []
    
    # Handle final report FIRST - make it the most prominent
    final_report = drive_links.get('final_report')
    if final_report:
        formatted.append("\n🌟 *FINAL ANALYSIS*")
        if isinstance(final_report, dict):
            title = final_report.get('title', 'Final Report')
            link = final_report.get('link', 'N/A')
            
            # Truncate title if too long
            if title and len(title) > 30:
                title = title[:27] + "..."
                
            # Shorten the URL
            short_url = shorten_url(link) if link != 'N/A' else 'N/A'
            
            formatted.append(f"👉 *{title}*: {short_url}")
        elif isinstance(final_report, str):
            # If it's just a string, assume it's a URL
            short_url = shorten_url(final_report)
            formatted.append(f"👉 *Final Report*: {short_url}")
        
        # Add a separator
        formatted.append("\n-------------------")
    
    # Handle summaries
    summaries = drive_links.get('summaries', [])
    if summaries:
        formatted.append("\n📄 *Summaries:*")
        for i, summary in enumerate(summaries, 1):
            if isinstance(summary, dict):
                title = summary.get('title', f'Summary {i}')
                link = summary.get('link', 'N/A')
                
                # Truncate title if too long
                if title and len(title) > 30:
                    title = title[:27] + "..."
                    
                # Shorten the URL
                short_url = shorten_url(link) if link != 'N/A' else 'N/A'
                
                formatted.append(f"- *{title}*: {short_url}")
            elif isinstance(summary, str):
                # If it's just a string, assume it's a URL
                short_url = shorten_url(summary)
                formatted.append(f"- *Summary {i}*: {short_url}")
    
    # Handle reports
    reports = drive_links.get('reports', [])
    if reports:
        formatted.append("\n📊 *Reports:*")
        for i, report in enumerate(reports, 1):
            if isinstance(report, dict):
                title = report.get('title', f'Report {i}')
                link = report.get('link', 'N/A')
                
                # Truncate title if too long
                if title and len(title) > 30:
                    title = title[:27] + "..."
                    
                # Shorten the URL
                short_url = shorten_url(link) if link != 'N/A' else 'N/A'
                
                formatted.append(f"- *{title}*: {short_url}")
            elif isinstance(report, str):
                # If it's just a string, assume it's a URL
                short_url = shorten_url(report)
                formatted.append(f"- *Report {i}*: {short_url}")
    
    return formatted

def _format_statistics(stats: Dict[str, Any]) -> list:
    """Format batch statistics"""
    return [
        f"\n📈 Processed {stats.get('total_videos', 0)} videos",
        f"✅ Success rate: {stats.get('success_rate', 0)*100:.0f}%"
    ]

async def process_whatsapp_analysis(user_id: str, user_number: str, message: str, inbound_msg_id: str):
    """Background task to handle analysis and send result"""
    with UserRepository() as repo:
        # Process analysis
        try:
            result = handle_analysis_request(message, user_id=user_id, message_id=inbound_msg_id)
        except Exception as e:
            await _handle_analysis_error(repo, user_id, user_number, str(e), inbound_msg_id)
            return

        # Format and send response
        try:
            response_text = format_response(result)
            await send_whatsapp_message(user_number, response_text)
            
            # Get the message by ID and update it with the agent's response
            message_to_update = repo.db.get(WhatsAppMessage, inbound_msg_id)
            if message_to_update:
                message_to_update.agent_message = response_text
                message_to_update.status = MessageStatus.SENT
                repo.db.commit()
            else:
                # Fallback in case the message can't be found
                print(f"Warning: Could not find message with ID {inbound_msg_id}")
                new_msg = WhatsAppMessage(
                    user_id=user_id,
                    agent_message=response_text,
                    status=MessageStatus.SENT
                )
                repo.db.add(new_msg)
                repo.db.commit()
            
        except Exception as e:
            await _handle_analysis_error(repo, user_id, user_number, str(e), inbound_msg_id)


@router.post("/webhook")
async def handle_whatsapp(request: Request, background_tasks: BackgroundTasks):
    form_data = await request.form()
    raw_number = form_data.get('From', '')
    message_body = form_data.get('Body', '').strip()
    
    user_number = normalize_whatsapp_number(raw_number)
    
    with UserRepository() as repo:
        user = repo.get_or_create_user(user_number)
        
        # Save incoming message
        incoming_msg = WhatsAppMessage(
            user_id=user.id,
            user_message=message_body,
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
            
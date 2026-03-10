"""
Notification service for email and Slack alerts
"""
import smtplib
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import structlog

from config import get_settings
from db.schemas import RiskAnalysisResult

logger = structlog.get_logger()


class NotificationService:
    def __init__(self):
        self.settings = get_settings()
        self.smtp_configured = all([
            self.settings.smtp_host,
            self.settings.smtp_user,
            self.settings.smtp_password
        ])
        self.slack_configured = bool(self.settings.slack_webhook_url)
    
    async def send_high_risk_alert(
        self,
        result: RiskAnalysisResult,
        pr_id: int,
        repository_name: str,
        pr_title: str,
        recipients: List[str],
        pr_url: Optional[str] = None
    ):
        """Send alerts for high-risk PRs via email and Slack"""
        
        if result.risk_level not in ["high", "critical"]:
            logger.debug("skipping_notification_low_risk", risk_level=result.risk_level)
            return
        
        logger.info("sending_high_risk_alert",
                    pr_id=pr_id,
                    risk_level=result.risk_level,
                    risk_score=result.risk_score)
        
        # Send email notification
        if self.smtp_configured and recipients:
            try:
                await self._send_email_alert(
                    result=result,
                    pr_id=pr_id,
                    repository_name=repository_name,
                    pr_title=pr_title,
                    recipients=recipients,
                    pr_url=pr_url
                )
            except Exception as e:
                logger.error("email_notification_failed", error=str(e))
        
        # Send Slack notification
        if self.slack_configured:
            try:
                await self._send_slack_alert(
                    result=result,
                    pr_id=pr_id,
                    repository_name=repository_name,
                    pr_title=pr_title,
                    pr_url=pr_url
                )
            except Exception as e:
                logger.error("slack_notification_failed", error=str(e))
    
    async def _send_email_alert(
        self,
        result: RiskAnalysisResult,
        pr_id: int,
        repository_name: str,
        pr_title: str,
        recipients: List[str],
        pr_url: Optional[str]
    ):
        """Send email notification for high-risk PR"""
        
        emoji = {"high": "🔴", "critical": "⛔", "medium": "🟡"}.get(result.risk_level, "🟢")
        
        subject = f"{emoji} High Risk Deployment Alert - PR #{pr_id} in {repository_name}"
        
        # Build HTML email body
        signals_html = "\n".join([
            f"<li><strong>{s.name}</strong>: {s.score:.1f} points - {s.description}</li>"
            for s in result.signals
        ])
        
        recommendations_html = "\n".join([
            f"<li>{rec}</li>"
            for rec in result.recommendations
        ])
        
        html_body = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                    .header {{ background: #ef4444; color: white; padding: 20px; }}
                    .content {{ padding: 20px; }}
                    .risk-score {{ font-size: 24px; font-weight: bold; color: #ef4444; }}
                    .section {{ margin: 20px 0; }}
                    ul {{ padding-left: 20px; }}
                    .footer {{ color: #666; font-size: 12px; margin-top: 30px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{emoji} DeployGuard High Risk Alert</h1>
                </div>
                <div class="content">
                    <div class="section">
                        <h2>Pull Request Details</h2>
                        <p><strong>Repository:</strong> {repository_name}</p>
                        <p><strong>PR #{pr_id}:</strong> {pr_title}</p>
                        {f'<p><a href="{pr_url}">View Pull Request</a></p>' if pr_url else ''}
                    </div>
                    
                    <div class="section">
                        <h2>Risk Assessment</h2>
                        <p><span class="risk-score">{result.risk_score:.1f} / 10</span> - {result.risk_level.upper()} RISK</p>
                    </div>
                    
                    <div class="section">
                        <h2>Risk Signals Detected</h2>
                        <ul>
                            {signals_html}
                        </ul>
                    </div>
                    
                    <div class="section">
                        <h2>Recommendations</h2>
                        <ul>
                            {recommendations_html}
                        </ul>
                    </div>
                    
                    <div class="footer">
                        <p>This is an automated alert from DeployGuard. Please review this PR carefully before merging.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.settings.smtp_user
        msg['To'] = ', '.join(recipients)
        
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
            server.starttls()
            server.login(self.settings.smtp_user, self.settings.smtp_password)
            server.send_message(msg)
        
        logger.info("email_alert_sent", pr_id=pr_id, recipients=recipients)
    
    async def _send_slack_alert(
        self,
        result: RiskAnalysisResult,
        pr_id: int,
        repository_name: str,
        pr_title: str,
        pr_url: Optional[str]
    ):
        """Send Slack notification for high-risk PR"""
        
        emoji = {"high": ":red_circle:", "critical": ":no_entry:", "medium": ":large_yellow_circle:"}.get(result.risk_level, ":white_check_mark:")
        
        color = {"high": "#ef4444", "critical": "#dc2626", "medium": "#f59e0b"}.get(result.risk_level, "#10b981")
        
        signals_text = "\n".join([
            f"• *{s.name}*: {s.score:.1f} points - {s.description}"
            for s in result.signals
        ])
        
        payload = {
            "text": f"{emoji} *High Risk Deployment Alert*",
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"{emoji} High Risk PR Detected"
                            }
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Repository:*\n{repository_name}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*PR:*\n#{pr_id}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Risk Score:*\n{result.risk_score:.1f} / 10"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Risk Level:*\n{result.risk_level.upper()}"
                                }
                            ]
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*PR Title:*\n{pr_title}"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Risk Signals:*\n{signals_text}"
                            }
                        }
                    ]
                }
            ]
        }
        
        if pr_url:
            payload["attachments"][0]["blocks"].append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Pull Request"
                        },
                        "url": pr_url,
                        "style": "danger"
                    }
                ]
            })
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.settings.slack_webhook_url,
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
        
        logger.info("slack_alert_sent", pr_id=pr_id)

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.certs.certificate_service import CertificateService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create scheduler instance
scheduler = AsyncIOScheduler()

def clean_pdfs_job():
    """Job to clean PDF files from temp directory."""
    try:
        certificate_service = CertificateService()
        certificate_service.clean_old_pdfs()
        logger.info("Daily PDF cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during PDF cleanup: {e}")

def start_scheduler():
    """Start the scheduler with all scheduled jobs."""
    # Schedule PDF cleanup at midnight (00:00) every day
    scheduler.add_job(
        clean_pdfs_job,
        trigger=CronTrigger(hour=0, minute=0),
        id='clean_pdfs_daily',
        name='Clean PDF files daily at midnight',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started - PDF cleanup scheduled for midnight daily")

def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shutdown complete")

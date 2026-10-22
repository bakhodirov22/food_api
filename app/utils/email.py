import time
import logging

logger = logging.getLogger(__name__)


def send_welcome_email(email: str, username: str):
    logger.info(f"Email yuborilmoqda: {email}")
    time.sleep(9)
    logger.info(f"Email yuborildi: {email} → {username}")


def send_order_notification(email: str, order_id: int):
    logger.info(f"Buyurtma bildirishi: {email} → order #{order_id}")
    time.sleep(1)
    logger.info("Bildirish yuborildi!")


def write_log(action: str, user_id: int, details: str = ""):
    logger.info(f"LOG: user={user_id} | action={action} | {details}")
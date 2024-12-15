import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Cấu hình logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Biến cấu hình
BOT_TOKEN = "PASTE YOUR BOTTOKEN FROM TELEGRAM"  # Thay thế bằng token thực tế của bạn
PATTERN_TESTFLIGHT_LINKS = r'https://testflight\.apple\.com/join/[a-zA-Z0-9]{8}'

async def check_testflight_status(link: str) -> bool:
    """Kiểm tra trạng thái của link TestFlight."""
    try:
        response = await asyncio.get_event_loop().run_in_executor(None, requests.get, link)
        soup = BeautifulSoup(response.text, 'html.parser')
        beta_status = soup.find('div', class_='beta-status')
        if beta_status:
            status_text = beta_status.text.strip()
            return "This beta is full" not in status_text  # Trả về True nếu có slot trống
        return False
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái TestFlight: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /start."""
    await update.message.reply_text("Xin chào! Sử dụng /theodoi để theo dõi một link TestFlight.")

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /check."""
    await update.message.reply_text("Vui lòng gửi link TestFlight bạn muốn theo dõi.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý link TestFlight người dùng gửi."""
    link = update.message.text
    await update.message.reply_text("Đang kiểm tra link TestFlight...")
    
    try:
        status = await check_testflight_status(link)
        if status:
            await update.message.reply_text(f"TestFlight beta có slot trống! Hãy nhanh tay đăng ký: {link}")
        else:
            await update.message.reply_text("Hiện tại beta này đã đầy. Bot sẽ tiếp tục theo dõi và thông báo khi có slot trống.")
            context.job_queue.run_repeating(
                check_and_notify,
                interval=300,
                first=10,
                data={'link': link, 'chat_id': update.effective_chat.id}
            )
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra link: {e}")
        await update.message.reply_text("Có lỗi xảy ra khi kiểm tra link. Vui lòng thử lại sau.")

async def check_and_notify(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kiểm tra định kỳ trạng thái của link TestFlight."""
    job = context.job
    link = job.data.get('link')
    chat_id = job.data.get('chat_id')
    
    if not link or not chat_id:
        logger.error("Thiếu link hoặc chat_id trong dữ liệu job")
        return

    try:
        status = await check_testflight_status(link)
        if status:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"TestFlight beta hiện đang có slot trống! Hãy nhanh tay đăng ký: {link}"
            )
            job.schedule_removal()  # Xóa job sau khi thông báo thành công
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái TestFlight: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lỗi."""
    logger.error("Lỗi khi xử lý cập nhật:", exc_info=context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text("Đã xảy ra lỗi khi xử lý yêu cầu của bạn.")

def main() -> None:
    """Khởi động bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex(PATTERN_TESTFLIGHT_LINKS), handle_link))
    application.add_error_handler(error_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
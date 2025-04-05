import asyncio
from telethon import TelegramClient, events, errors
from telethon.tl.types import Channel, User, Chat
import g4f
import random
from functools import partial
from concurrent.futures import TimeoutError
import sys
import signal
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Телеграм API-ключи
api_id = 27253387
api_hash = 'be38587d6486b296ed6e457088201771'

# ID канала для уведомлений о нарушениях
alert_channel_id = 2574801649

# Флаг для корректного завершения
running = True

def signal_handler(signum, frame):
    global running
    logger.info(f"Получен сигнал {signum}")
    running = False

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

client = TelegramClient(
    'anon', 
    api_id, 
    api_hash,
    device_model="Desktop",
    system_version="Windows 10",
    app_version="1.0",
    retry_delay=1,
    connection_retries=None,
    auto_reconnect=True
)

async def check_content_with_gpt(text):
    prompt = """Проанализируй следующий текст и определи, содержит ли он:
    1. Дискриминацию (расизм, сексизм, ксенофобию, нетерпимость, предвзятость, притеснение)
    2. Унижение (оскорбления, травля, буллинг, издевательства, моральное давление, харассмент)
    3. Шок-контент (жестокость, gore, расчленёнка, кровь, смерть, страдания)
    4. Насилие (агрессия, избиение, пытки, драки, убийства, угрозы)
    
    Ответь только Да или Нет. Если хотя бы один пункт присутствует, ответь Да.
    
    Текст: """
    
    try:
        # Создаем задачу для запроса к GPT
        gpt_task = asyncio.create_task(
            asyncio.to_thread(
                g4f.ChatCompletion.create,
                model=g4f.models.gpt_35_turbo,
                messages=[{"role": "user", "content": prompt + text}]
            )
        )
        
        # Ждем ответа максимум 60 секунд
        response = await asyncio.wait_for(gpt_task, timeout=60.0)
        print(f"🤖 Ответ GPT: {response}")
        return 'да' in response.lower() or 'yes' in response.lower()
        
    except (TimeoutError, asyncio.TimeoutError):
        print("⚠️ Превышен таймаут ожидания ответа GPT")
        return True  # Пересылаем сообщение при таймауте
    except Exception as e:
        print(f"⚠️ Ошибка GPT: {e}")
        return True  # Пересылаем сообщение при любой ошибке

@client.on(events.NewMessage())
async def handler(event):
    try:
        chat = await event.get_chat()
        
        # Проверяем, является ли источник каналом и не является ли комментарием
        if (not isinstance(chat, Channel) or 
            chat.id == alert_channel_id or 
            event.message.reply_to is not None):
            return
            
        # Выводим информацию о сообщении
        print("\n" + "="*50)
        print(f"📨 НОВЫЙ ПОСТ")
        print(f"Канал: {getattr(chat, 'title', 'Н/Д')}")
        print(f"ID канала: {chat.id}")
        print(f"Текст: {event.message.text[:200] if event.message.text else '[Нет текста]'}")
        print(f"Медиа: {'Да' if event.message.media else 'Нет'}")
        
        # Получаем только текст сообщения
        message_text = event.message.text or ''

        # Если текста нет или он короткий - игнорируем
        if not message_text or len(message_text) < 10:
            print("⏩ Сообщение пропущено (короткий текст или без текста)")
            return

        # Проверка текста через GPT
        print("🔄 Отправка в GPT...")
        is_violating = await check_content_with_gpt(message_text)
        
        if is_violating:
            await asyncio.sleep(random.uniform(2, 5))
            await client.forward_messages(alert_channel_id, event.message)
            print("❌ Сообщение переслано (нарушение/ошибка)")
            

            if random.random() < 0.4:
                try:
                    # Генерируем провокационный вопрос через GPT
                    prompt = f"""На основе этого текста сгенерируй один провокационный вопрос, 
                    который вызовет дискуссию. Вопрос должен быть кратким и спорным. Задавай вопрос на русском языке и в неформальном стиле. Задавай вопрос в грубой форме, оказывай давление на человека.
                    
                    Текст: {message_text}
                    """
                    
                    question_task = asyncio.create_task(
                        asyncio.to_thread(
                            g4f.ChatCompletion.create,
                            model=g4f.models.gpt_35_turbo,
                            messages=[{"role": "user", "content": prompt}]
                        )
                    )
                    
                    question = await asyncio.wait_for(question_task, timeout=80.0)
                    
                    # Отправляем вопрос с тегами
                    await client.send_message(
                        alert_channel_id,
                        f"@topbestb @aanastsok {question}"
                    )
                    print("✅ Отправлен провокационный вопрос с тегами")
                except Exception as e:
                    print(f"⚠️ Ошибка при генерации вопроса: {e}")
        else:
            print("✅ Проверка пройдена")
        print("="*50 + "\n")

    except Exception as e:
        print(f"⚠️ Ошибка обработки: {str(e)}")
        try:
            await client.forward_messages(alert_channel_id, event.message)
            print("✅ Сообщение переслано (ошибка)")
        except:
            pass
        await asyncio.sleep(1)

async def keep_alive():
    global running
    while running:
        try:
            if not client.is_connected():
                await client.connect()
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Ошибка в keep_alive: {e}")
            await asyncio.sleep(5)

async def main():
    global running
    try:
        logger.info("Запуск бота...")
        
        # Подключение и авторизация
        await client.connect()
        if not await client.is_user_authorized():
            logger.warning("Требуется авторизация!")
            await client.start()
        
        # Получаем информацию о юзерботе
        me = await client.get_me()
        logger.info(f"Бот запущен как: @{me.username if me.username else me.id}")
        
        print("\n" + "="*50)
        print("✅ Успешно подключено!")
        print("🔵 Бот запущен и слушает сообщения из каналов...")
        
        # Запускаем keep_alive в отдельной задаче
        keep_alive_task = asyncio.create_task(keep_alive())
        
        # Основной цикл работы
        while running:
            try:
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Ошибка в основном цикле: {e}")
                await asyncio.sleep(5)
                
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        running = False
        try:
            # Отменяем keep_alive
            keep_alive_task.cancel()
            await client.disconnect()
            logger.info("Соединение закрыто корректно")
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединения: {e}")

if __name__ == "__main__":
    try:
        # Запускаем бота в бесконечном цикле с автоперезапуском
        while True:
            try:
                asyncio.run(main())
                if not running:  # Если получен сигнал остановки
                    break
            except Exception as e:
                logger.critical(f"Фатальная ошибка: {e}")
                asyncio.sleep(5)  # Пауза перед перезапуском
    except KeyboardInterrupt:
        running = False
        print("\n⛔ Корректная остановка бота")

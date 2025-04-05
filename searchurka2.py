import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import Channel, User, Chat
import g4f
import random
from functools import partial
from concurrent.futures import TimeoutError

# Телеграм API-ключи
api_id = 27253387
api_hash = 'be38587d6486b296ed6e457088201771'

# ID канала для уведомлений о нарушениях
alert_channel_id = 2574801649

client = TelegramClient('anon', api_id, api_hash)

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

async def main():
    try:
        print("\n" + "="*50)
        print("🔵 Подключение к Telegram...")
        await client.start()
        
        # Получаем информацию о юзерботе
        me = await client.get_me()
        print("\n📱 Информация об аккаунте:")
        print(f"ID: {me.id}")
        print(f"Имя: {me.first_name}")
        print(f"Username: @{me.username if me.username else 'Отсутствует'}")
        print(f"Телефон: {me.phone if me.phone else 'Не указан'}")
        print(f"Премиум: {'Да' if me.premium else 'Нет'}")
        print("="*50 + "\n")
        
        print("✅ Успешно подключено!")
        print("🔵 Бот запущен и слушает сообщения из каналов...")
        
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        print("\n⚠️ Получен сигнал завершения...")
    except Exception as e:
        print(f"\n❌ Ошибка: {str(e)}")
    finally:
        print("🔄 Закрытие соединения...")
        await client.disconnect()
        print("✅ Бот остановлен")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⛔ Принудительная остановка бота")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {str(e)}")

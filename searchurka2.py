from telethon import TelegramClient, events
import asyncio

# Телеграм API-ключи
api_id = 27253387
api_hash = 'be38587d6486b296ed6e457088201771'
alert_channel_id = 2574801649

# Инициализация клиента
client = TelegramClient('anon', api_id, api_hash)

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    try:
        chat = await event.get_chat()
        
        # Пропускаем только сообщения из канала модерации и комментарии
        if chat.id == alert_channel_id or event.message.reply_to is not None:
            return
            
        # Выводим информацию о сообщении
        print("\n" + "="*50)
        print(f"📨 НОВЫЙ ПОСТ")
        print(f"Канал: {getattr(chat, 'title', 'Н/Д')}")
        print(f"ID канала: {chat.id}")
        print(f"Текст: {event.message.text[:200] if event.message.text else '[Нет текста]'}")
        print(f"Медиа: {'Да' if event.message.media else 'Нет'}")
        
        # Пересылаем сообщение
        await client.forward_messages(alert_channel_id, event.message)
        print("✅ Сообщение переслано")
        print("="*50 + "\n")

    except Exception as e:
        print(f"⚠️ Ошибка: {str(e)}")
        await asyncio.sleep(1)

async def main():
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
    print("🔵 Бот запущен и слушает сообщения...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
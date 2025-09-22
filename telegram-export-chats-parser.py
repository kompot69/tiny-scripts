import json
exept_None_chats=True
chats_min_msg=int(input('? minimum messages in chat: '))

chats_added,chats_skipped,msg_added,msg_skipped=0,0,0,0

def extract_text(text_field):
    """Преобразует поле text в обычную строку"""
    if isinstance(text_field, str):
        return text_field
    elif isinstance(text_field, list):
        result = ''
        for part in text_field:
            if isinstance(part, str):
                result += part
            elif isinstance(part, dict):
                part_text = part.get('text', '')
                if part.get('type') == 'text_link' and 'href' in part:
                    result += f"{part_text} {part['href']}"
                else:
                    result += part_text
        return result.strip()
    return ''

def simplify_json(data):
    simplified = {"chats_list": []}
    global chats_skipped, chats_added, msg_added, msg_skipped
    for chat in data.get("chats", {}).get("list", []):
        chat_id = chat.get("id")
        if exept_None_chats and chat.get("name") == None:
            print(f'skip chat with None ({chat_id})')
            chats_skipped+=1
            msg_skipped+=len(chat.get("messages", []))
            continue
        if len(chat.get("messages", [])) < chats_min_msg:
            print(f'skip chat with {chat.get("name")} ({chat_id}) bc msg={len(chat.get("messages", []))}')
            chats_skipped+=1
            msg_skipped+=len(chat.get("messages", []))
            continue
        role = input(f'роль для чата {chat_id} ({chat.get("name")}): ')
        new_chat = {"id": chat_id, "role": role, "messages": []}

        for msg in chat.get("messages", []):
            date = msg.get("date")
            from_id = msg.get("from_id")
            if from_id:
                if from_id.startswith('user'): from_id=from_id[4:]
            text = extract_text(msg.get("text", ''))
            attachment = None
            if msg.get("file_name"): attachment = 'file: '+msg.get("file_name")
            if msg.get("media_type"): attachment = msg.get("media_type")
            if msg.get("sticker_emoji"): attachment = 'sticker: '+msg.get("sticker_emoji")
            if msg.get("photo"): attachment = 'photo'
            if msg.get("action"): attachment = 'action: '+msg.get("action")
            new_chat["messages"].append({
                "date": date,
                "from_id": from_id,
                "attachment": attachment,
                "text": text
            })

        simplified["chats_list"].append(new_chat)
        chats_added+=1
        msg_added+=len(chat.get("messages", []))
    return simplified

# Загрузка, обработка и сохранение
with open('result.json', 'r', encoding='utf-8') as infile:
    original_data = json.load(infile)

simplified_data = simplify_json(original_data)
print(f'total chats: {chats_added+chats_skipped}, added: {chats_added}, skipped: {chats_skipped}')
print(f'total messages: {msg_added+msg_skipped}, added: {msg_added}, skipped: {msg_skipped}')

with open('output.json', 'w', encoding='utf-8') as outfile:
    json.dump(simplified_data, outfile, ensure_ascii=False, indent=2)

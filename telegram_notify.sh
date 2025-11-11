#!/bin/bash

BOT_TOKEN="1234567890:AAbbCCdd..." # токен бота
CHAT_ID="12345678" # ID пользователя / чата куда отправлять уведомления

if [ -z "$1" ]; then
    echo "Ошибка: не указан текст сообщения."
    echo "Использование: $0 \"Сообщение\""
    exit 1
fi

MESSAGE=$(printf "ℹ *$(hostname):*\n$1")
curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
     -d "chat_id=${CHAT_ID}" \
     -d "text=${MESSAGE}" \
     -d "parse_mode=Markdown" >/dev/null

if [ $? -eq 0 ]; then
    echo "$0: alert sended to $CHAT_ID"
else
    echo "$0: error sending alert to $CHAT_ID"
fi

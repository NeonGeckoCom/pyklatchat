const socket = io("http://127.0.0.1:8000");

socket.on('connect', () => {
     console.info('Connected to Server')
});

socket.on('user_message', (msg) => {
    const msgData = JSON.parse(msg);
    const targetChat = document.getElementById(msgData['chat_id']);
    if(targetChat){
        const targetChatBody = targetChat.getElementsByClassName('chatBody')[0]
        targetChatBody.insertAdjacentHTML('beforeend', `<p>${msgData['msg_text']}</p>`);
    }
});
function play(audio_data){
    const df = document.createDocumentFragment();
    const audio = new Audio("data:audio/wav;base64," + audio_data);
    df.appendChild(audio);
    audio.addEventListener('ended', function () {df.removeChild(snd);});
    audio.play().catch(err=> console.warn(`Failed to play audio_data = ${err}`));
}

function playTTS(cid, lang, audio_data){
    setChatState(cid, 'active');
    play(audio_data);
}

function getTTS(cid, message_id, lang, gender='female'){
    // TODO: consider multi-gender voices in future
    socket.emit('request_tts', {'cid':cid,
                                'user_id':currentUser['_id'],
                                'message_id':message_id,
                                'lang':lang});
}
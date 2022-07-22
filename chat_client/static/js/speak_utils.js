/**
 * Generic function to play base64 audio file (currently only .wav format is supported)
 * @param audio_data: base64 encoded audio data
 */
function play(audio_data){
    const df = document.createDocumentFragment();
    const audio = new Audio("data:audio/wav;base64," + audio_data);
    df.appendChild(audio);
    audio.addEventListener('ended', function () {df.removeChild(snd);});
    audio.play().catch(err=> console.warn(`Failed to play audio_data = ${err}`));
}

/**
 * Plays received TTS response
 * @param cid: target conversation id
 * @param lang: language of playing
 * @param audio_data: audio data to play
 */
function playTTS(cid, lang, audio_data){
    setChatState(cid, 'updating', 'Playing received audio');
    play(audio_data);
    setChatState(cid, 'active');
}

/**
 * Requests TTS for provider params
 * @param cid: target conversation id
 * @param message_id: target message id
 * @param lang: target language
 * @param gender: gender of speaker
 */
function getTTS(cid, message_id, lang, gender='female'){
    // TODO: consider multi-gender voices in future
    socket.emit('request_tts', {'cid':cid,
                                'user_id':currentUser['_id'],
                                'message_id':message_id,
                                'lang':lang});
}
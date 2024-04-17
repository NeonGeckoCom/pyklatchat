/**
 * Generic function to play base64 audio file (currently only .wav format is supported)
 * @param audio_data: base64 encoded audio data
 */
function play(audio_data){
    const df = document.createDocumentFragment();
    const audio = new Audio("data:audio/wav;base64," + audio_data);
    df.appendChild(audio);
    audio.addEventListener('ended', function () {df.removeChild(audio);});
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
 * Shows STT response of audio message
 * @param message_id: id of the audio message
 * @param lang: language of response (text is not shown if language differs from current preference)
 * @param message_text: message text to display
 */
function showSTT(message_id, lang, message_text){
    // TODO: skip showing text when preferred language changed
    // console.log(`showing: message_id=${message_id}, lang=${lang}, message_text=${message_text}`);
    const messageSTTContent = document.getElementById(`${message_id}-stt`);
    if(messageSTTContent && message_text){
        messageSTTContent.innerText = '"' + message_text + '"';
    }
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
    socket.emitAuthorized('request_tts', {'cid':cid,
                                'user_id':currentUser['_id'],
                                'message_id':message_id,
                                'lang':lang});
}


/**
 * Requests STT for provider message params
 * @param cid: target conversation id
 * @param message_id: target message id
 * @param lang: target language
 */
function getSTT(cid, message_id, lang){
    socket.emitAuthorized('request_stt', {'cid':cid,
                                'user_id':currentUser['_id'],
                                'message_id':message_id,
                                'lang':lang});
}

/**
 * Records audio from the client browser
 * @param cid: target conversation id
 * @return {Promise} recorder instance with following properties:
 * - start() to start recording
 * - stop() to end recording
 */
const recordAudio = (cid) => {
  return new Promise(resolve => {
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(stream => {
        const mediaRecorder = new MediaRecorder(stream);
        const audioChunks = [];

        mediaRecorder.addEventListener("dataavailable", event => {
          audioChunks.push(event.data);
        });

        const start = () => {
          mediaRecorder.start();
        };

        const stop = () => {
          return new Promise(resolve => {
            mediaRecorder.addEventListener("stop", () => {
              const audioBlob = new Blob(audioChunks, { 'type' : 'audio/wav; codecs=0' });
              const audioUrl = URL.createObjectURL(audioBlob);
              const audio = new Audio(audioUrl);
              const play = () => {
                audio.play();
              };

              resolve({ audioBlob, audioUrl, play });
            });

            mediaRecorder.stop();
          });
        };

        resolve({ start, stop });
      }).catch(err=>{
          const errMsg = err.toString();
          console.warn(`Starting audio recording failed with error - ${errMsg}`)
          const audioInput = document.getElementById(`${cid}-audio-input`);
          audioInput.disabled = true;
    });
  });
};

// Recorder instance
let recorder = null;


/**
 * Adds event listener for audio recording
 * @param conversationData: conversation data object
 */
async function addRecorder(conversationData) {

    const cid = conversationData["_id"];

    const recorderButton = document.getElementById(`${cid}-audio-input`);

    if (!recorderButton.disabled) {
        recorderButton.onmousedown = async function () {
            recorder = await recordAudio(cid);
            recorder.start();
        };

        recorderButton.onmouseup = async function () {
            if (recorder) {
                recorder.stop().then(audio => {
                    const audioBlob = toBase64(audio['audioBlob']);
                    console.log('audioBlob=', audioBlob);
                    return audioBlob;
                }).then(encodedAudio => {
                    emitUserMessage(encodedAudio, conversationData['_id'], null, [], '1', '0');
                });
            }
        };
    }
}

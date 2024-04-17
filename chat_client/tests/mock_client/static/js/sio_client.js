const eventLog = document.getElementById('eventLog');
const socket = io("http://127.0.0.1:8000");

socket.on('connect', () => {
     eventLog.insertAdjacentHTML('beforeend','<p>Connected to http://127.0.0.1:8000</p>')
});

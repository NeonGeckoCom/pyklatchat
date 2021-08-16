let configData = {
    'staticFolder':'../../static',
    'imageBaseFolder': '../../static/img',
    'cssBaseFolder': '../../static/css',
    'jsBaseFolder': '../../static/js',
    'currentURLBase': __extractURLBase(),
    'currentURLFull': window.location.href
};

const conversationAlignmentKey = 'conversationAlignment';

const configFullLoadedEvent = new CustomEvent("configLoaded", { "detail": "Event that is fired when configs are loaded" });

function __extractURLBase(){
    return window.location.protocol + '//' + window.location.hostname + (window.location.port?':'+window.location.port:'');
}

async function extractConfigData(filePath){
    return fetch(filePath).then(response => {
        if (response.ok){
            return response.json();
        }return  {};
    });
}

document.addEventListener('DOMContentLoaded', async (e)=>{
    configData = Object.assign(configData, await extractConfigData(configData['jsBaseFolder']+'/runtime_config.json'));
    document.dispatchEvent(configFullLoadedEvent);
});


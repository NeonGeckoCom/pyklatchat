/**
 * Collection of supported clients, current client is matched based on client configuration
 * @type {{NANO: string, MAIN: string}}
 */
const CLIENTS = {
    MAIN: 'main',
    NANO: 'nano'
}

/**
 * JS Object containing frontend configuration data
 * @type {{cssBaseFolder: string, staticFolder: string, currentURLBase: string, currentURLFull: (string|string|string|SVGAnimatedString|*), imageBaseFolder: string, jsBaseFolder: string, client: string}}
 */
let configData = {
    'staticFolder': "../../static",
    'currentURLBase': extractURLBase(),
    'currentURLFull': window.location.href,
    'client': CLIENTS.MAIN
};

/**
 * Default key for storing data in local storage
 * @type {string}
 */
const conversationAlignmentKey = 'conversationAlignment';

/**
 * Custom Event fired on configs ended up loading
 * @type {CustomEvent<string>}
 */
const configFullLoadedEvent = new CustomEvent("configLoaded", { "detail": "Event that is fired when configs are loaded" });

/**
 * Convenience method for getting URL base for current page
 * @returns {string} constructed URL base
 */
function extractURLBase(){
    return window.location.protocol + '//' + window.location.hostname + (window.location.port?':'+window.location.port:'');
}

/**
 * Extracts json data from provided file path
 * @param filePath: file path string
 * @returns {Promise<* | {}>} promise that resolves data obtained from file path
 */
async function extractJsonData(filePath=""){
    return fetch(filePath).then(response => {
        if (response.ok){
            return response.json();
        }return  {};
    });
}

document.addEventListener('DOMContentLoaded', async (e)=>{
    if (configData['client'] === CLIENTS.MAIN) {
        configData = Object.assign(configData, await extractJsonData(configData['staticFolder'] + '/runtime_config.json'));
        document.dispatchEvent(configFullLoadedEvent);
    }
});


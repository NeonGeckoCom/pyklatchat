const configNanoLoadedEvent = new CustomEvent("configNanoLoaded", { "detail": "Event that is fired when nano configs are loaded" });

/**
 * Single class that builds embeddable JS widget into the desired website
 */
class NanoBuilder {

    requiredProperties = ['CHAT_DATA', 'CHAT_SERVER_URL_BASE'];
    propertyHandlers = {
        'SOCKET_IO_SERVER_URL': this.resolveSIO,
        'CHAT_SERVER_URL_BASE': this.addConfig,
        'CHAT_CLIENT_URL_BASE': this.setClientURL,
        'PREFERENCES': this.resolvePreferences
    }
    /**
     * Constructing NanoBuilder instance
     * @param options: JS Object containing list of properties for built conversation
     */
    constructor(options) {
        /**
         * Attributes for options:
         * - CHAT_DATA: array of chat configs of type:
         *      {
         *           PARENT_ID: id of parent Node (required)
         *           CID: id of desired conversation (required)
         *      }
         * - SOCKET_IO_SERVER_URL: HTTP Endpoint of Socket IO Server
         * - CHAT_SERVER_URL_BASE: HTTP Endpoint for Klatchat Server
         * - CHAT_CLIENT_URL_BASE: HTTP Endpoint for Klatchat Client
         */
        this.options = options;
        this.options.SOCKET_IO_SERVER_URL = options.SOCKET_IO_SERVER_URL || options.CHAT_SERVER_URL_BASE;
        configData.client = CLIENTS.NANO;
        this.applyConfigs();
        // by default modals will be initialised under first nano chat
        const modalParentID = options?.MODALS_PARENT || options['CHAT_DATA'][0]['PARENT_ID'];
        fetchSupportedLanguages().then(async _ => await refreshCurrentUser(false))
                                 .then(_=>this.resolveChatData(this.options))
                                 .then(async _=> await requestChatsLanguageRefresh())
                                 .then(async _ =>await initModals(modalParentID));
    }

    /**
     * Applies configuration params based on declared handlers in "propertyHandlers"
     */
    applyConfigs(){
        this.requiredProperties.forEach(property => {
           if(!this.options.hasOwnProperty(property)){
               throw `${property} is required for NanoBuilder`;
           }
        });
        for (const [key, value] of Object.entries(this.options)) {
            if(this.propertyHandlers.hasOwnProperty(key)){
                const handler = this.propertyHandlers[key];
                if ([this.addConfig, this.setClientURL].includes(handler)){
                    handler(key, value);
                }
                else {
                    this.propertyHandlers[key](this.options);
                }
            }
        }
    }

    /**
     * Resolves nano conversation ID based on options
     * @param options: provided nano builder options
     */
    resolveChatData(options){
        const chatData = options['CHAT_DATA'];
        const nanoChatsLoaded = new CustomEvent('nanoChatsLoaded')
        Array.from(chatData).forEach(async chat => {
            await displayConversation(chat['CID'], CONVERSATION_SKINS.BASE, chat['PARENT_ID'], chat['PARENT_ID'])
        });
        console.log('all chats loaded')
        document.dispatchEvent(nanoChatsLoaded);
    }

    /**
     * Resolves SIO properties based on provided options
     * @param options: provided nano builder options
     */
    resolveSIO(options){
        configData['SOCKET_IO_SERVER_URL'] = options.SOCKET_IO_SERVER_URL;
        document.dispatchEvent(configNanoLoadedEvent);
    }

    /**
     * Adds config to configData
     * @param key: key to add
     * @param value: value to add under @param key
     */
    addConfig(key, value){
        configData[key] = value;
    }

    setClientURL(key, value){
        configData['currentURLBase'] = value;
    }

    /**
     * Resolves preferences from user options
     * @param options: provided nano builder options
     * */
    resolvePreferences(options){
        setDefault(currentUser, 'preferences', {})
        for (const [key, val] of Object.entries(options)){
            currentUser.preferences[key.toLowerCase()] = val.toLowerCase();
        }
    }
}

const initKlatChat = (options) => {
    document.addEventListener('DOMContentLoaded', (e)=>{
        return new NanoBuilder(options);
    })
};
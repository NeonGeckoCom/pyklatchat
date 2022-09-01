const configNanoLoadedEvent = new CustomEvent("configNanoLoaded", { "detail": "Event that is fired when nano configs are loaded" });

/**
 * Single class that builds embeddable JS widget into the desired website
 */
class NanoBuilder {

    requiredProperties = ['CHAT_DATA', 'SOCKET_IO_SERVER_URL', 'CHAT_SERVER_URL_BASE'];
    propertyHandlers = {
        'SOCKET_IO_SERVER_URL': this.resolveSIO,
        'CHAT_SERVER_URL_BASE': this.addConfig
    }
    /**
     * Constructing NanoBuilder instance
     * @param options: JS Object containing list of properties for built conversation
     */
    async constructor(options = {}) {
        /**
         * Attributes for options:
         * - parentID: id of parent Node (required)
         * - cid: id of desired conversation (required)
         */
        this.options = options;
        configData.client = CLIENTS.NANO;
        this.applyConfigs();
        await refreshCurrentUser(true, false);
        this.resolveChatData(this.options);
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
                if (handler === this.addConfig){
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
        Array.from(chatData).forEach(chat => {
            getConversationDataByInput(chat['CID']).then(async conversationData=>{
            if(conversationData) {
                await buildConversation(conversationData, false, chat['PARENT_ID']);
            }else{
                console.error(`No conversation found matching provided id: ${chat['CID']}`);
            }
        }).catch(err=> console.error(err));
        })
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
}
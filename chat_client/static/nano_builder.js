const configNanoLoadedEvent = new CustomEvent("configNanoLoaded", { "detail": "Event that is fired when nano configs are loaded" });

/**
 * Single class that builds embeddable JS widget into the desired website
 */
class NanoBuilder {

    requiredProperties = ['cid', 'imageBaseFolder', 'SOCKET_IO_SERVER_URL', 'CHAT_SERVER_URL_BASE'];
    propertyHandlers = {
        'SOCKET_IO_SERVER_URL': this.resolveSIO,
        'imageBaseFolder': this.addConfig,
        'CHAT_SERVER_URL_BASE': this.addConfig
    }
    /**
     * Constructing NanoBuilder instance
     * @param options: JS Object containing list of properties for built conversation
     */
    constructor(options = {}) {
        /**
         * Attributes for options:
         * - parentID: id of parent Node (required)
         * - cid: id of desired conversation (required)
         */
        this.options = options;
        configData.client = CLIENTS.NANO;
        this.applyConfigs();
        refreshCurrentUser(true, false);
        this.resolveCid(this.options);
    }

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

    resolveCid(options){
        const cid = options['cid'];
        getConversationDataByInput(cid).then(async conversationData=>{
            if(conversationData) {
                await buildConversation(conversationData, false, options?.parentID);
            }else{
                console.error(`No conversation found matching provided id: ${cid}`);
            }
        }).catch(err=> console.error(err));
    }

    resolveSIO(options){
        configData['SOCKET_IO_SERVER_URL'] = options.SOCKET_IO_SERVER_URL;
        document.dispatchEvent(configNanoLoadedEvent);
    }

    addConfig(key, value){
        configData[key] = value;
    }
}
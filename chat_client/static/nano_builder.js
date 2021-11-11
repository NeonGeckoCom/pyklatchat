/**
 * Single class that builds embeddable JS widget into the desired website
 */
class NanoBuilder {
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
        if(options?.cid){
            const cid = options.cid;
            getConversationDataByInput(cid).then(async conversationData=>{
                if(conversationData) {
                    await this.buildNanoConversation(conversationData);
                }else{
                    console.error(`No conversation found matching provided id: ${cid}`);
                }
            }).catch(err=> console.error(err));
        }
    }

    async buildNanoConversation(conversationData) {
        await buildConversation(conversationData, false, this.options?.parentID);
    }
}
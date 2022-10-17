/**
 * Renders suggestions HTML
 */
async function renderSuggestions() {
    await fetchServer(`chat_api/get_popular_cids?limit=5&search_str=${conversationSearchInput.value}`).then(async response => {
        const items = await response.json();
        importConversationModalSuggestions.innerHTML = "";
        for (const item of Array.from(items)) {
            importConversationModalSuggestions.insertAdjacentHTML('afterbegin', await buildSuggestionHTML(item['_id'], item['conversation_name']));
        }
        Array.from(importConversationModalSuggestions.getElementsByClassName('dropdown-item')).forEach(item => {
            const cid = item.getAttribute('data-cid')
            if (cid) {
                item.addEventListener('click', async (e) => {
                    conversationSearchInput.value = await displayConversation(cid);
                });
            }
        });
    });
}
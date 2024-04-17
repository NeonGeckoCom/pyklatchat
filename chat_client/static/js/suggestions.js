/**
 * Renders suggestions HTML
 */
async function renderSuggestions() {
    const displayedCids = Object.values(await retrieveItemsLayout(true)).join(',');
    await fetchServer(`chat_api/get_popular_cids?limit=5&search_str=${conversationSearchInput.value}&exclude_items=${displayedCids}`).then(async response => {
        const items = await response.json();
        importConversationModalSuggestions.innerHTML = "";
        for (const item of Array.from(items)) {
            importConversationModalSuggestions.insertAdjacentHTML('afterbegin', await buildSuggestionHTML(item['_id'], item['conversation_name']));
        }
        Array.from(importConversationModalSuggestions.getElementsByClassName('suggestion-item')).forEach(item => {
            const cid = item.getAttribute('data-cid');
            if (cid) {
                item.addEventListener('click', async (e) => {
                    await displayConversation(cid);
                    conversationSearchInput.value = "";
                    importConversationModal.modal('hide');
                    // importConversationModalSuggestions.innerHTML = "";
                });
                item.addEventListener('mouseover', (event) => {
                   item.classList.add('selected')
                });
                item.addEventListener('mouseleave', (event) => {
                   item.classList.remove('selected')
                });
            }
        });
        importConversationModalSuggestions.style.setProperty('display', 'inherit', 'important');
    });
}

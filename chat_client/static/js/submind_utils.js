let submindsPerCid;

// submindsPerCid = {
//         1: [
//             {submind_id: "wiz-1bbbd8af178a455eb65c669e72c89490", status: "active"},
//             {submind_id: "wolfram-b5003bfc25d7461e9888cfc344c04a85", status: "active"},
//         ]
//     }

function renderActiveSubminds(cid) {
    if (!submindsPerCid) {
        console.log(`Subminds for CID ${cid} not yet loaded.`);
        return;
    }
    const loadingSpinner = document.getElementById(`${cid}-subminds-state-loading`);
    if (loadingSpinner) {
        loadingSpinner.classList.remove('d-flex');
        loadingSpinner.style.display = 'none';
    }

    const dropdownMenu = document.getElementById(`bot-list-${cid}`);
    dropdownMenu.addEventListener('click', (event) => {
            event.stopPropagation();
        });

    const table = document.getElementById(`${cid}-subminds-state-table`);
    const entriesContainer = document.getElementById(`${cid}-subminds-state-entries`);
    const buttonsContainer = document.getElementById(`${cid}-subminds-buttons`);
    const resetButton = document.getElementById(`${cid}-reset-button`);
    const submitButton = document.getElementById(`${cid}-submit-button`);

    let initialState = (submindsPerCid?.[cid] || []).map(submind => ({
        id: submind.submind_id,
        active: submind.status === 'active',
    }));

    let currentState = structuredClone(initialState);

    const updateButtonVisibility = () => {
        const hasChanges = initialState.some((submind, index) => submind.active !== currentState[index].active);
        buttonsContainer.style.display = hasChanges ? 'block' : 'none';
    };

    table.style.display = '';
    entriesContainer.innerHTML = '';

    (submindsPerCid?.[cid] || []).forEach((submind, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${submind.submind_id.slice(0, submind.submind_id.lastIndexOf('-'))}</td>
            <td class="text-center">
                <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" id="toggle-${cid}-${submind.submind_id}" ${submind.status === 'active' ? 'checked' : ''}>
                    <label class="custom-control-label" for="toggle-${cid}-${submind.submind_id}"></label>
                </div>
            </td>
        `;

        const checkbox = row.querySelector(`#toggle-${cid}-${submind.submind_id}`);
        checkbox.addEventListener('change', () => {
            currentState[index].active = checkbox.checked;
            updateButtonVisibility();
        });
        entriesContainer.appendChild(row);
    });

    resetButton.onclick = () => {
        currentState = structuredClone(initialState);
        currentState.forEach((submind, index) => {
            const checkbox = document.getElementById(`toggle-${cid}-${submind.id}`);
            if (checkbox) checkbox.checked = submind.active;
        });
        updateButtonVisibility();
    };

    submitButton.onclick = () => {

        // function to apply changes for chat

        socket.emit('update_subminds', {cid: currentState});

        const dropdownToggle = document.getElementById(`dropdownToggle-${cid}`);
        if (dropdownToggle) dropdownToggle.click();

        buttonsContainer.style.display = 'none';
    };
}


async function parseSubmindsState(data){
    submindsPerCid = data['subminds_per_cid'];

    for (const cid of Object.keys(submindsPerCid)){
        refreshSubmindsCount(cid);
    }
}


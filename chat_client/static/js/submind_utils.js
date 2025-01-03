let subminds_state;

function renderActiveSubminds(cid) {
    if (!subminds_state) {
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
    buttonsContainer.style.display = 'none';
    const cancelButton = document.getElementById(`${cid}-reset-button`);
    const submitButton = document.getElementById(`${cid}-submit-button`);

    const active_subminds = subminds_state["subminds_per_cid"]?.[cid]?.filter(submind => submind.status === 'active') || [];
    const activeSubmindIds = new Set(active_subminds.map(submind => submind.submind_id));

    const banned_subminds = subminds_state["subminds_per_cid"]?.[cid]?.filter(submind => submind.status === 'banned') || [];
    const bannedSubmindIds = new Set(banned_subminds.map(submind => submind.submind_id));

    const initialSubmindsState = Object.entries(subminds_state?.["connected_subminds"] || {})
        .filter(([submind_id, submind]) => {
        return submind["bot_type"] === "submind" && !bannedSubmindIds.has(submind_id);
        })
        .map(([submind_id, submind]) => ({
        id: submind_id,
        is_active: activeSubmindIds.has(submind_id),
        }))
        .sort((a, b) => {
        return b.is_active - a.is_active;
        });

    let currentState = structuredClone(initialSubmindsState);

    const updateButtonVisibility = () => {
        const hasChanges = initialSubmindsState.some((submind, index) => submind.is_active !== currentState[index].is_active);
        buttonsContainer.style.display = hasChanges ? 'block' : 'none';
    };

    table.style.display = '';
    entriesContainer.innerHTML = '';

    initialSubmindsState.forEach((submind, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${submind.id.slice(0, submind.id.lastIndexOf('-'))}</td>
            <td class="text-center">
                <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" id="toggle-${cid}-${submind.id}" ${submind.is_active === true ? 'checked' : ''}>
                    <label class="custom-control-label" for="toggle-${cid}-${submind.id}"></label>
                </div>
            </td>
        `;

        const checkbox = row.querySelector(`#toggle-${cid}-${submind.id}`);
        checkbox.addEventListener('change', () => {
            currentState[index].is_active = checkbox.checked;
            updateButtonVisibility();
        });
        entriesContainer.appendChild(row);
    });

    cancelButton.onclick = () => {
        currentState = structuredClone(initialSubmindsState);
        currentState.forEach((submind, index) => {
            const checkbox = document.getElementById(`toggle-${cid}-${submind.id}`);
            checkbox.checked = (submind.is_active)? "checked" : '';
        });
        updateButtonVisibility();
    };

    submitButton.onclick = () => {
        const modifiedSubminds = currentState.filter((current, index) => {
            return current.is_active !== initialSubmindsState[index].is_active;
        });

        let subminds_to_remove = modifiedSubminds.filter(submind => !submind.is_active).map(submind => submind.id);
        let subminds_to_add = modifiedSubminds.filter(submind => submind.is_active).map(submind => submind.id);

        if (subminds_to_add.length !== 0){
            socket.emit('broadcast', {
                msg_type: "invite_subminds",
                "cid": cid,
                "requested_participants": subminds_to_add,
            });
        }

        if (subminds_to_remove.length !== 0) {
            socket.emit('broadcast', {
                msg_type: "remove_subminds",
                "cid": cid,
                "requested_participants": subminds_to_remove,
            });
        }

        const dropdownToggle = document.getElementById(`dropdownToggle-${cid}`);
        if (dropdownToggle) dropdownToggle.click();

        buttonsContainer.style.display = 'none';
    };
}


async function parseSubmindsState(data){
    subminds_state = data;

    const cids = Object.keys(subminds_state["subminds_per_cid"])
    if (cids.length === 0){
        setAllCountersToZero();
    } else {
        for (const cid of cids){
            refreshSubmindsCount(cid);
        }
    }
}


let submindsState;

function renderActiveSubminds(cid) {
    if (!submindsState) {
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

    const { subminds_per_cid: submindsPerCID, connected_subminds: connectedSubminds } = submindsState;

    const activeSubminds = submindsPerCID?.[cid]?.filter(submind => submind.status === 'active') || [];
    const activeSubmindServices = new Set(activeSubminds.map(submind => submind.submind_id.slice(0, submind.submind_id.lastIndexOf('-'))))

    const banned_subminds = submindsPerCID?.[cid]?.filter(submind => submind.status === 'banned') || [];
    const bannedSubmindIds = new Set(banned_subminds.map(submind => submind.submind_id));

    const initialSubmindsState = [];
    const processedServiceNames = [];
    for (let [submindID, submindData] of Object.entries(connectedSubminds || {})){
        const serviceName = submindData.service_name;
        const botType = submindData.bot_type;
        if (botType === "submind" && !bannedSubmindIds.has(submindID) && !processedServiceNames.includes(serviceName)){
            processedServiceNames.push(serviceName)
            initialSubmindsState.push(
                {
                    service_name: serviceName,
                    is_active: activeSubmindServices.has(serviceName)
                }
            )
        }
    }
    initialSubmindsState.sort((a, b) => {
        return b.is_active - a.is_active;
    })

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
            <td>${submind.service_name}</td>
            <td class="text-center">
                <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" id="toggle-${cid}-${submind.service_name}" ${submind.is_active === true ? 'checked' : ''}>
                    <label class="custom-control-label" for="toggle-${cid}-${submind.service_name}"></label>
                </div>
            </td>
        `;

        const checkbox = row.querySelector(`#toggle-${cid}-${submind.service_name}`);
        checkbox.addEventListener('change', () => {
            currentState[index].is_active = checkbox.checked;
            updateButtonVisibility();
        });
        entriesContainer.appendChild(row);
    });

    cancelButton.onclick = () => {
        currentState = structuredClone(initialSubmindsState);
        currentState.forEach((submind, index) => {
            const checkbox = document.getElementById(`toggle-${cid}-${submind.service_name}`);
            checkbox.checked = (submind.is_active)? "checked" : '';
        });
        updateButtonVisibility();
    };

    submitButton.onclick = () => {
        const modifiedSubminds = currentState.filter((current, index) => {
            return current.is_active !== initialSubmindsState[index].is_active;
        });

        let subminds_to_remove = modifiedSubminds.filter(submind => !submind.is_active).map(submind => submind.service_name);
        let subminds_to_add = modifiedSubminds.filter(submind => submind.is_active).map(submind => submind.service_name);

        if (subminds_to_add.length !== 0 || subminds_to_remove.length !== 0){
            socket.emit('broadcast', {
                msg_type: "update_participating_subminds",
                "cid": cid,
                "subminds_to_invite": subminds_to_add,
                "subminds_to_kick": subminds_to_remove,
            });
        }

        const dropdownToggle = document.getElementById(`dropdownToggle-${cid}`);
        if (dropdownToggle) dropdownToggle.click();

        buttonsContainer.style.display = 'none';
    };
}


function parseSubmindsState(data){
    submindsState = data;

    const cids = Object.keys(submindsState["subminds_per_cid"])
    if (cids.length === 0){
        setAllCountersToZero();
    } else {
        for (const cid of cids){
            refreshSubmindsCount(cid);
        }
    }
}

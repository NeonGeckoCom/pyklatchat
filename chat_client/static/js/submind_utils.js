let submindsPerCid;


function renderActiveSubminds(cid) {

    const loadingSpinner = document.getElementById(`${cid}-subminds-state-loading`);
    const table = document.getElementById(`${cid}-subminds-state-table`);
    const entriesContainer = document.getElementById(`${cid}-subminds-state-entries`);

    // TODO: fix it
    loadingSpinner.style.display = 'none!important';
    table.style.display = '';
    entriesContainer.innerHTML = '';

    (submindsPerCid?.[cid] || []).forEach(submind => {
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
        entriesContainer.appendChild(row);
    });
}


async function parseSubmindsState(data){
    submindsPerCid = data['subminds_per_cid'];
}


let submindsPerCid;




function renderActiveSubminds(cid) {
    const table = document.getElementById(`${cid}-subminds-state-table`);
    table.innerHTML = '';

    (submindsPerCid?.[cid] || []).forEach(submind => {
        const row = document.createElement('tr');

        const checkboxCell = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'form-check-input bot-checkbox';
        checkbox.value = submind.name;
        checkbox.checked = submind.status === 'active';
        checkbox.id = `bot-${submind.submind_id}-${cid}`;
        checkboxCell.appendChild(checkbox);


        const nameCell = document.createElement('td');
        const label = document.createElement('label');
        label.className = 'form-check-label';
        label.htmlFor = `bot-${submind.submind_id}-${cid}`;
        label.textContent = submind.submind_id.slice(0, submind.submind_id.lastIndexOf('-'));
        nameCell.appendChild(label);

        row.appendChild(checkboxCell);
        row.appendChild(nameCell);

        table.appendChild(row);
    });
}


async function parseSubmindsState(data){
    submindsPerCid = data['subminds_per_cid'];
}
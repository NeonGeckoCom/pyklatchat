document.addEventListener("DOMContentLoaded", (_) => {
    document.addEventListener('configLoaded',async (_)=> {
        fetchServer(`configs/footer`)
            .then(response => response.json())
            .then(data => {
                document.getElementById('footer-loading-spinner').style.display = 'none';
                if (data.markup) {
                    document.getElementById('footer-container').innerHTML = data.markup;
                } else {
                    document.getElementById('footer-content').style.display = 'block';
                }
            })
            .catch(error => console.error('Error fetching footer:', error));
    });
});
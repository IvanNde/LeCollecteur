function ouvrirModalePing(serveurId, serveurNom) {
    const content = document.getElementById('modal-ping-content');
    content.innerHTML = `<b>Ping de ${serveurNom}...</b><br><span style='color:#888;'>En cours...</span>`;
    document.getElementById('modal-ping').style.display = 'block';
    fetch(`/ping/${serveurId}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                content.innerHTML = `<b>Réponse de ${data.ip} :</b><br><span style='color:green;'>${data.message}</span>`;
            } else {
                content.innerHTML = `<b>Échec du ping (${data.ip || ''}) :</b><br><span style='color:red;'>${data.message}</span><br><small>${data.error || ''}</small>`;
            }
        })
        .catch(() => {
            content.innerHTML = `<span style='color:red;'>Erreur réseau ou serveur</span>`;
        });
}

function fermerModalePing() {
    document.getElementById('modal-ping').style.display = 'none';
}
// Fermer la modale si on clique en dehors
window.addEventListener('click', function(event) {
    const modal = document.getElementById('modal-ping');
    if (event.target === modal) {
        fermerModalePing();
    }
}); 
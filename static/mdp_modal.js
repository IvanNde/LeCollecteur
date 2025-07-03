function ouvrirModaleMdp(serveurId) {
    document.getElementById('modal-serveur-id').value = serveurId;
    document.getElementById('modal-session-mdp').value = '';
    document.getElementById('modal-mdp-result').innerHTML = '';
    document.getElementById('modal-mdp').style.display = 'block';
    setTimeout(() => { document.getElementById('modal-session-mdp').focus(); }, 100);
}

function fermerModaleMdp() {
    document.getElementById('modal-mdp').style.display = 'none';
}

function verifierAfficherMdp() {
    const serveurId = document.getElementById('modal-serveur-id').value;
    const sessionMdp = document.getElementById('modal-session-mdp').value;
    const resultDiv = document.getElementById('modal-mdp-result');
    resultDiv.innerHTML = 'Vérification...';
    fetch(`/afficher_mot_de_passe/${serveurId}`, {
        method: 'POST',
        headers: { 'Accept': 'application/json' },
        body: new URLSearchParams({ password: sessionMdp })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            resultDiv.innerHTML = `<b>Mot de passe SSH :</b> <span style='font-family:monospace;'>${data.mot_de_passe || '(vide)'}</span>`;
        } else {
            resultDiv.innerHTML = `<span style='color:red;'>${data.message}</span>`;
        }
    })
    .catch(() => {
        resultDiv.innerHTML = "<span style='color:red;'>Erreur réseau</span>";
    });
}
// Fermer la modale si on clique en dehors
window.onclick = function(event) {
    const modal = document.getElementById('modal-mdp');
    if (event.target === modal) {
        fermerModaleMdp();
    }
} 
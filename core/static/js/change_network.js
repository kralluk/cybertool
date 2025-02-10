document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("networkSelect").addEventListener("change", function () {
        let selectedNetwork = this.value;
        fetch("/", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRFToken": getCSRFToken()
            },
            body: "network=" + encodeURIComponent(selectedNetwork)
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById("current_network").innerText = data.current_network;
            alert(data.message);
        })
        .catch(error => console.error("Chyba:", error));
    });
});

// Funkce pro získání CSRF tokenu z Django šablony
function getCSRFToken() {
    return document.querySelector("[name=csrfmiddlewaretoken]").value;
}
document.addEventListener("DOMContentLoaded", function () {
    const toggleButton = document.createElement("button");
    toggleButton.id = "toggle-dark-mode";
    toggleButton.textContent = "🌙 Tryb ciemny";
    document.body.insertBefore(toggleButton, document.body.firstChild);

    const darkModeStylesheet = document.getElementById("dark-mode-stylesheet");

    // Sprawdzenie zapisanych ustawień użytkownika
    if (localStorage.getItem("dark-mode") === "enabled") {
        darkModeStylesheet.removeAttribute("disabled");
        toggleButton.textContent = "☀️ Tryb jasny";
    }

    toggleButton.addEventListener("click", function () {
        if (darkModeStylesheet.disabled) {
            darkModeStylesheet.removeAttribute("disabled");
            localStorage.setItem("dark-mode", "enabled");
            toggleButton.textContent = "☀️ Tryb jasny";
        } else {
            darkModeStylesheet.setAttribute("disabled", "true");
            localStorage.setItem("dark-mode", "disabled");
            toggleButton.textContent = "🌙 Tryb ciemny";
        }
    });
});

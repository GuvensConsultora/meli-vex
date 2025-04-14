/** @odoo-module **/
document.addEventListener("DOMContentLoaded", function () {
    function toggleAutoSection() {
        const checkbox = document.querySelector("input[name='is_automatic_type']");
        const section = document.getElementsByClassName("auto_section");

        if (checkbox && section) {
            section.style.display = checkbox.checked ? "none" : "block";
        }
    }

    // Ejecutar al cargar
    toggleAutoSection();

    // Detectar cambios en el checkbox
    document.addEventListener("change", function (event) {
        if (event.target.name === "is_automatic_type") {
            toggleAutoSection();
        }
    });
});

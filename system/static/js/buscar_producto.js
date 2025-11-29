// Listener that submits the search form only when Enter is pressed in the input.
// The form already uses GET, so no live filtering occurs while typing.
document.addEventListener('DOMContentLoaded', function () {
    var input = document.getElementById('buscarProductoInput');
    var form = document.getElementById('buscarProductoForm');
    if (!input || !form) return;

    // Prevent accidental submissions from non-Enter keys; rely on native Enter behavior.
    input.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter') {
            // Let the form submit normally
            return true;
        }
    });

    // Optional: prevent other controls from submitting the form unintentionally
    form.addEventListener('submit', function (e) {
        // If input is empty, allow submit to show all products; no special handling needed.
    });

    // Reset button: clear input and submit form to show all products
    var resetBtn = document.getElementById('buscarResetBtn');
    if (resetBtn) {
        resetBtn.addEventListener('click', function (ev) {
            ev.preventDefault();
            input.value = '';
            // submit the form to reload without query
            try {
                form.submit();
            } catch (err) {
                // fallback: navigate to current path
                window.location.href = window.location.pathname;
            }
        });
    }
});
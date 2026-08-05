<%--
    Wires every [data-password-toggle] button to the password input it names.

    Included only on pages that have a password field. The button starts as a
    plain button with no behaviour, so if scripting is unavailable the field
    still works normally - it just stays masked.
--%>
<script>
    (function () {
        var toggles = document.querySelectorAll('[data-password-toggle]');

        Array.prototype.forEach.call(toggles, function (button) {
            var input = document.getElementById(button.getAttribute('data-password-toggle'));
            if (!input) { return; }

            var eye = button.querySelector('[data-eye="show"]');
            var eyeOff = button.querySelector('[data-eye="hide"]');

            button.hidden = false;

            button.addEventListener('click', function () {
                var reveal = input.type === 'password';
                input.type = reveal ? 'text' : 'password';

                button.setAttribute('aria-pressed', String(reveal));
                button.setAttribute('aria-label', reveal ? 'Hide password' : 'Show password');
                button.title = reveal ? 'Hide password' : 'Show password';
                eye.hidden = reveal;
                eyeOff.hidden = !reveal;

                // Clicking the button moves focus off the field; put the caret
                // back where the user left it so typing can continue.
                var caret = input.value.length;
                input.focus();
                try {
                    input.setSelectionRange(caret, caret);
                } catch (e) {
                    /* Some browsers reject setSelectionRange on certain input types. */
                }
            });
        });
    })();
</script>

/* =====================================================================
   Sign-in page
   ===================================================================== */

import { api, auth, signIn } from "./api.js";
import { $, el, modal, notify, show } from "./ui.js";

const form = $("#loginForm");
const usernameInput = $("#username");
const passwordInput = $("#password");
const submitButton = $("#submitBtn");
const errorNode = $("#formError");

/* Already signed in? Send them straight to their dashboard rather than
   showing a login form they do not need. The token is verified against
   the server first, so a stale one still lands here. */
(async function redirectIfSignedIn() {
  if (!auth.isSignedIn) return;
  try {
    const user = await api.get("/api/auth/me");
    location.replace(user.role === "student" ? "dashboard.html" : "admin.html");
  } catch {
    // Token is stale; api.js has already cleared it. Stay on the form.
  }
})();

// Shown when api.js bounced the user here after a 401.
if (new URLSearchParams(location.search).get("expired")) {
  show("#expiredNotice", true);
  history.replaceState(null, "", location.pathname);
}

/* --- Show / hide password -------------------------------------------- */

$("#togglePassword").addEventListener("click", (event) => {
  const button = event.currentTarget;
  const revealed = passwordInput.type === "text";
  passwordInput.type = revealed ? "password" : "text";
  button.setAttribute("aria-pressed", String(!revealed));
  button.setAttribute("aria-label", revealed ? "Show password" : "Hide password");
  button.textContent = revealed ? "👁" : "🙈";
});

/* --- Submit ----------------------------------------------------------- */

function showError(message) {
  errorNode.textContent = message;
  errorNode.classList.remove("hidden");
  usernameInput.classList.add("is-invalid");
  passwordInput.classList.add("is-invalid");
}

function hideError() {
  errorNode.classList.add("hidden");
  usernameInput.classList.remove("is-invalid");
  passwordInput.classList.remove("is-invalid");
}

[usernameInput, passwordInput].forEach((input) =>
  input.addEventListener("input", hideError)
);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError();

  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  if (!username || !password) {
    showError("Enter both your username and password");
    (username ? passwordInput : usernameInput).focus();
    return;
  }

  submitButton.classList.add("is-loading");
  submitButton.disabled = true;

  try {
    const user = await signIn(username, password);

    if (user.must_change_password) {
      // Flagged so the dashboard can prompt immediately - a generated
      // initial password should not stay in use.
      sessionStorage.setItem("fs.mustChangePassword", "1");
    }

    notify.success(`Welcome back, ${user.name}`);

    // Small delay so the toast is visible before navigation.
    setTimeout(() => {
      location.href = user.role === "student" ? "dashboard.html" : "admin.html";
    }, 350);
  } catch (error) {
    showError(error.message || "Sign-in failed");
    passwordInput.select();
  } finally {
    submitButton.classList.remove("is-loading");
    submitButton.disabled = false;
  }
});

/* --- Forgot password --------------------------------------------------- *
 * Self-service, no session required. The server checks the username
 * against the email on file before accepting a new password - see
 * backend/routes/auth.py for what that does and does not protect
 * against.                                                              */

$("#forgotPasswordBtn").addEventListener("click", async () => {
  const policy = await api.get("/api/auth/password-policy").catch(() => null);

  await modal({
    title: "Reset your password",
    render: (close) => {
      const username = el("input", {
        class: "input",
        placeholder: "Your username or roll number",
        autocomplete: "username",
      });
      const email = el("input", {
        class: "input",
        type: "email",
        placeholder: "The email on your account",
        autocomplete: "email",
      });
      const newPassword = el("input", {
        class: "input",
        type: "password",
        placeholder: "New password",
        autocomplete: "new-password",
      });
      const error = el("p", { class: "field-error hidden" });

      const submit = el("button", {
        class: "btn btn-primary",
        text: "Reset password",
        onclick: async () => {
          error.classList.add("hidden");
          submit.classList.add("is-loading");
          submit.disabled = true;
          try {
            await api.post("/api/auth/forgot-password", {
              username: username.value.trim(),
              email: email.value.trim(),
              new_password: newPassword.value,
            });
            notify.success("Password updated. You can sign in with it now.");
            close(true);
          } catch (err) {
            error.textContent = err.message;
            error.classList.remove("hidden");
          } finally {
            submit.classList.remove("is-loading");
            submit.disabled = false;
          }
        },
      });

      return el(
        "div",
        {},
        el(
          "div",
          { class: "modal-body stack-sm" },
          el(
            "p",
            { class: "text-sm muted" },
            "Enter your username and the email on your account, and choose a new password."
          ),
          el(
            "div",
            { class: "field" },
            el("label", { class: "label", text: "Username" }),
            username
          ),
          el(
            "div",
            { class: "field" },
            el("label", { class: "label", text: "Email" }),
            email
          ),
          el(
            "div",
            { class: "field" },
            el("label", { class: "label", text: "New password" }),
            newPassword
          ),
          policy
            ? el("div", {
                class: "field-hint",
                text: `Requires: ${policy.requirements.join(", ").toLowerCase()}.`,
              })
            : null,
          error
        ),
        el(
          "div",
          { class: "modal-footer" },
          el("button", {
            class: "btn btn-outline",
            text: "Cancel",
            onclick: () => close(null),
          }),
          submit
        )
      );
    },
  });
});

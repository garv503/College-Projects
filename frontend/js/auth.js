const form = document.getElementById("authForm");
const message = document.getElementById("message");

form.onsubmit = async (e) => {
  e.preventDefault();

  const username = document.getElementById("usernameInput").value.trim();
  const password = document.getElementById("passwordInput").value.trim();

  const res = await fetch("http://127.0.0.1:5000/login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ username, password })
  });

  const data = await res.json();

  if (data.status === "success") {

    localStorage.setItem("student_id", data.student_id);
    localStorage.setItem("username", username);

    if (data.role === "admin") {
      window.location.href = "admin.html";
    } else {
      window.location.href = "dashboard.html";
    }

  } else {
    message.textContent = data.message;
    message.className = "text-red-500 mt-4 text-center";
  }
};

// Forgot Password
async function forgotPassword() {
  const username = prompt("Enter your username:");
  const newPassword = prompt("Enter new password:");

  if (!username || !newPassword) return;

  const res = await fetch("http://127.0.0.1:5000/forgot-password", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ username, password: newPassword })
  });

  const data = await res.json();
  alert(data.message);
}

// Show Password
function togglePassword() {
  const p = document.getElementById("passwordInput");
  p.type = p.type === "password" ? "text" : "password";
}

// Dark Mode
function toggleTheme() {
  document.body.classList.toggle("dark-mode");
}
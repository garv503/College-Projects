const student_id = localStorage.getItem("student_id");

// Load Dashboard Data
async function loadDashboard() {
  const res = await fetch(`http://127.0.0.1:5000/student-data/${student_id}`);
  const data = await res.json();

  let html = "";
  let total = 0;

  if (data.length > 0) {
    document.getElementById("studentName").textContent = data[0].name;
    document.getElementById("studentInfo").textContent =
      `${data[0].branch} - Semester ${data[0].semester}`;
  }

  data.forEach(d => {
    total += d.marks;

    html += `
      <tr>
        <td>${d.subject_name}</td>
        <td>${d.marks}</td>
        <td>${d.attendance_percentage}%</td>
      </tr>
    `;
  });

  document.getElementById("studentTable").innerHTML = html;

  // Average marks
  if (data.length > 0) {
    document.getElementById("avgMarks").textContent =
      (total / data.length).toFixed(2);
  }

  // Chart Call
  renderChart(data);
}


// Chart Function
function renderChart(data) {
  const labels = data.map(d => d.subject_name);
  const marks = data.map(d => d.marks);

  new Chart(document.getElementById("marksChart"), {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Marks",
        data: marks
      }]
    }
  });
}


// Analytics Loader
async function loadAnalytics() {
  const res = await fetch(`http://127.0.0.1:5000/analytics/${student_id}`);
  const data = await res.json();

  document.getElementById("avgMarks").textContent = data.average_marks;
  document.getElementById("avgAttendance").textContent = data.average_attendance;

  const statusEl = document.getElementById("status");
  statusEl.textContent = data.status;

  statusEl.style.color = data.status === "Weak" ? "red" : "green";
}


// Password Change Function
async function changePassword() {
  const username = localStorage.getItem("username");
  const newPassword = prompt("Enter new password:");

  const res = await fetch("http://127.0.0.1:5000/change-password", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ username, password: newPassword })
  });

  const data = await res.json();
  alert(data.message);
}


// Logout Function
function logout(){
  window.location.href="index.html";
}


// Dark Mode Toggle
function toggleTheme(){
  document.body.classList.toggle("dark-mode");
}


// Function Loaders
window.onload = () => {
  loadDashboard();
  loadAnalytics();
};
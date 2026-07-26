const form = document.getElementById("fullForm");
const container = document.getElementById("subjectsContainer");

// Load Subjects
async function loadSubjects() {
  const branchValue = document.getElementById("branch").value;
  const semesterValue = document.getElementById("semester").value;

  if (!branchValue || !semesterValue) {
    alert("Please enter branch and semester first");
    return;
  }

  const res = await fetch(`http://127.0.0.1:5000/subjects/${branchValue}/${semesterValue}`);
  const data = await res.json();

  container.innerHTML = "";

  data.forEach(sub => {
    container.innerHTML += `
      <div class="mt-2">
        <label>${sub.subject_name}</label>
        <input placeholder="Marks" id="m_${sub.subject_id}" class="w-full p-2 border mb-1" required>
        <input placeholder="Attendance" id="a_${sub.subject_id}" class="w-full p-2 border mb-2" required>
      </div>
    `;
  });
}

// Submit Form
form.onsubmit = async (e) => {
  e.preventDefault();

  const name = document.getElementById("name").value;
  const branch = document.getElementById("branch").value;
  const semester = document.getElementById("semester").value;

  const subjects = [];

  document.querySelectorAll("[id^='m_']").forEach(el => {
    const id = el.id.split("_")[1];

    subjects.push({
      subject_id: id,
      marks: el.value,
      attendance: document.getElementById(`a_${id}`).value
    });
  });

  if (subjects.length === 0) {
    alert("Please load subjects and enter data");
    return;
  }

  const res = await fetch("http://127.0.0.1:5000/add-full-student", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      name: name,
      branch: branch,
      semester: semester,
      subjects: subjects
    })
  });

  const data = await res.json();

  if (data.status === "success") {
    alert("Student Added Successfully!");
    form.reset();
    container.innerHTML = "";
  } else {
    alert("Error adding student");
  }
};

// Logout
function logout() {
  window.location.href = "index.html";
}

// Dark Mode
function toggleTheme() {
  document.body.classList.toggle("dark-mode");
}
<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Unable to Save Note</title>
    <%@ include file="all_component/allcss.jsp" %>
</head>
<body>
    <%@ include file="all_component/navbar.jsp" %>
    <main class="container py-5">
        <div class="alert alert-danger" role="alert">
            <h4 class="alert-heading">Unable to save your note</h4>
            <p><%= request.getAttribute("errorMessage") != null ? request.getAttribute("errorMessage") : "Please try again." %></p>
        </div>
        <a href="addNotes.jsp" class="btn btn-primary">Back to Add Notes</a>
    </main>
</body>
</html>

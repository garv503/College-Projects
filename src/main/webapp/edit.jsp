<%--
    Edit form.

    The note is loaded scoped to the signed-in user. Previously it was fetched
    by id alone, so changing note_id in the URL displayed another user's note.
    A note that is missing or not owned by the caller now redirects instead of
    rendering, which also fixes the null dereference the old page hit.
--%>
<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<%@ page import="com.util.Csrf" %>
<%@ page import="com.util.WebUtils" %>
<%@ page import="com.DAO.PostDAO" %>
<%@ page import="com.User.Post" %>
<%@ page import="com.User.UserDetails" %>

<c:set var="csrfToken" value="<%= Csrf.token(request) %>"/>
<c:set var="ctx" value="${pageContext.request.contextPath}"/>
<c:set var="activePage" value="notes"/>

<%
    UserDetails editUser = (UserDetails) session.getAttribute("userD");
    int editNoteId = WebUtils.intParam(request, "note_id", -1);
    Post editNote = editNoteId < 1 ? null : new PostDAO().getNoteById(editNoteId, editUser.getId());

    if (editNote == null) {
        WebUtils.error(request, "That note could not be found.");
        response.sendRedirect(request.getContextPath() + "/showNotes.jsp");
        return;
    }

    request.setAttribute("note", editNote);
%>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Edit note &mdash; E-Notes</title>
    <%@ include file="all_component/allcss.jsp" %>
</head>
<body>
    <%@ include file="all_component/icons.jsp" %>
    <%@ include file="all_component/navbar.jsp" %>

    <main class="page">
        <div class="container" style="max-width:800px">
            <%@ include file="all_component/flash.jsp" %>

            <div class="page-head">
                <div>
                    <h1>Edit note</h1>
                    <p class="sub">Changes are saved to this note only.</p>
                </div>
                <a class="btn btn-ghost btn-sm" href="${ctx}/showNotes.jsp">
                    <svg class="icon"><use href="#i-arrow-left"/></svg> Back to notes
                </a>
            </div>

            <div class="card">
                <div class="card-body">
                    <form action="${ctx}/NoteEditServlet" method="post" novalidate>
                        <input type="hidden" name="csrfToken" value="${csrfToken}">
                        <input type="hidden" name="noteid" value="${note.id}">

                        <div class="field">
                            <label for="title">Title</label>
                            <input class="input" type="text" id="title" name="title"
                                   maxlength="200" required
                                   value="<c:out value='${note.title}'/>">
                        </div>

                        <div class="field">
                            <label for="content">Content</label>
                            <%-- No whitespace inside the textarea tags: anything there
                                 becomes part of the note's content. --%>
                            <textarea class="textarea" id="content" name="content"
                                      maxlength="20000" required><c:out value="${note.content}"/></textarea>
                        </div>

                        <div style="display:flex;gap:10px;flex-wrap:wrap">
                            <button type="submit" class="btn btn-primary">
                                <svg class="icon"><use href="#i-check"/></svg> Save changes
                            </button>
                            <a class="btn btn-outline" href="${ctx}/showNotes.jsp">Cancel</a>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </main>
</body>
</html>

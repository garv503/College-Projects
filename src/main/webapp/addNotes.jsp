<%--
    New note form.

    There is no hidden author field any more: AddNotesServlet takes the owner
    from the session, so the note cannot be filed under another account.
--%>
<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<%@ page import="com.util.Csrf" %>

<c:set var="csrfToken" value="<%= Csrf.token(request) %>"/>
<c:set var="ctx" value="${pageContext.request.contextPath}"/>
<c:set var="activePage" value="add"/>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>New note &mdash; E-Notes</title>
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
                    <h1>New note</h1>
                    <p class="sub">Give it a title and write whatever you need.</p>
                </div>
                <a class="btn btn-ghost btn-sm" href="${ctx}/showNotes.jsp">
                    <svg class="icon"><use href="#i-arrow-left"/></svg> Back to notes
                </a>
            </div>

            <div class="card">
                <div class="card-body">
                    <form action="${ctx}/AddNotesServlet" method="post" novalidate>
                        <input type="hidden" name="csrfToken" value="${csrfToken}">

                        <div class="field">
                            <label for="title">Title</label>
                            <input class="input" type="text" id="title" name="title"
                                   placeholder="What is this note about?"
                                   maxlength="200" required autofocus>
                        </div>

                        <div class="field">
                            <label for="content">Content</label>
                            <textarea class="textarea" id="content" name="content"
                                      placeholder="Start writing..."
                                      maxlength="20000" required></textarea>
                            <p class="field-hint">Line breaks are preserved.</p>
                        </div>

                        <div style="display:flex;gap:10px;flex-wrap:wrap">
                            <button type="submit" class="btn btn-primary">
                                <svg class="icon"><use href="#i-check"/></svg> Save note
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

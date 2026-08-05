<%--
    Note list, with search.

    Note titles and bodies are written with <c:out>, which escapes them. They
    were previously written with <%= %>, so a note containing markup ran as HTML
    in the author's own browser.
--%>
<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<%@ taglib prefix="fmt" uri="http://java.sun.com/jsp/jstl/fmt" %>
<%@ taglib prefix="fn" uri="http://java.sun.com/jsp/jstl/functions" %>
<%@ page import="com.util.Csrf" %>
<%@ page import="com.util.WebUtils" %>
<%@ page import="com.DAO.PostDAO" %>
<%@ page import="com.User.UserDetails" %>

<c:set var="csrfToken" value="<%= Csrf.token(request) %>"/>
<c:set var="ctx" value="${pageContext.request.contextPath}"/>
<c:set var="activePage" value="notes"/>

<%
    UserDetails listUser = (UserDetails) session.getAttribute("userD");
    String searchTerm = WebUtils.trimmed(request, "q");
    PostDAO listDao = new PostDAO();

    request.setAttribute("searchTerm", searchTerm);
    request.setAttribute("notes", searchTerm == null
            ? listDao.getNotes(listUser.getId())
            : listDao.searchNotes(listUser.getId(), searchTerm));
%>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>My notes &mdash; E-Notes</title>
    <%@ include file="all_component/allcss.jsp" %>
</head>
<body>
    <%@ include file="all_component/icons.jsp" %>
    <%@ include file="all_component/navbar.jsp" %>

    <main class="page">
        <div class="container">
            <%@ include file="all_component/flash.jsp" %>

            <div class="page-head">
                <div>
                    <h1>My notes</h1>
                    <p class="sub">
                        <c:choose>
                            <c:when test="${not empty searchTerm}">
                                ${fn:length(notes)} result<c:if test="${fn:length(notes) ne 1}">s</c:if>
                                for &ldquo;<c:out value="${searchTerm}"/>&rdquo;
                            </c:when>
                            <c:otherwise>Everything you have saved, pinned notes first.</c:otherwise>
                        </c:choose>
                    </p>
                </div>
                <a class="btn btn-primary" href="${ctx}/addNotes.jsp">
                    <svg class="icon"><use href="#i-plus"/></svg> New note
                </a>
            </div>

            <div class="toolbar">
                <form class="search-form" action="${ctx}/showNotes.jsp" method="get" role="search">
                    <input class="input" type="search" name="q" value="<c:out value='${searchTerm}'/>"
                           placeholder="Search your notes..." aria-label="Search notes">
                    <button type="submit" class="btn btn-outline">
                        <svg class="icon"><use href="#i-search"/></svg>
                        <span class="visually-hidden">Search</span>
                    </button>
                </form>

                <c:if test="${not empty searchTerm}">
                    <a class="btn btn-ghost btn-sm" href="${ctx}/showNotes.jsp">Clear search</a>
                </c:if>
            </div>

            <c:choose>
                <c:when test="${empty notes}">
                    <div class="empty">
                        <div class="empty-icon">
                            <svg class="icon"><use href="#i-${empty searchTerm ? 'notes' : 'search'}"/></svg>
                        </div>
                        <c:choose>
                            <c:when test="${not empty searchTerm}">
                                <h3>No matches</h3>
                                <p>Nothing matched &ldquo;<c:out value="${searchTerm}"/>&rdquo;. Try a different word.</p>
                                <a class="btn btn-outline" href="${ctx}/showNotes.jsp">Show all notes</a>
                            </c:when>
                            <c:otherwise>
                                <h3>Nothing here yet</h3>
                                <p>Write your first note and it will appear right here.</p>
                                <a class="btn btn-primary" href="${ctx}/addNotes.jsp">
                                    <svg class="icon"><use href="#i-plus"/></svg> Write a note
                                </a>
                            </c:otherwise>
                        </c:choose>
                    </div>
                </c:when>

                <c:otherwise>
                    <div class="notes-grid">
                        <c:forEach var="note" items="${notes}">
                            <article class="note ${note.pinned ? 'is-pinned' : ''}">
                                <div class="note-body">
                                    <h3 class="note-title">
                                        <c:if test="${note.pinned}">
                                            <span class="note-pin-marker" title="Pinned">
                                                <svg class="icon"><use href="#i-pin"/></svg>
                                            </span>
                                        </c:if>
                                        <c:out value="${note.title}"/>
                                    </h3>
                                    <p class="note-content"><c:out value="${note.content}"/></p>
                                </div>

                                <div class="note-meta">
                                    <span class="tag">
                                        <svg class="icon" style="width:12px;height:12px"><use href="#i-clock"/></svg>
                                        <fmt:formatDate value="${note.createdAt}" pattern="d MMM yyyy, HH:mm"/>
                                    </span>
                                    <c:if test="${note.pinned}"><span class="tag tag-pinned">pinned</span></c:if>
                                    <c:if test="${note.edited}"><span class="tag">edited</span></c:if>
                                </div>

                                <%-- Each action is a POST carrying the CSRF token. Delete was
                                     previously a GET link, so it could be triggered from
                                     anywhere and acted on any note id. --%>
                                <div class="note-actions">
                                    <form action="${ctx}/PinServlet" method="post">
                                        <input type="hidden" name="csrfToken" value="${csrfToken}">
                                        <input type="hidden" name="note_id" value="${note.id}">
                                        <input type="hidden" name="q" value="<c:out value='${searchTerm}'/>">
                                        <button type="submit" class="btn btn-ghost btn-sm"
                                                title="${note.pinned ? 'Unpin this note' : 'Pin this note'}">
                                            <svg class="icon"><use href="#i-pin"/></svg>
                                            ${note.pinned ? 'Unpin' : 'Pin'}
                                        </button>
                                    </form>

                                    <a class="btn btn-ghost btn-sm" href="${ctx}/edit.jsp?note_id=${note.id}">
                                        <svg class="icon"><use href="#i-edit"/></svg> Edit
                                    </a>

                                    <form action="${ctx}/deleteServlet" method="post"
                                          onsubmit="return confirm('Delete this note? This cannot be undone.');">
                                        <input type="hidden" name="csrfToken" value="${csrfToken}">
                                        <input type="hidden" name="note_id" value="${note.id}">
                                        <button type="submit" class="btn btn-danger btn-sm spacer" title="Delete this note">
                                            <svg class="icon"><use href="#i-trash"/></svg> Delete
                                        </button>
                                    </form>
                                </div>
                            </article>
                        </c:forEach>
                    </div>
                </c:otherwise>
            </c:choose>
        </div>
    </main>

    <%@ include file="all_component/footer.jsp" %>
</body>
</html>

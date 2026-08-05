<%--
    Dashboard.

    The sign-in check that used to sit here as a scriptlet now lives in
    AuthFilter, which cannot be bypassed by a missing return statement.
--%>
<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<%@ taglib prefix="fmt" uri="http://java.sun.com/jsp/jstl/fmt" %>
<%@ page import="com.util.Csrf" %>
<%@ page import="com.DAO.PostDAO" %>
<%@ page import="com.User.UserDetails" %>

<c:set var="csrfToken" value="<%= Csrf.token(request) %>"/>
<c:set var="ctx" value="${pageContext.request.contextPath}"/>
<c:set var="activePage" value="home"/>

<%
    UserDetails dashboardUser = (UserDetails) session.getAttribute("userD");
    PostDAO dashboardDao = new PostDAO();
    request.setAttribute("totalNotes", dashboardDao.countNotes(dashboardUser.getId()));
    request.setAttribute("pinnedNotes", dashboardDao.countPinned(dashboardUser.getId()));
    request.setAttribute("recentNotes", dashboardDao.getNotes(dashboardUser.getId()));
%>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Dashboard &mdash; E-Notes</title>
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
                    <h1>Hello, <c:out value="${sessionScope.userD.name}"/></h1>
                    <p class="sub">Here is what you have saved so far.</p>
                </div>
                <a class="btn btn-primary" href="${ctx}/addNotes.jsp">
                    <svg class="icon"><use href="#i-plus"/></svg> New note
                </a>
            </div>

            <div class="stat-grid">
                <div class="stat">
                    <div class="stat-label">
                        <svg class="icon"><use href="#i-notes"/></svg> Total notes
                    </div>
                    <div class="stat-value">${totalNotes}</div>
                </div>

                <div class="stat">
                    <div class="stat-label">
                        <svg class="icon"><use href="#i-pin"/></svg> Pinned
                    </div>
                    <div class="stat-value">${pinnedNotes}</div>
                </div>

                <div class="stat">
                    <div class="stat-label">
                        <svg class="icon"><use href="#i-clock"/></svg> Member since
                    </div>
                    <div class="stat-value" style="font-size:1.25rem">
                        <c:choose>
                            <c:when test="${not empty sessionScope.userD.createdAt}">
                                <fmt:formatDate value="${sessionScope.userD.createdAt}" pattern="d MMM yyyy"/>
                            </c:when>
                            <c:otherwise>&mdash;</c:otherwise>
                        </c:choose>
                    </div>
                </div>
            </div>

            <c:choose>
                <c:when test="${empty recentNotes}">
                    <div class="empty">
                        <div class="empty-icon"><svg class="icon"><use href="#i-notes"/></svg></div>
                        <h3>No notes yet</h3>
                        <p>Your notes will show up here once you write your first one.</p>
                        <a class="btn btn-primary" href="${ctx}/addNotes.jsp">
                            <svg class="icon"><use href="#i-plus"/></svg> Write your first note
                        </a>
                    </div>
                </c:when>

                <c:otherwise>
                    <div class="page-head">
                        <h2>Recent notes</h2>
                        <a href="${ctx}/showNotes.jsp">View all ${totalNotes} &rarr;</a>
                    </div>

                    <div class="notes-grid">
                        <%-- Dashboard shows a preview; the full list lives on showNotes.jsp. --%>
                        <c:forEach var="note" items="${recentNotes}" end="5">
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
                                        <fmt:formatDate value="${note.createdAt}" pattern="d MMM yyyy"/>
                                    </span>
                                    <c:if test="${note.edited}"><span class="tag">edited</span></c:if>
                                </div>

                                <div class="note-actions">
                                    <a class="btn btn-ghost btn-sm" href="${ctx}/edit.jsp?note_id=${note.id}">
                                        <svg class="icon"><use href="#i-edit"/></svg> Edit
                                    </a>
                                </div>
                            </article>
                        </c:forEach>
                    </div>
                </c:otherwise>
            </c:choose>
        </div>
    </main>
</body>
</html>

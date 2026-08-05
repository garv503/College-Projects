<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<%@ page import="com.util.Csrf" %>

<c:set var="csrfToken" value="<%= Csrf.token(request) %>"/>
<c:set var="ctx" value="${pageContext.request.contextPath}"/>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Something went wrong &mdash; E-Notes</title>
    <%@ include file="all_component/allcss.jsp" %>
</head>
<body>
    <%@ include file="all_component/icons.jsp" %>
    <%@ include file="all_component/navbar.jsp" %>

    <main class="page">
        <div class="container">
            <div class="empty">
                <div class="empty-icon" style="color:var(--danger);background:var(--danger-bg)">
                    <svg class="icon"><use href="#i-alert"/></svg>
                </div>
                <h3>Something went wrong</h3>

                <%-- Only the app's own validation message is shown, escaped.
                     Never a stack trace or raw exception text. --%>
                <p>
                    <c:choose>
                        <c:when test="${not empty requestScope.errorMessage}">
                            <c:out value="${requestScope.errorMessage}"/>
                        </c:when>
                        <c:otherwise>
                            That request could not be completed. Please try again.
                        </c:otherwise>
                    </c:choose>
                </p>

                <div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap">
                    <a class="btn btn-primary" href="${ctx}/home.jsp">Back to dashboard</a>
                    <a class="btn btn-outline" href="${ctx}/showNotes.jsp">My notes</a>
                </div>
            </div>
        </div>
    </main>
</body>
</html>

<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<%@ page import="com.util.Csrf" %>
<c:set var="csrfToken" value="<%= Csrf.token(request) %>"/>
<c:set var="ctx" value="${pageContext.request.contextPath}"/>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>E-Notes &mdash; Your notes, organised</title>
    <%@ include file="all_component/allcss.jsp" %>
</head>
<body>
    <%@ include file="all_component/icons.jsp" %>
    <%@ include file="all_component/navbar.jsp" %>

    <main class="page" style="padding-top:0">
        <section class="hero">
            <div class="container">
                <span class="eyebrow">
                    <svg class="icon"><use href="#i-bolt"/></svg> Fast, private, yours
                </span>

                <h1>Every thought worth keeping, <span class="gradient-text">in one place</span></h1>

                <p class="lead">
                    Capture ideas, pin what matters, and find any note in seconds.
                    E-Notes keeps your writing organised and to yourself.
                </p>

                <div class="hero-actions">
                    <c:choose>
                        <c:when test="${not empty sessionScope.userD}">
                            <a class="btn btn-primary" href="${ctx}/addNotes.jsp">
                                <svg class="icon"><use href="#i-plus"/></svg> Write a note
                            </a>
                            <a class="btn btn-outline" href="${ctx}/showNotes.jsp">
                                <svg class="icon"><use href="#i-notes"/></svg> My notes
                            </a>
                        </c:when>
                        <c:otherwise>
                            <a class="btn btn-primary" href="${ctx}/register.jsp">
                                <svg class="icon"><use href="#i-user-plus"/></svg> Create free account
                            </a>
                            <a class="btn btn-outline" href="${ctx}/login.jsp">
                                <svg class="icon"><use href="#i-user"/></svg> Sign in
                            </a>
                        </c:otherwise>
                    </c:choose>
                </div>

                <div class="feature-grid">
                    <article class="feature">
                        <div class="feature-icon"><svg class="icon"><use href="#i-bolt"/></svg></div>
                        <h3>Write without friction</h3>
                        <p>A clean editor that gets out of the way. Type, save, done.</p>
                    </article>

                    <article class="feature">
                        <div class="feature-icon"><svg class="icon"><use href="#i-pin"/></svg></div>
                        <h3>Pin what matters</h3>
                        <p>Keep your most-used notes at the top of the list, always in reach.</p>
                    </article>

                    <article class="feature">
                        <div class="feature-icon"><svg class="icon"><use href="#i-search"/></svg></div>
                        <h3>Find it instantly</h3>
                        <p>Search across every title and body as your collection grows.</p>
                    </article>

                    <article class="feature">
                        <div class="feature-icon"><svg class="icon"><use href="#i-lock"/></svg></div>
                        <h3>Yours alone</h3>
                        <p>Every note is locked to its owner and visible only to you.</p>
                    </article>
                </div>
            </div>
        </section>
    </main>
</body>
</html>

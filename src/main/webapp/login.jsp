<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<%@ page import="com.util.Csrf" %>
<c:set var="csrfToken" value="<%= Csrf.token(request) %>"/>
<c:set var="ctx" value="${pageContext.request.contextPath}"/>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Sign in &mdash; E-Notes</title>
    <%@ include file="all_component/allcss.jsp" %>
</head>
<body>
    <%@ include file="all_component/icons.jsp" %>
    <%@ include file="all_component/navbar.jsp" %>

    <main class="auth-shell">
        <div class="auth-card">
            <div class="auth-head">
                <div class="auth-icon"><svg class="icon"><use href="#i-user"/></svg></div>
                <h1>Welcome back</h1>
                <p>Sign in to reach your notes.</p>
            </div>

            <div class="auth-body">
                <%@ include file="all_component/flash.jsp" %>

                <form action="${ctx}/loginServlet" method="post" novalidate>
                    <input type="hidden" name="csrfToken" value="${csrfToken}">

                    <div class="field">
                        <label for="uemail">Email address</label>
                        <input class="input" type="email" id="uemail" name="uemail"
                               placeholder="you@example.com" autocomplete="email"
                               required autofocus>
                    </div>

                    <div class="field">
                        <label for="upassword">Password</label>
                        <div class="password-wrap">
                            <input class="input" type="password" id="upassword" name="upassword"
                                   placeholder="Your password" autocomplete="current-password" required>
                            <%-- Hidden until the script enables it, so it is never
                                 a dead button when scripting is unavailable. --%>
                            <button type="button" class="password-toggle" hidden
                                    data-password-toggle="upassword"
                                    aria-pressed="false" aria-label="Show password" title="Show password">
                                <svg class="icon" data-eye="show"><use href="#i-eye"/></svg>
                                <svg class="icon" data-eye="hide" hidden><use href="#i-eye-off"/></svg>
                            </button>
                        </div>
                    </div>

                    <button type="submit" class="btn btn-primary btn-block">
                        <svg class="icon"><use href="#i-user"/></svg> Sign in
                    </button>
                </form>
            </div>

            <div class="auth-foot">
                New here? <a href="${ctx}/register.jsp">Create an account</a>
            </div>
        </div>
    </main>

    <%@ include file="all_component/passwordToggle.jsp" %>
</body>
</html>

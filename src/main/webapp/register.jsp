<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<%@ page import="com.util.Csrf" %>
<c:set var="csrfToken" value="<%= Csrf.token(request) %>"/>
<c:set var="ctx" value="${pageContext.request.contextPath}"/>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Create account &mdash; E-Notes</title>
    <%@ include file="all_component/allcss.jsp" %>
</head>
<body>
    <%@ include file="all_component/icons.jsp" %>
    <%@ include file="all_component/navbar.jsp" %>

    <main class="auth-shell">
        <div class="auth-card">
            <div class="auth-head">
                <div class="auth-icon"><svg class="icon"><use href="#i-user-plus"/></svg></div>
                <h1>Create your account</h1>
                <p>Start keeping your notes in one place.</p>
            </div>

            <div class="auth-body">
                <%@ include file="all_component/flash.jsp" %>

                <form action="${ctx}/UserServlet" method="post" novalidate>
                    <input type="hidden" name="csrfToken" value="${csrfToken}">

                    <div class="field">
                        <label for="fname">Full name</label>
                        <input class="input" type="text" id="fname" name="fname"
                               placeholder="Your name" autocomplete="name"
                               maxlength="100" required autofocus>
                    </div>

                    <div class="field">
                        <label for="uemail">Email address</label>
                        <input class="input" type="email" id="uemail" name="uemail"
                               placeholder="you@example.com" autocomplete="email"
                               maxlength="190" required>
                    </div>

                    <div class="field">
                        <label for="upassword">Password</label>
                        <input class="input" type="password" id="upassword" name="upassword"
                               placeholder="At least 8 characters" autocomplete="new-password"
                               minlength="8" required>
                        <p class="field-hint">Use 8 characters or more.</p>
                    </div>

                    <button type="submit" class="btn btn-primary btn-block">
                        <svg class="icon"><use href="#i-user-plus"/></svg> Create account
                    </button>
                </form>
            </div>

            <div class="auth-foot">
                Already registered? <a href="${ctx}/login.jsp">Sign in</a>
            </div>
        </div>
    </main>

    <%@ include file="all_component/footer.jsp" %>
</body>
</html>

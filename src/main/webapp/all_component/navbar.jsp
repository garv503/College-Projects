<%--
    Site header.

    The user object comes from the session and is rendered with <c:out>, which
    escapes it. The old navbar wrote the name and email straight into the page
    with <%= %>, so a name containing markup was executed as HTML.

    The app has one fixed dark theme, so there is no theme switcher here.

    Sign-out is a POST form carrying the CSRF token, not a link, so another site
    cannot sign the user out by pointing an image at the URL.
--%>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>

<c:set var="ctx" value="${pageContext.request.contextPath}"/>

<header class="site-header">
    <div class="container">
        <nav class="nav" aria-label="Main">
            <a class="brand" href="${ctx}/${empty sessionScope.userD ? 'index.jsp' : 'home.jsp'}">
                <span class="brand-mark"><svg class="icon"><use href="#i-book"/></svg></span>
                E-Notes
            </a>

            <input type="checkbox" id="navToggle" class="nav-toggle">
            <label for="navToggle" class="nav-toggle-label" aria-label="Toggle navigation">
                <svg class="icon" style="width:22px;height:22px"><use href="#i-menu"/></svg>
            </label>

            <c:if test="${not empty sessionScope.userD}">
                <ul class="nav-links">
                    <li>
                        <a class="nav-link ${activePage eq 'home' ? 'is-active' : ''}" href="${ctx}/home.jsp">
                            <svg class="icon"><use href="#i-home"/></svg> Dashboard
                        </a>
                    </li>
                    <li>
                        <a class="nav-link ${activePage eq 'add' ? 'is-active' : ''}" href="${ctx}/addNotes.jsp">
                            <svg class="icon"><use href="#i-plus"/></svg> New note
                        </a>
                    </li>
                    <li>
                        <a class="nav-link ${activePage eq 'notes' ? 'is-active' : ''}" href="${ctx}/showNotes.jsp">
                            <svg class="icon"><use href="#i-notes"/></svg> My notes
                        </a>
                    </li>
                </ul>
            </c:if>

            <div class="nav-actions">
                <c:choose>
                    <c:when test="${not empty sessionScope.userD}">
                        <span class="user-chip" title="<c:out value='${sessionScope.userD.email}'/>">
                            <span class="avatar"><c:out value="${sessionScope.userD.initial}"/></span>
                            <span class="name"><c:out value="${sessionScope.userD.name}"/></span>
                        </span>
                        <form action="${ctx}/logoutServlet" method="post">
                            <input type="hidden" name="csrfToken" value="${csrfToken}">
                            <button type="submit" class="btn btn-outline btn-sm">
                                <svg class="icon"><use href="#i-logout"/></svg> Sign out
                            </button>
                        </form>
                    </c:when>
                    <c:otherwise>
                        <a class="btn btn-outline btn-sm" href="${ctx}/login.jsp">
                            <svg class="icon"><use href="#i-user"/></svg> Sign in
                        </a>
                        <a class="btn btn-primary btn-sm" href="${ctx}/register.jsp">
                            <svg class="icon"><use href="#i-user-plus"/></svg> Get started
                        </a>
                    </c:otherwise>
                </c:choose>
            </div>
        </nav>
    </div>
</header>

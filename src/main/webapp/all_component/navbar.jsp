<%--
    Site header.

    The user object comes from the session and is rendered with <c:out>, which
    escapes it. The old navbar wrote the name and email straight into the page
    with <%= %>, so a name containing markup was executed as HTML.

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
                <button type="button" class="btn btn-icon" id="themeToggle"
                        aria-label="Switch between light and dark theme">
                    <svg class="icon" data-theme-icon="light"><use href="#i-sun"/></svg>
                    <svg class="icon" data-theme-icon="dark" style="display:none"><use href="#i-moon"/></svg>
                </button>

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

<script>
    (function () {
        var toggle = document.getElementById('themeToggle');
        if (!toggle) { return; }

        var root = document.documentElement;
        var sun = toggle.querySelector('[data-theme-icon="light"]');
        var moon = toggle.querySelector('[data-theme-icon="dark"]');

        function currentTheme() {
            return root.getAttribute('data-theme')
                || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        }

        // Offer the theme the click will switch *to*.
        function paintIcon() {
            var dark = currentTheme() === 'dark';
            sun.style.display = dark ? '' : 'none';
            moon.style.display = dark ? 'none' : '';
        }

        toggle.addEventListener('click', function () {
            var next = currentTheme() === 'dark' ? 'light' : 'dark';
            root.setAttribute('data-theme', next);
            try {
                localStorage.setItem('enotes-theme', next);
            } catch (e) {
                /* Not persistable; the choice still applies to this page view. */
            }
            paintIcon();
        });

        paintIcon();
    })();
</script>

<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<%@ page import="java.time.Year" %>

<footer class="site-footer">
    <div class="container footer-inner">
        <span>E-Notes &mdash; designed and developed by Garv Bhargava</span>
        <span>&copy; <%= Year.now().getValue() %> &middot; All rights reserved</span>
    </div>
</footer>

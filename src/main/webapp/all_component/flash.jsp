<%--
    Renders one-shot success/error messages, then clears them so a refresh does
    not show the same banner again.
--%>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>

<c:if test="${not empty sessionScope.flashSuccess}">
    <div class="alert alert-success" role="status">
        <svg class="icon"><use href="#i-check"/></svg>
        <span><c:out value="${sessionScope.flashSuccess}"/></span>
    </div>
    <c:remove var="flashSuccess" scope="session"/>
</c:if>

<c:if test="${not empty sessionScope.flashError}">
    <div class="alert alert-error" role="alert">
        <svg class="icon"><use href="#i-alert"/></svg>
        <span><c:out value="${sessionScope.flashError}"/></span>
    </div>
    <c:remove var="flashError" scope="session"/>
</c:if>

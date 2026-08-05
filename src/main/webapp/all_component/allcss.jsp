<%--
    Shared <head> assets.

    Everything is local: the app used to load Bootstrap, jQuery, Popper and
    Font Awesome from three external CDNs, so it rendered unstyled and
    icon-less without internet access. Icons are now an inline SVG sprite
    (see icons.jsp) and styling is a single local stylesheet.
--%>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="E-Notes - a fast, private place to keep your notes.">
<%-- One fixed dark theme; tells the browser to match its own UI (form
     controls, scrollbars) before the stylesheet loads. --%>
<meta name="color-scheme" content="dark">
<link rel="stylesheet" href="${pageContext.request.contextPath}/css/style.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#128221;</text></svg>">

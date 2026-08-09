package com.util;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

/** Reads and writes JSON request/response bodies for the API servlets. */
public final class Json {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private Json() {
    }

    /** Writes {@code body} as JSON with the given status code. */
    public static void write(HttpServletResponse response, int status, Object body) throws IOException {
        response.setStatus(status);
        response.setContentType("application/json;charset=UTF-8");
        MAPPER.writeValue(response.getWriter(), body);
    }

    /** Writes a 200 response. */
    public static void ok(HttpServletResponse response, Object body) throws IOException {
        write(response, HttpServletResponse.SC_OK, body);
    }

    /** Writes an error in the single shape the front end knows how to display. */
    public static void error(HttpServletResponse response, int status, String message) throws IOException {
        write(response, status, Map.of("error", message));
    }

    /**
     * Parses the request body as JSON.
     *
     * @return the parsed tree, or {@code null} when the body is absent or malformed
     */
    public static JsonNode read(HttpServletRequest request) {
        try {
            if (request.getContentLength() == 0) {
                return null;
            }
            return MAPPER.readTree(request.getReader());
        } catch (IOException | RuntimeException e) {
            return null;
        }
    }

    /** Reads a string field, trimmed, returning {@code null} when absent or blank. */
    public static String text(JsonNode node, String field) {
        if (node == null || !node.hasNonNull(field)) {
            return null;
        }
        String value = node.get(field).asText().trim();
        return value.isEmpty() ? null : value;
    }

    /** Convenience builder for small ad-hoc response objects, preserving key order. */
    public static Map<String, Object> map() {
        return new LinkedHashMap<>();
    }
}

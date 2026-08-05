package com.User;

import java.sql.Timestamp;

/**
 * An application user.
 *
 * <p>{@code password} holds a hash, never a raw password, and is cleared before
 * the object is placed in the session so the credential is not kept in memory
 * for the life of the session.
 */
public class UserDetails {
    private int id;
    private String full_name;
    private String email;
    private String password;
    private Timestamp createdAt;

    public UserDetails() {
        super();
    }

    public UserDetails(int id, String full_name, String email, String password) {
        super();
        this.id = id;
        this.full_name = full_name;
        this.email = email;
        this.password = password;
    }

    public int getId() {
        return id;
    }

    public void setId(int id) {
        this.id = id;
    }

    public String getName() {
        return full_name;
    }

    public void setName(String name) {
        this.full_name = name;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }

    public Timestamp getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Timestamp createdAt) {
        this.createdAt = createdAt;
    }

    /** First letter of the user's name, for the avatar badge in the navbar. */
    public String getInitial() {
        if (full_name == null || full_name.trim().isEmpty()) {
            return "?";
        }
        return full_name.trim().substring(0, 1).toUpperCase();
    }
}

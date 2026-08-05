package com.User;

import java.sql.Timestamp;

/** A single note belonging to one user. */
public class Post {
    private int id;
    private String title;
    private String content;
    private boolean pinned;
    private int uid;
    private Timestamp createdAt;
    private Timestamp updatedAt;

    public int getId() {
        return id;
    }

    public void setId(int id) {
        this.id = id;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public boolean isPinned() {
        return pinned;
    }

    public void setPinned(boolean pinned) {
        this.pinned = pinned;
    }

    public int getUid() {
        return uid;
    }

    public void setUid(int uid) {
        this.uid = uid;
    }

    public Timestamp getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Timestamp createdAt) {
        this.createdAt = createdAt;
    }

    public Timestamp getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Timestamp updatedAt) {
        this.updatedAt = updatedAt;
    }

    /** True when the note has been changed since it was first created. */
    public boolean isEdited() {
        return createdAt != null && updatedAt != null && updatedAt.after(createdAt);
    }

    /** Kept so existing pages that referenced the old published-date getter still work. */
    public Timestamp getPdate() {
        return createdAt;
    }
}

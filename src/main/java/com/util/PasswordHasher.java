package com.util;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.security.spec.InvalidKeySpecException;
import java.util.Base64;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;

/**
 * Salted PBKDF2 password hashing.
 *
 * <p>Passwords used to be stored as plain text, so anyone who could read the
 * {@code user} table could read every account's password. Hashes produced here
 * are one-way: a stolen table no longer reveals the passwords behind it.
 *
 * <p>Stored format is self-describing so the cost factor can be raised later
 * without invalidating existing hashes:
 * {@code pbkdf2$<iterations>$<base64 salt>$<base64 hash>}.
 */
public final class PasswordHasher {

    private static final String ALGORITHM = "PBKDF2WithHmacSHA256";
    private static final String PREFIX = "pbkdf2";
    private static final String SEPARATOR = "\\$";
    private static final int ITERATIONS = 120_000;
    private static final int SALT_BYTES = 16;
    private static final int KEY_BITS = 256;

    private static final SecureRandom RANDOM = new SecureRandom();

    private PasswordHasher() {
    }

    /** Hashes a raw password with a freshly generated random salt. */
    public static String hash(String rawPassword) {
        byte[] salt = new byte[SALT_BYTES];
        RANDOM.nextBytes(salt);
        byte[] key = derive(rawPassword, salt, ITERATIONS);

        Base64.Encoder encoder = Base64.getEncoder();
        return PREFIX + "$" + ITERATIONS + "$" + encoder.encodeToString(salt) + "$" + encoder.encodeToString(key);
    }

    /**
     * Checks a raw password against a stored value.
     *
     * <p>Returns false rather than throwing on a malformed stored value, so a
     * corrupt row fails the login instead of breaking the whole request.
     */
    public static boolean matches(String rawPassword, String storedValue) {
        if (rawPassword == null || storedValue == null || !isHashed(storedValue)) {
            return false;
        }

        String[] parts = storedValue.split(SEPARATOR);
        if (parts.length != 4) {
            return false;
        }

        try {
            int iterations = Integer.parseInt(parts[1]);
            byte[] salt = Base64.getDecoder().decode(parts[2]);
            byte[] expected = Base64.getDecoder().decode(parts[3]);
            byte[] actual = derive(rawPassword, salt, iterations);
            // Constant-time compare, so response timing does not leak how much
            // of the hash matched.
            return MessageDigest.isEqual(expected, actual);
        } catch (IllegalArgumentException e) {
            return false;
        }
    }

    /**
     * Reports whether a stored value is already in the hashed format.
     *
     * <p>Rows written before hashing existed hold raw passwords; the login flow
     * uses this to detect them and transparently upgrade them.
     */
    public static boolean isHashed(String storedValue) {
        return storedValue != null && storedValue.startsWith(PREFIX + "$");
    }

    private static byte[] derive(String rawPassword, byte[] salt, int iterations) {
        PBEKeySpec spec = new PBEKeySpec(rawPassword.toCharArray(), salt, iterations, KEY_BITS);
        try {
            return SecretKeyFactory.getInstance(ALGORITHM).generateSecret(spec).getEncoded();
        } catch (NoSuchAlgorithmException | InvalidKeySpecException e) {
            throw new IllegalStateException("Unable to hash password using " + ALGORITHM, e);
        } finally {
            spec.clearPassword();
        }
    }

    /** Constant-time comparison helper for non-hash secrets such as CSRF tokens. */
    public static boolean constantTimeEquals(String a, String b) {
        if (a == null || b == null) {
            return false;
        }
        return MessageDigest.isEqual(
                a.getBytes(StandardCharsets.UTF_8),
                b.getBytes(StandardCharsets.UTF_8));
    }
}

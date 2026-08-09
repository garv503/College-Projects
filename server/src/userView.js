/**
 * The user fields the client is allowed to see.
 *
 * Shared so the sign-in response and the per-request session refresh can never
 * drift apart. Deliberately omits the password.
 */
export function publicView(user) {
  return {
    id: user.id,
    name: user.full_name,
    email: user.email,
    role: user.role,
    initial: (user.full_name || '?').trim().charAt(0).toUpperCase() || '?',
    createdAt: user.created_at ? new Date(user.created_at).getTime() : null,
  };
}

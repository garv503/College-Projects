import { Router } from 'express';
import { execute, query, queryOne } from '../db.js';

/**
 * Administrator endpoints.
 *
 * Mounted behind requireAdmin, so reaching any handler here already proves the
 * caller is an administrator. The role comes from the session, which is written
 * at sign-in from the database, so a client cannot claim it for itself.
 *
 * Two rules exist purely to make lockout impossible:
 *   - an admin cannot change their own role
 *   - an admin cannot delete their own account
 * Together they guarantee at least one administrator always remains, because
 * the acting admin necessarily survives their own request.
 */
const router = Router();

router.get('/users', async (req, res, next) => {
  try {
    const users = await query(`
      SELECT u.id, u.full_name, u.email, u.role, u.created_at,
             COUNT(p.id) AS note_count
      FROM user u
      LEFT JOIN post p ON p.uid = u.id
      GROUP BY u.id, u.full_name, u.email, u.role, u.created_at
      ORDER BY u.id ASC
    `);

    res.json({
      users: users.map((user) => ({
        id: user.id,
        name: user.full_name,
        email: user.email,
        role: user.role,
        noteCount: Number(user.note_count) || 0,
        createdAt: user.created_at ? new Date(user.created_at).getTime() : null,
        // Lets the UI disable the controls the server would reject anyway.
        isSelf: user.id === req.session.user.id,
      })),
    });
  } catch (error) {
    next(error);
  }
});

router.get('/stats', async (req, res, next) => {
  try {
    const totals = await queryOne(`
      SELECT
        (SELECT COUNT(*) FROM user)                      AS totalUsers,
        (SELECT COUNT(*) FROM user WHERE role = 'ADMIN') AS totalAdmins,
        (SELECT COUNT(*) FROM post)                      AS totalNotes,
        (SELECT COUNT(*) FROM post WHERE pinned = TRUE)  AS pinnedNotes
    `);

    res.json({
      totalUsers: Number(totals.totalUsers) || 0,
      totalAdmins: Number(totals.totalAdmins) || 0,
      totalNotes: Number(totals.totalNotes) || 0,
      pinnedNotes: Number(totals.pinnedNotes) || 0,
    });
  } catch (error) {
    next(error);
  }
});

router.patch('/users/:id/role', async (req, res, next) => {
  try {
    const id = Number(req.params.id);
    const role = req.body?.role;

    if (!Number.isInteger(id) || id < 1) {
      return res.status(404).json({ error: 'That user could not be found.' });
    }
    if (role !== 'USER' && role !== 'ADMIN') {
      return res.status(400).json({ error: "Role must be either 'USER' or 'ADMIN'." });
    }
    if (id === req.session.user.id) {
      return res.status(400).json({
        error: 'You cannot change your own role. Ask another administrator.',
      });
    }

    const result = await execute('UPDATE user SET role = ? WHERE id = ?', [role, id]);
    if (result.affectedRows !== 1) {
      return res.status(404).json({ error: 'That user could not be found.' });
    }

    return res.json({ message: `Role updated to ${role}.` });
  } catch (error) {
    return next(error);
  }
});

router.delete('/users/:id', async (req, res, next) => {
  try {
    const id = Number(req.params.id);

    if (!Number.isInteger(id) || id < 1) {
      return res.status(404).json({ error: 'That user could not be found.' });
    }
    if (id === req.session.user.id) {
      return res.status(400).json({ error: 'You cannot delete your own account.' });
    }

    // The post table's foreign key cascades, so the user's notes go with them.
    const result = await execute('DELETE FROM user WHERE id = ?', [id]);
    if (result.affectedRows !== 1) {
      return res.status(404).json({ error: 'That user could not be found.' });
    }

    return res.json({ message: 'User deleted, along with all of their notes.' });
  } catch (error) {
    return next(error);
  }
});

export default router;

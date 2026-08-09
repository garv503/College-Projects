import { Router } from 'express';
import { queryOne } from '../db.js';

/** Dashboard counters for the signed-in user. */
const router = Router();

router.get('/', async (req, res, next) => {
  try {
    const uid = req.session.user.id;

    const totals = await queryOne(
      'SELECT COUNT(*) AS totalNotes, SUM(pinned = TRUE) AS pinnedNotes FROM post WHERE uid = ?',
      [uid],
    );

    res.json({
      totalNotes: Number(totals.totalNotes) || 0,
      // SUM returns null when the user has no rows at all.
      pinnedNotes: Number(totals.pinnedNotes) || 0,
    });
  } catch (error) {
    next(error);
  }
});

export default router;

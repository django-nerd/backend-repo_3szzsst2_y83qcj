import { Router } from 'express';
import { verifyIdentity, listChecks } from '../../controllers/identity.controller';
import { authMiddleware } from '../../middleware/auth';

const router = Router();

router.post('/verify', authMiddleware, verifyIdentity);
router.get('/checks', authMiddleware, listChecks);

export default router;

import { Router } from 'express';
import { register, login, profile } from '../../controllers/auth.controller';
import { authMiddleware } from '../../middleware/auth';

const router = Router();

router.post('/register', register);
router.post('/login', login);
router.get('/profile', authMiddleware, profile);

export default router;

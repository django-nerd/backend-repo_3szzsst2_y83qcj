import { Router } from 'express';
import { createGrievance, listGrievances, analytics } from '../../controllers/grievance.controller';
import { authMiddleware } from '../../middleware/auth';

const router = Router();

router.post('/', authMiddleware, createGrievance);
router.get('/', authMiddleware, listGrievances);
router.get('/analytics', authMiddleware, analytics);

export default router;

import { Router } from 'express';
import authRouter from './v1/auth';
import identityRouter from './v1/identity';
import appRouter from './v1/app';
import grievanceRouter from './v1/grievance';

const router = Router();

router.use('/auth', authRouter);
router.use('/identity', identityRouter);
router.use('/app', appRouter);
router.use('/grievance', grievanceRouter);

export default router;

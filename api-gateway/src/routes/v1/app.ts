import { Router } from 'express';
import { addOfficial, listOfficial, markSuspicious, listSuspicious } from '../../controllers/app.controller';

const router = Router();

router.post('/official', addOfficial);
router.get('/official', listOfficial);
router.post('/suspicious', markSuspicious);
router.get('/suspicious', listSuspicious);

export default router;

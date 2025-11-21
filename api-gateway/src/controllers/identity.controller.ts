import { Response } from 'express';
import IdentityCheck from '../models/IdentityCheck';
import { identityPredict } from '../services/ml';
import { AuthRequest } from '../middleware/auth';

export const verifyIdentity = async (req: AuthRequest, res: Response) => {
  try {
    const userId = req.user!.id;
    const payload = req.body; // e.g., { livenessVideo: base64 }
    const result = await identityPredict(payload);

    const approved = result.data.approved ?? true;
    const score = result.data.score ?? 0.5;

    const doc = await IdentityCheck.create({ userId, status: approved ? 'approved' : 'rejected', score, reason: result.data.reason });
    return res.json({ success: true, statusCode: 200, data: { checkId: doc.id, status: doc.status, score } });
  } catch (e) {
    return res.status(500).json({ success: false, statusCode: 500, error: 'identity verification failed' });
  }
};

export const listChecks = async (req: AuthRequest, res: Response) => {
  try {
    const userId = req.user!.id;
    const items = await IdentityCheck.find({ userId }).sort({ createdAt: -1 }).limit(20);
    return res.json({ success: true, statusCode: 200, data: items });
  } catch (e) {
    return res.status(500).json({ success: false, statusCode: 500, error: 'failed to list checks' });
  }
};

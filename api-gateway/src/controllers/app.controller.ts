import { Request, Response } from 'express';
import OfficialApp from '../models/OfficialApp';
import SuspiciousApp from '../models/SuspiciousApp';

export const addOfficial = async (req: Request, res: Response) => {
  try {
    const { packageName, issuer, notes } = req.body;
    if (!packageName || !issuer) return res.status(400).json({ success: false, statusCode: 400, error: 'packageName and issuer required' });
    const doc = await OfficialApp.create({ packageName, issuer, notes });
    return res.json({ success: true, statusCode: 200, data: doc });
  } catch (e: any) {
    const msg = e?.code === 11000 ? 'package already exists' : 'failed to add official app';
    return res.status(400).json({ success: false, statusCode: 400, error: msg });
  }
};

export const listOfficial = async (_req: Request, res: Response) => {
  const items = await OfficialApp.find().sort({ createdAt: -1 }).limit(100);
  return res.json({ success: true, statusCode: 200, data: items });
};

export const markSuspicious = async (req: Request, res: Response) => {
  try {
    const { packageName, reason, riskScore } = req.body;
    if (!packageName || !reason) return res.status(400).json({ success: false, statusCode: 400, error: 'packageName and reason required' });
    const doc = await SuspiciousApp.create({ packageName, reason, riskScore });
    return res.json({ success: true, statusCode: 200, data: doc });
  } catch (e) {
    return res.status(500).json({ success: false, statusCode: 500, error: 'failed to mark suspicious' });
  }
};

export const listSuspicious = async (_req: Request, res: Response) => {
  const items = await SuspiciousApp.find().sort({ createdAt: -1 }).limit(100);
  return res.json({ success: true, statusCode: 200, data: items });
};

import { Response } from 'express';
import Grievance from '../models/Grievance';
import { grievanceCategorize } from '../services/ml';
import { AuthRequest } from '../middleware/auth';

export const createGrievance = async (req: AuthRequest, res: Response) => {
  try {
    const userId = req.user!.id;
    const { title, description } = req.body;
    if (!title || !description) return res.status(400).json({ success: false, statusCode: 400, error: 'title and description required' });

    const ml = await grievanceCategorize({ title, description });
    const category = ml.data.category || 'general';

    const doc = await Grievance.create({ userId, title, description, category });
    return res.json({ success: true, statusCode: 200, data: doc });
  } catch (e) {
    return res.status(500).json({ success: false, statusCode: 500, error: 'failed to create grievance' });
  }
};

export const listGrievances = async (req: AuthRequest, res: Response) => {
  try {
    const userId = req.user!.id;
    const items = await Grievance.find({ userId }).sort({ createdAt: -1 }).limit(100);
    return res.json({ success: true, statusCode: 200, data: items });
  } catch (e) {
    return res.status(500).json({ success: false, statusCode: 500, error: 'failed to list grievances' });
  }
};

export const analytics = async (_req: AuthRequest, res: Response) => {
  try {
    const pipeline = [
      { $group: { _id: '$category', count: { $sum: 1 } } },
      { $project: { _id: 0, category: '$_id', count: 1 } },
    ];
    const data = await Grievance.aggregate(pipeline);
    return res.json({ success: true, statusCode: 200, data });
  } catch (e) {
    return res.status(500).json({ success: false, statusCode: 500, error: 'failed to compute analytics' });
  }
};

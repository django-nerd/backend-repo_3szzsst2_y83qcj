import { Request, Response } from 'express';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import User from '../models/User';

const signToken = (id: string, email: string) => {
  const secret = process.env.JWT_SECRET || 'dev_secret';
  return jwt.sign({ id, email }, secret, { expiresIn: '24h' });
};

export const register = async (req: Request, res: Response) => {
  try {
    const { email, password, name } = req.body;
    if (!email || !password) return res.status(400).json({ success: false, statusCode: 400, error: 'email and password required' });

    const exists = await User.findOne({ email });
    if (exists) return res.status(409).json({ success: false, statusCode: 409, error: 'email already registered' });

    const passwordHash = await bcrypt.hash(password, 10);
    const user = await User.create({ email, passwordHash, name });
    const token = signToken(user.id, user.email);

    return res.json({ success: true, statusCode: 200, data: { token, user: { id: user.id, email: user.email, name: user.name } } });
  } catch (e) {
    return res.status(500).json({ success: false, statusCode: 500, error: 'registration failed' });
  }
};

export const login = async (req: Request, res: Response) => {
  try {
    const { email, password } = req.body;
    const user = await User.findOne({ email });
    if (!user) return res.status(401).json({ success: false, statusCode: 401, error: 'invalid credentials' });

    const ok = await bcrypt.compare(password, user.passwordHash);
    if (!ok) return res.status(401).json({ success: false, statusCode: 401, error: 'invalid credentials' });

    const token = signToken(user.id, user.email);
    return res.json({ success: true, statusCode: 200, data: { token, user: { id: user.id, email: user.email, name: user.name } } });
  } catch (e) {
    return res.status(500).json({ success: false, statusCode: 500, error: 'login failed' });
  }
};

export const profile = async (req: any, res: Response) => {
  try {
    const id = req.user?.id;
    const user = await User.findById(id).select('-passwordHash');
    return res.json({ success: true, statusCode: 200, data: user });
  } catch (e) {
    return res.status(500).json({ success: false, statusCode: 500, error: 'failed to fetch profile' });
  }
};

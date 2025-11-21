import dotenv from 'dotenv';
import express from 'express';
import cors from 'cors';
import morgan from 'morgan';
import mongoose from 'mongoose';
import apiRouter from './routes';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(morgan('dev'));

app.get('/api/health', (_req, res) => {
  res.json({ success: true, statusCode: 200, data: { service: 'api-gateway', status: 'ok' } });
});

app.use('/api', apiRouter);

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017';
const DATABASE_NAME = process.env.DATABASE_NAME || 'trustguard';
const PORT = process.env.PORT ? Number(process.env.PORT) : 8080;

mongoose
  .connect(`${MONGODB_URI}/${DATABASE_NAME}`)
  .then(() => {
    console.log('MongoDB connected');
    app.listen(PORT, () => console.log(`API running on :${PORT}`));
  })
  .catch((err) => {
    console.error('Mongo connection error', err);
    process.exit(1);
  });

export default app;

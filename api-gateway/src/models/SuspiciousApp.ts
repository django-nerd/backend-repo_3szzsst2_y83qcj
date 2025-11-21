import mongoose, { Schema, Document } from 'mongoose';

export interface ISuspiciousApp extends Document {
  packageName: string;
  reason: string;
  riskScore?: number;
  createdAt: Date;
  updatedAt: Date;
}

const SuspiciousAppSchema = new Schema<ISuspiciousApp>(
  {
    packageName: { type: String, required: true },
    reason: { type: String, required: true },
    riskScore: { type: Number },
  },
  { timestamps: true }
);

export default mongoose.models.SuspiciousApp || mongoose.model<ISuspiciousApp>('SuspiciousApp', SuspiciousAppSchema);

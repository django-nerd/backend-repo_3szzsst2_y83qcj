import mongoose, { Schema, Document } from 'mongoose';

export interface IIdentityCheck extends Document {
  userId: mongoose.Types.ObjectId;
  status: 'approved' | 'rejected' | 'pending';
  score?: number;
  reason?: string;
  createdAt: Date;
  updatedAt: Date;
}

const IdentityCheckSchema = new Schema<IIdentityCheck>(
  {
    userId: { type: Schema.Types.ObjectId, ref: 'User', required: true },
    status: { type: String, enum: ['approved', 'rejected', 'pending'], default: 'pending' },
    score: { type: Number },
    reason: { type: String },
  },
  { timestamps: true }
);

export default mongoose.models.IdentityCheck || mongoose.model<IIdentityCheck>('IdentityCheck', IdentityCheckSchema);

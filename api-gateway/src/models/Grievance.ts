import mongoose, { Schema, Document } from 'mongoose';

export interface IGrievance extends Document {
  userId: mongoose.Types.ObjectId;
  title: string;
  description: string;
  category?: string;
  status: 'open' | 'in_progress' | 'resolved';
  createdAt: Date;
  updatedAt: Date;
}

const GrievanceSchema = new Schema<IGrievance>(
  {
    userId: { type: Schema.Types.ObjectId, ref: 'User', required: true },
    title: { type: String, required: true },
    description: { type: String, required: true },
    category: { type: String },
    status: { type: String, enum: ['open', 'in_progress', 'resolved'], default: 'open' },
  },
  { timestamps: true }
);

export default mongoose.models.Grievance || mongoose.model<IGrievance>('Grievance', GrievanceSchema);

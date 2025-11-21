import mongoose, { Schema, Document } from 'mongoose';

export interface IOfficialApp extends Document {
  packageName: string;
  issuer: string;
  notes?: string;
  createdAt: Date;
  updatedAt: Date;
}

const OfficialAppSchema = new Schema<IOfficialApp>(
  {
    packageName: { type: String, required: true, unique: true },
    issuer: { type: String, required: true },
    notes: { type: String },
  },
  { timestamps: true }
);

export default mongoose.models.OfficialApp || mongoose.model<IOfficialApp>('OfficialApp', OfficialAppSchema);

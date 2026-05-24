export interface User {
  id: string;
  clerk_id: string;
  email: string;
  is_pro: boolean;
  stripe_customer_id: string | null;
  created_at: Date;
}
